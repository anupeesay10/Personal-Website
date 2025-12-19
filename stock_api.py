import yfinance as yf
import pandas as pd
from sqlalchemy import create_engine
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import date
import os

# Database connection
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

engine = create_engine(DATABASE_URL)

# Create Flask app
app = Flask(__name__)
CORS(app)

# Root route to confirm deployment
@app.route("/", methods=['GET'])
def index():
    return jsonify({
        'success': True,
        'message': 'Stock API is live!'
    })

# Health check route
@app.route("/api/health", methods=['GET'])
def health_check():
    try:
        pd.read_sql_query("SELECT 1;", engine)
        return jsonify({'success': True, 'message': 'API is healthy'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'API health check failed: {str(e)}'}), 500


# Load stock data
@app.route('/api/stock/load', methods=['POST'])
def load_stock_data():
    try:
        data = request.get_json()
        ticker = data.get('ticker', 'TSLA').upper()
        start_date = data.get('start_date', '2010-06-29')
        end_date = data.get('end_date', date.today().strftime("%Y-%m-%d"))

        if not ticker:
            return jsonify({'success': False, 'message': 'Ticker symbol required'}), 400

        table_name = f"{ticker.lower()}_data"

        # Check if table exists
        query = f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = '{table_name}'
        );
        """
        exists = pd.read_sql_query(query, engine).iloc[0, 0]

        # Fetch existing data if present
        if exists:
            date_query = f"""
            SELECT MIN("Date") as min_date, MAX("Date") as max_date 
            FROM {table_name};
            """
            date_range = pd.read_sql_query(date_query, engine)
            db_min_date = pd.to_datetime(date_range['min_date'][0])
            db_max_date = pd.to_datetime(date_range['max_date'][0])
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)

            if start_dt >= db_min_date and end_dt <= db_max_date:
                df_existing = pd.read_sql_query(
                    f'SELECT * FROM {table_name} WHERE "Date" BETWEEN \'{start_date}\' AND \'{end_date}\';',
                    engine
                )
                df_existing['date'] = pd.to_datetime(df_existing['Date'])
                df_existing.drop(columns=['Date'], inplace=True)
                return jsonify({
                    'success': True,
                    'message': f'Data for {ticker} retrieved from database!',
                    'data': df_existing.to_json(date_format='iso', orient='split'),
                    'available_years': sorted(df_existing['date'].dt.year.unique().tolist()),
                    'source': 'database'
                })

        # Download data from Yahoo Finance
        df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=False)
        if df.empty:
            return jsonify({'success': False, 'message': f'No data found for {ticker}'}), 404

        df = df.reset_index()
        df['Date'] = pd.to_datetime(df['Date'])

        # Save to SQL
        if_exists_action = 'replace' if not exists else 'append'
        df.to_sql(table_name, engine, if_exists=if_exists_action, index=False)

        # Remove duplicates if appended
        if if_exists_action == 'append':
            df_all = pd.read_sql_query(f'SELECT * FROM {table_name};', engine)
            df_all = df_all.drop_duplicates(subset=['Date'])
            df_all.to_sql(table_name, engine, if_exists='replace', index=False)

        df['date'] = df['Date']
        df.drop(columns=['Date'], inplace=True)

        return jsonify({
            'success': True,
            'message': f'Data for {ticker} loaded successfully!',
            'data': df.to_json(date_format='iso', orient='split'),
            'available_years': sorted(df['date'].dt.year.unique().tolist()),
            'source': 'yahoo_finance'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Get stock data
@app.route('/api/stock/data/<ticker>', methods=['GET'])
def get_stock_data(ticker):
    try:
        table_name = f"{ticker.lower()}_data"
        query = f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name='{table_name}');"
        exists = pd.read_sql_query(query, engine).iloc[0, 0]
        if not exists:
            return jsonify({'success': False, 'message': f'No data for {ticker}'}), 404

        df = pd.read_sql_query(f'SELECT * FROM {table_name};', engine)
        df['date'] = pd.to_datetime(df['Date'])
        df.drop(columns=['Date'], inplace=True)

        return jsonify({
            'success': True,
            'data': df.to_json(date_format='iso', orient='split'),
            'available_years': sorted(df['date'].dt.year.unique().tolist()),
            'source': 'database'
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Get available tables
@app.route('/api/stock/tables', methods=['GET'])
def get_available_tables():
    try:
        query = """
        SELECT table_name FROM information_schema.tables
        WHERE table_schema='public' AND table_name LIKE '%_data';
        """
        tables = pd.read_sql_query(query, engine)
        tickers = [t.replace('_data', '').upper() for t in tables['table_name']]
        return jsonify({'success': True, 'tickers': tickers})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

# Run the app on Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
