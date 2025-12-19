import pandas as pd
import datetime
from datetime import date
import requests
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import os

# -------------------------
# Config
# -------------------------
DEFAULT_TICKER = "TSLA"
DEFAULT_START_DATE = "2010-06-29"
DEFAULT_END_DATE = date.today().strftime("%Y-%m-%d")

API_URL = os.environ.get(
    "API_URL",
    "https://stock-api-bj3r.onrender.com/api"
)

# -------------------------
# Dash App
# -------------------------
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server  # REQUIRED for Render + Gunicorn

# -------------------------
# Layout
# -------------------------
app.layout = html.Div([
    html.H1("Stock Dashboard", style={'textAlign': 'center'}),

    html.Div([
        dcc.Input(
            id='ticker-input',
            type='text',
            value=DEFAULT_TICKER,
            placeholder="Ticker (e.g. TSLA)"
        ),
        dcc.DatePickerSingle(
            id='start-date-picker',
            date=DEFAULT_START_DATE
        ),
        dcc.DatePickerSingle(
            id='end-date-picker',
            date=DEFAULT_END_DATE
        ),
        html.Button("Load Stock Data", id='submit-button', n_clicks=0),
    ]),

    html.Div(id='data-loaded-message'),

    dcc.Dropdown(
        id='stat-select',
        options=[
            {'label': 'Yearly Statistics', 'value': 'year'},
            {'label': 'All Years Statistics', 'value': 'all'}
        ],
        value='year'
    ),

    dcc.Dropdown(id='select-year'),

    dcc.Store(id='stock-data-store'),
    html.Div(id='output-container')
])

# -------------------------
# Load Stock Data
# -------------------------
@app.callback(
    [
        Output('stock-data-store', 'data'),
        Output('data-loaded-message', 'children'),
        Output('select-year', 'options'),
        Output('select-year', 'value')
    ],
    Input('submit-button', 'n_clicks'),
    [
        State('ticker-input', 'value'),
        State('start-date-picker', 'date'),
        State('end-date-picker', 'date')
    ]
)
def load_stock_data(n_clicks, ticker, start_date, end_date):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate

    try:
        payload = {
            "ticker": ticker.upper(),
            "start_date": start_date,
            "end_date": end_date
        }

        r = requests.post(
            f"{API_URL}/stock/load",
            json=payload,
            timeout=30
        )

        if r.status_code != 200:
            return None, f"API error ({r.status_code})", [], None

        result = r.json()
        if not result.get("success"):
            return None, result.get("message", "Failed"), [], None

        years = result.get("available_years", [])
        year_options = [{'label': y, 'value': y} for y in years]

        return (
            result["data"],
            f"Loaded {ticker.upper()} data ✔",
            year_options,
            years[-1] if years else None
        )

    except Exception as e:
        return None, f"Error loading data: {str(e)}", [], None


# -------------------------
# Charts
# -------------------------
@app.callback(
    Output('output-container', 'children'),
    [
        Input('stock-data-store', 'data'),
        Input('select-year', 'value')
    ]
)
def update_charts(json_data, year):
    if not json_data:
        return "Please load stock data first."

    df = pd.read_json(json_data, orient='split')
    df['date'] = pd.to_datetime(df['date'])

    if year:
        df = df[df['date'].dt.year == year]

    return html.Div([
        html.P(f"Loaded {len(df)} rows"),
        html.Pre(df.head().to_string())
    ])


# -------------------------
# Local dev only
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
