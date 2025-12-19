import pandas as pd
import plotly.graph_objects as go
import datetime
from datetime import date
import requests
import json
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.express as px
import os

# Display all rows and columns
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)

# Default values
DEFAULT_TICKER = "TSLA"
DEFAULT_START_DATE = "2010-06-29"
DEFAULT_END_DATE = date.today().strftime("%Y-%m-%d")

# API endpoint — **use the Render service URL for your API service**
API_URL = os.environ.get("API_URL", "http://localhost:5001/api")

# Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Dropdown options for statistics view
dropdown_options = [
    {'label': 'Yearly Statistics', 'value': 'Yearly Statistics'},
    {'label': 'All Years Statistics', 'value': 'All Years Statistics'}
]

# Initial year list
current_year = datetime.datetime.now().year
year_list = [i for i in range(2010, current_year + 1)]

# --- Layout ---
app.layout = html.Div([
    html.H1("Stock Dashboard", style={'textAlign': 'center', 'color': '#003366'}),

    html.Div([
        html.Div([
            html.Label("Enter Stock Ticker:"),
            dcc.Input(id='ticker-input', type='text', value=DEFAULT_TICKER, style={'width': '100%', 'padding': '8px', 'margin-bottom': '10px'}),
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label("Start Date:"),
            dcc.DatePickerSingle(id='start-date-picker', date=DEFAULT_START_DATE, display_format='YYYY-MM-DD', style={'width': '100%'})
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label("End Date:"),
            dcc.DatePickerSingle(id='end-date-picker', date=DEFAULT_END_DATE, display_format='YYYY-MM-DD', style={'width': '100%'})
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Button('Load Stock Data', id='submit-button', n_clicks=0,
                    style={'width': '100%', 'padding': '10px', 'margin-top': '20px', 'background-color': '#003366', 'color': 'white'}),
    ], style={'margin-bottom': '20px', 'border': '1px solid #ddd', 'padding': '10px', 'border-radius': '5px'}),

    html.Div(id='data-loaded-message', style={'margin': '10px 0', 'color': 'green'}),

    html.Div([
        html.Label("Select Statistics:"),
        dcc.Dropdown(id='stat-select', options=dropdown_options, value='Yearly Statistics')
    ]),

    html.Div([
        html.Label("Select Year:"),
        dcc.Dropdown(id='select-year', options=[{'label': i, 'value': i} for i in year_list], value=year_list[-1])
    ]),

    html.Div(id='output-container', className='chart-grid', style={'padding': '20px'}),

    # Store the loaded data in browser
    dcc.Store(id='stock-data-store'),
    dcc.Store(id='years-available'),

    html.Div(id='initialization-div', style={'display': 'none'})
])

# --- Callbacks ---
@app.callback(
    [Output('stock-data-store', 'data'),
     Output('data-loaded-message', 'children'),
     Output('years-available', 'data'),
     Output('select-year', 'options'),
     Output('select-year', 'value')],
    [Input('submit-button', 'n_clicks'),
     Input('initialization-div', 'children')],
    [State('ticker-input', 'value'),
     State('start-date-picker', 'date'),
     State('end-date-picker', 'date')]
)
def load_stock_data(n_clicks, init_trigger, ticker, start_date, end_date):
    import dash
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None

    # Initialization check
    if trigger_id == 'initialization-div':
        result = check_ticker_data(DEFAULT_TICKER)
        if result:
            df_json = result.get('data')
            available_years = result.get('available_years', [])
            year_options = [{'label': i, 'value': i} for i in available_years]
            message = f"Data for {DEFAULT_TICKER} retrieved from {result.get('source', 'database')}!"
            return df_json, message, available_years, year_options, available_years[-1] if available_years else None
        return None, "Please load stock data by clicking the 'Load Stock Data' button", None, [], None

    if n_clicks is None:
        raise dash.exceptions.PreventUpdate

    if not ticker:
        return None, "Please enter a valid ticker symbol", None, [], None

    try:
        payload = {"ticker": ticker.upper(), "start_date": start_date, "end_date": end_date}
        response = requests.post(f"{API_URL}/stock/load", json=payload)

        if response.status_code != 200:
            return None, response.json().get('message', 'Unknown error occurred'), None, [], None

        result = response.json()
        if not result.get('success', False):
            return None, result.get('message', 'Failed to load data'), None, [], None

        df_json = result.get('data')
        available_years = result.get('available_years', [])
        year_options = [{'label': i, 'value': i} for i in available_years]
        message = f"Data for {ticker.upper()} loaded from {result.get('source', 'unknown')}!"
        return df_json, message, available_years, year_options, available_years[-1] if available_years else None

    except Exception as e:
        return None, f"Error loading data: {str(e)}", None, [], None


@app.callback(
    Output('select-year', 'disabled'),
    Input('stat-select', 'value')
)
def toggle_year_dropdown(stat_type):
    return stat_type == 'All Years Statistics'


@app.callback(
    Output('output-container', 'children'),
    [Input('stock-data-store', 'data'),
     Input('stat-select', 'value'),
     Input('select-year', 'value'),
     Input('ticker-input', 'value')]
)
def update_output(json_data, stat_type, year, ticker):
    if json_data is None:
        return html.Div("Please load stock data first.")

    df2 = pd.read_json(json_data, orient='split')
    stock_name = ticker.upper() if ticker else "Stock"

    # The same charting code as before...
    # (Keep your candlestick, volume, daily return, drawdown logic here)

    return html.Div(f"Charts for {stock_name} will appear here.")  # Placeholder


# --- Helper function ---
def check_ticker_data(ticker):
    try:
        response = requests.get(f"{API_URL}/stock/data/{ticker}")
        if response.status_code == 200 and response.json().get('success', False):
            return response.json()
        return None
    except:
        return None


# --- Main entry for local dev ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
