import pandas as pd
import datetime
from datetime import date
import requests
import os
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

# -------------------
# Display settings
# -------------------
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)

# -------------------
# Default values
# -------------------
DEFAULT_TICKER = "TSLA"
DEFAULT_START_DATE = "2010-06-29"
DEFAULT_END_DATE = date.today().strftime("%Y-%m-%d")

# -------------------
# API endpoint (Render URL)
# -------------------
API_URL = os.environ.get("API_URL", "https://stock-api-bj3r.onrender.com/api")

# -------------------
# Dash app
# -------------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # expose Flask server for Render

# -------------------
# Dropdown options
# -------------------
dropdown_options = [
    {'label': 'Yearly Statistics', 'value': 'Yearly Statistics'},
    {'label': 'All Years Statistics', 'value': 'All Years Statistics'}
]

# Initial year list
current_year = datetime.datetime.now().year
year_list = [i for i in range(2010, current_year + 1)]

# -------------------
# Layout
# -------------------
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

    # Store data in browser
    dcc.Store(id='stock-data-store'),
    dcc.Store(id='years-available'),
])

# -------------------
# Helper function
# -------------------
def get_stock_data_from_api(ticker, start_date, end_date):
    try:
        payload = {
            "ticker": ticker.upper(),
            "start_date": start_date,
            "end_date": end_date
        }
        response = requests.post(f"{API_URL}/stock/load", json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            return {"success": False, "message": f"API returned {response.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# -------------------
# Callbacks
# -------------------
@app.callback(
    [Output('stock-data-store', 'data'),
     Output('data-loaded-message', 'children'),
     Output('years-available', 'data'),
     Output('select-year', 'options'),
     Output('select-year', 'value')],
    [Input('submit-button', 'n_clicks')],
    [State('ticker-input', 'value'),
     State('start-date-picker', 'date'),
     State('end-date-picker', 'date')]
)
def load_stock_data(n_clicks, ticker, start_date, end_date):
    import dash
    if n_clicks is None or not ticker:
        raise dash.exceptions.PreventUpdate

    result = get_stock_data_from_api(ticker, start_date, end_date)

    if not result.get("success", False):
        return None, f"Error: {result.get('message')}", None, [], None

    df_json = result.get('data')
    available_years = result.get('available_years', [])
    year_options = [{'label': i, 'value': i} for i in available_years]

    message = f"Data for {ticker.upper()} loaded from {result.get('source', 'unknown')}!"

    return df_json, message, available_years, year_options, available_years[-1] if available_years else None

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

    # Placeholder chart area
    return html.Div(f"Charts for {stock_name} will appear here.")

# -------------------
# Main entry
# -------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=True)
