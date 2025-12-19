import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
import requests
import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import os

# Defaults
DEFAULT_TICKER = "TSLA"
DEFAULT_START_DATE = "2010-06-29"
DEFAULT_END_DATE = date.today().strftime("%Y-%m-%d")
API_URL = os.environ.get("API_URL", "https://stock-api-bj3r.onrender.com/api")

# Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Layout
app.layout = html.Div([
    html.H1("Stock Dashboard"),
    html.Div([
        html.Label("Ticker:"),
        dcc.Input(id='ticker-input', type='text', value=DEFAULT_TICKER),
        html.Label("Start Date:"),
        dcc.DatePickerSingle(id='start-date-picker', date=DEFAULT_START_DATE),
        html.Label("End Date:"),
        dcc.DatePickerSingle(id='end-date-picker', date=DEFAULT_END_DATE),
        html.Button("Load Stock Data", id='load-btn')
    ]),
    html.Div(id='data-message', style={'color': 'green'}),
    html.Label("Statistics Type:"),
    dcc.Dropdown(id='stat-select', options=[
        {'label': 'Yearly Statistics', 'value': 'yearly'},
        {'label': 'All Years Statistics', 'value': 'all'}
    ], value='yearly'),
    html.Label("Year:"),
    dcc.Dropdown(id='year-select'),
    dcc.Store(id='stock-store'),
    html.Div(id='graph-container')
])

# Load data
@app.callback(
    [Output('stock-store', 'data'),
     Output('data-message', 'children'),
     Output('year-select', 'options'),
     Output('year-select', 'value')],
    Input('load-btn', 'n_clicks'),
    [State('ticker-input', 'value'),
     State('start-date-picker', 'date'),
     State('end-date-picker', 'date')]
)
def load_stock(n_clicks, ticker, start, end):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate
    try:
        resp = requests.post(f"{API_URL}/stock/load",
                             json={"ticker": ticker.upper(), "start_date": start, "end_date": end})
        result = resp.json()
        if not result.get("success"):
            return None, "Failed to load data", [], None

        # Convert API list of dicts to DataFrame JSON
        df = pd.DataFrame(result['data'])
        df_json = df.to_json(orient='split')
        years = sorted(result.get('available_years', []))
        year_options = [{'label': y, 'value': y} for y in years]
        return df_json, f"Data for {ticker.upper()} loaded!", year_options, years[-1] if years else None
    except Exception as e:
        return None, f"Error: {str(e)}", [], None

# Enable/disable year dropdown
@app.callback(
    Output('year-select', 'disabled'),
    Input('stat-select', 'value')
)
def disable_year_dropdown(stat_type):
    return stat_type == 'all'

# Update graphs
@app.callback(
    Output('graph-container', 'children'),
    [Input('stock-store', 'data'),
     Input('stat-select', 'value'),
     Input('year-select', 'value'),
     Input('ticker-input', 'value')]
)
def update_graph(json_data, stat_type, year, ticker):
    if not json_data:
        return "Please load stock data first."
    df = pd.read_json(json_data, orient='split')
    df['date'] = pd.to_datetime(df['date'])
    stock_name = ticker.upper() if ticker else "Stock"

    if stat_type == 'all':
        fig = go.Figure(data=[go.Candlestick(
            x=df['date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Adj Close']
        )])
        fig.update_layout(title=f"{stock_name} Candlestick (All Years)")
        return dcc.Graph(figure=fig)
    else:
        df_year = df[df['date'].dt.year == year]
        if df_year.empty:
            return f"No data for {year}"
        fig = go.Figure(data=[go.Candlestick(
            x=df_year['date'], open=df_year['Open'], high=df_year['High'], low=df_year['Low'], close=df_year['Adj Close']
        )])
        fig.update_layout(title=f"{stock_name} Candlestick ({year})")
        return dcc.Graph(figure=fig)

if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))


