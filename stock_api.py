import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine, text
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import date
import os

# -----------------------------
# Database connection
# -----------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# -----------------------------
# Flask app
# -----------------------------
app = Flask(__name__)
CORS(app)

API_PREFIX = "/api"

# -----------------------------
# Root (Render health check)
# -----------------------------
@app.route("/", methods=["GET"])
def root():
    return jsonify({"success": True, "message": "Stock API is live!"})

# -----------------------------
# Health check
# -----------------------------
@app.route(f"{API_PREFIX}/health", methods=["GET"])
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return jsonify({"success": True, "message": "API is healthy"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------
# Load stock data
# -----------------------------
@app.route(f"{API_PREFIX}/stock/load", methods=["POST"])
def load_stock_data():
    try:
        data = request.get_json(force=True)

        ticker = data.get("ticker", "TSLA").upper()
        start_date = data.get("start_date", "2010-06-29")
        end_date = data.get("end_date", date.today().strftime("%Y-%m-%d"))

        table_name = f"{ticker.lower()}_data"

        # Check table existence
        exists_query = text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema='public'
                AND table_name=:table
            )
        """)

        with engine.connect() as conn:
            exists = conn.execute(exists_query, {"table": table_name}).scalar()

        # Download data
        df = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            progress=False,
            threads=False
        )

        if df.empty:
            return jsonify({"success": False, "message": "No data found"}), 404

        df.reset_index(inplace=True)
        df["Date"] = pd.to_datetime(df["Date"])

        df.to_sql(
            table_name,
            engine,
            if_exists="append" if exists else "replace",
            index=False
        )

        # Deduplicate
        df_all = pd.read_sql_query(f'SELECT * FROM "{table_name}"', engine)
        df_all.drop_duplicates(subset=["Date"], inplace=True)
        df_all.to_sql(table_name, engine, if_exists="replace", index=False)

        df_all["date"] = pd.to_datetime(df_all["Date"])
        df_all.drop(columns=["Date"], inplace=True)

        return jsonify({
            "success": True,
            "ticker": ticker,
            "rows": len(df_all),
            "available_years": sorted(df_all["date"].dt.year.unique().tolist()),
            "source": "yahoo_finance"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------
# Get stock data
# -----------------------------
@app.route(f"{API_PREFIX}/stock/data/<ticker>", methods=["GET"])
def get_stock_data(ticker):
    try:
        table_name = f"{ticker.lower()}_data"

        exists = pd.read_sql_query(
            f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public'
                AND table_name='{table_name}'
            )
            """,
            engine
        ).iloc[0, 0]

        if not exists:
            return jsonify({"success": False, "message": "No data found"}), 404

        df = pd.read_sql_query(f'SELECT * FROM "{table_name}"', engine)
        df["date"] = pd.to_datetime(df["Date"])
        df.drop(columns=["Date"], inplace=True)

        return jsonify({
            "success": True,
            "data": df.to_json(orient="split", date_format="iso"),
            "available_years": sorted(df["date"].dt.year.unique().tolist()),
            "source": "database"
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# -----------------------------
# List available tickers
# -----------------------------
@app.route(f"{API_PREFIX}/stock/tables", methods=["GET"])
def get_available_tables():
    try:
        df = pd.read_sql_query("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            AND table_name LIKE '%_data'
        """, engine)

        tickers = [t.replace("_data", "").upper() for t in df["table_name"]]

        return jsonify({"success": True, "tickers": tickers})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
