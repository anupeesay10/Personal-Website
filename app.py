import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
import requests
import os

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State

# Default values
DEFAULT_TICKER = "TSLA"
DEFAULT_START_DATE = "2010-06-29"
DEFAULT_END_DATE = date.today().strftime("%Y-%m-%d")

# API endpoint
API_URL = os.environ.get("API_URL", "https://stock-api-bj3r.onrender.com/api")

# Dash app
app = dash.Dash(__name__, suppress_callback_exceptions=True)
server = app.server

# Dropdown options
dropdown_options = [
    {'label': 'Yearly Statistics', 'value': 'Yearly Statistics'},
    {'label': 'All Years Statistics', 'value': 'All Years Statistics'}
]

# Year list
current_year = date.today().year
year_list = list(range(2010, current_year + 1))

# --- Layout ---
app.layout = html.Div([
    html.H1("Stock Dashboard", style={'textAlign': 'center'}),

    html.Div([
        html.Div([
            html.Label("Enter Stock Ticker:"),
            dcc.Input(id='ticker-input', type='text', value=DEFAULT_TICKER, style={'width': '100%', 'padding': '8px'})
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label("Start Date:"),
            dcc.DatePickerSingle(id='start-date-picker', date=DEFAULT_START_DATE, display_format='YYYY-MM-DD')
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label("End Date:"),
            dcc.DatePickerSingle(id='end-date-picker', date=DEFAULT_END_DATE, display_format='YYYY-MM-DD')
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Button('Load Stock Data', id='submit-button', n_clicks=0, style={'margin-top': '20px'})
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

    html.Div(id='output-container', style={'padding': '20px'}),

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

    # Initialization
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

    if not start_date or not end_date:
        return None, "Please select both start and end dates", None, [], None

    try:
        payload = {"ticker": ticker.upper(), "start_date": start_date, "end_date": end_date}
        response = requests.post(f"{API_URL}/stock/load", json=payload, timeout=10)
        try:
            result = response.json()
        except ValueError:
            return None, "API did not return valid JSON. Make sure backend is running.", None, [], None

        if response.status_code != 200:
            return None, result.get('message', 'Unknown error occurred'), None, [], None

        if not result.get('success', False):
            return None, result.get('message', 'Failed to load data'), None, [], None

        df_json = result.get('data')
        available_years = result.get('available_years', [])
        year_options = [{'label': i, 'value': i} for i in available_years]
        message = f"Data for {ticker.upper()} loaded from {result.get('source', 'unknown')}!"
        return df_json, message, available_years, year_options, available_years[-1] if available_years else None

    except requests.exceptions.RequestException as e:
        return None, f"Error contacting API: {str(e)}", None, [], None
    except Exception as e:
        return None, f"Unexpected error: {str(e)}", None, [], None


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

    try:
        df2 = pd.read_json(json_data, orient='split')
    except ValueError:
        return html.Div("Error parsing stock data. Please reload.")

    df2['date'] = pd.to_datetime(df2['date'])
    price_col = 'Adj Close' if 'Adj Close' in df2.columns else 'Close'

    for col in ['Open', 'High', 'Low', 'Close', 'Volume', price_col]:
        if col in df2.columns:
            df2[col] = pd.to_numeric(df2[col], errors='coerce')

    stock_name = ticker.upper() if ticker else "Stock"

    # --- All Years Statistics ---
    if stat_type == 'All Years Statistics':
        start_year, end_year = df2['date'].dt.year.min(), df2['date'].dt.year.max()

        fig1 = go.Figure(data=[go.Candlestick(
            x=df2['date'], open=df2['Open'], high=df2['High'],
            low=df2['Low'], close=df2[price_col]
        )])
        fig1.update_layout(title=f'{stock_name} Candlestick ({start_year}-{end_year})',
                           yaxis_title='Price', xaxis_title='Date', xaxis_rangeslider_visible=True,
                           width=1900, height=700)

        df2['Year'] = df2['date'].dt.year
        yearly_volume = df2.groupby('Year')['Volume'].mean().reset_index()
        fig2 = px.area(yearly_volume, x='Year', y='Volume',
                       title=f'Average {stock_name} Trading Volume Per Year ({start_year}-{end_year})',
                       width=1900, height=700, markers=True)
        fig2.update_layout(xaxis_title='Year')

        df2['daily_return'] = df2[price_col].pct_change() * 100
        yearly_return = df2.groupby('Year')['daily_return'].mean().reset_index()
        yearly_return['return_category'] = yearly_return['daily_return'].apply(
            lambda x: 'Positive' if x > 0 else 'Negative')
        fig3 = px.bar(yearly_return, x='Year', y='daily_return', color='return_category',
                      color_discrete_map={'Positive': 'green', 'Negative': 'red'})
        fig3.update_layout(title=f'Average Daily Returns Per Year for {stock_name}',
                           yaxis_title='Percent Daily Return (%)', xaxis_title='Year',
                           legend_title_text="Return Category", width=1900, height=700)

        df2['Cumulative Max'] = df2[price_col].cummax()
        df2['Drawdown'] = (df2[price_col] / df2['Cumulative Max'] - 1) * 100
        fig4 = px.area(df2, x='date', y='Drawdown', title=f'{stock_name} Drawdowns Over All Years')
        fig4.update_layout(yaxis_title='Percent Drawdown (%)', xaxis_title='Date', width=1900, height=700)

        return [dcc.Graph(figure=fig1), dcc.Graph(figure=fig2),
                dcc.Graph(figure=fig3), dcc.Graph(figure=fig4)]

    # --- Yearly Statistics ---
    elif stat_type == 'Yearly Statistics' and year:
        year_data = df2[df2['date'].dt.year == int(year)]
        if year_data.empty:
            return html.Div(f"No data available for {stock_name} in {year}.")

        fig1 = go.Figure(data=[go.Candlestick(
            x=year_data['date'], open=year_data['Open'], high=year_data['High'],
            low=year_data['Low'], close=year_data[price_col]
        )])
        fig1.update_layout(title=f'{stock_name} Candlestick for {year}',
                           yaxis_title='Price', xaxis_title='Date', xaxis_rangeslider_visible=True,
                           width=1900, height=700)

        fig2 = px.area(year_data, x='date', y='Volume', title=f'{stock_name} Daily Trading Volume for {year}',
                       width=1900, height=700)
        fig2.update_layout(xaxis_title='Date')

        year_data['daily_return'] = year_data[price_col].pct_change() * 100
        year_data['return_category'] = year_data['daily_return'].apply(lambda x: 'Positive' if x > 0 else 'Negative')
        fig3 = px.bar(year_data, x='date', y='daily_return', color='return_category',
                      color_discrete_map={'Positive': 'green', 'Negative': 'red'})
        fig3.update_layout(title=f"{stock_name} Average Daily Returns for {year}",
                           yaxis_title='Percent Daily Return (%)', xaxis_title='Date',
                           legend_title_text="Return Category", width=1900, height=700)

        year_data['Cumulative Max'] = year_data[price_col].cummax()
        year_data['Drawdown'] = (year_data[price_col] / year_data['Cumulative Max'] - 1) * 100
        fig4 = px.area(year_data, x='date', y='Drawdown', title=f'{stock_name} Drawdowns for {year}')
        fig4.update_layout(yaxis_title='Percent Drawdown (%)', xaxis_title='Date', width=1900, height=700)

        return [dcc.Graph(figure=fig1), dcc.Graph(figure=fig2),
                dcc.Graph(figure=fig3), dcc.Graph(figure=fig4)]

    return html.Div("No data to display.")


# --- Helper ---
def check_ticker_data(ticker):
    try:
        response = requests.get(f"{API_URL}/stock/data/{ticker}", timeout=5)
        if response.status_code == 200 and response.json().get('success', False):
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None


# --- Main ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=True)
