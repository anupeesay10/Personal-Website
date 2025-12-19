from flask import Flask, request, jsonify
import yfinance as yf
import pandas as pd
import os
import json

app = Flask(__name__)

# Storage folder for CSVs
DATA_FOLDER = os.environ.get("DATA_FOLDER", "stock_data")
os.makedirs(DATA_FOLDER, exist_ok=True)

# --- Helper Functions ---
def get_csv_path(ticker):
    return os.path.join(DATA_FOLDER, f"{ticker.upper()}.csv")

def save_data_to_csv(df, ticker):
    df.to_csv(get_csv_path(ticker), index=False)

def load_data_from_csv(ticker):
    path = get_csv_path(ticker)
    if os.path.exists(path):
        return pd.read_csv(path, parse_dates=['date'])
    return None

def get_available_years(df):
    if df is None or df.empty:
        return []
    return sorted(df['date'].dt.year.unique())

# --- API Endpoints ---
@app.route("/api/stock/load", methods=["POST"])
def load_stock_data():
    try:
        data = request.get_json()
        ticker = data.get("ticker", "").upper()
        start_date = data.get("start_date")
        end_date = data.get("end_date")
        if not ticker:
            return jsonify({"success": False, "message": "Ticker symbol is required"}), 400

        # Try loading from CSV first
        df = load_data_from_csv(ticker)
        source = "database"
        if df is None or df.empty:
            # Download from Yahoo Finance
            df = yf.download(ticker, start=start_date, end=end_date)
            if df.empty:
                return jsonify({"success": False, "message": f"No data found for {ticker}"}), 404
            df = df.reset_index().rename(columns={"Date": "date"})
            save_data_to_csv(df, ticker)
            source = "Yahoo Finance"

        # Convert DataFrame to JSON for Dash
        df_json = df.to_json(orient="split", date_format="iso")
        available_years = get_available_years(df)
        return jsonify({
            "success": True,
            "data": df_json,
            "available_years": available_years,
            "source": source
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/stock/data/<ticker>", methods=["GET"])
def check_ticker_data(ticker):
    try:
        df = load_data_from_csv(ticker)
        if df is None or df.empty:
            return jsonify({"success": False, "message": f"No data available for {ticker}"}), 404
        df_json = df.to_json(orient="split", date_format="iso")
        return jsonify({
            "success": True,
            "data": df_json,
            "available_years": get_available_years(df),
            "source": "database"
        })
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/stock/tables", methods=["GET"])
def list_available_tickers():
    try:
        files = os.listdir(DATA_FOLDER)
        tickers = [f.replace(".csv", "") for f in files if f.endswith(".csv")]
        return jsonify({"success": True, "tickers": tickers})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# --- Run Server ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)
