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
server = app.server  # For Gunicorn / Render

# Layout
app.layout = html.Div([
    html.H1("Stock Dashboard", style={'textAlign': 'center', 'color': '#003366'}),

    html.Div([
        html.Div([
            html.Label("Stock Ticker:"),
            dcc.Input(id='ticker-input', type='text', value=DEFAULT_TICKER, style={'width': '100%'}),
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label("Start Date:"),
            dcc.DatePickerSingle(id='start-date-picker', date=DEFAULT_START_DATE,
                                 display_format='YYYY-MM-DD', style={'width': '100%'})
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Div([
            html.Label("End Date:"),
            dcc.DatePickerSingle(id='end-date-picker', date=DEFAULT_END_DATE,
                                 display_format='YYYY-MM-DD', style={'width': '100%'})
        ], style={'width': '30%', 'display': 'inline-block', 'padding': '10px'}),

        html.Button("Load Stock Data", id='load-btn', n_clicks=0,
                    style={'width': '100%', 'margin-top': '10px', 'background-color': '#003366', 'color': 'white'})
    ], style={'border': '1px solid #ddd', 'padding': '10px', 'border-radius': '5px', 'margin-bottom': '20px'}),

    html.Div(id='data-message', style={'margin': '10px 0', 'color': 'green'}),

    html.Div([
        html.Label("Statistics Type:"),
        dcc.Dropdown(id='stat-select', options=[
            {'label': 'Yearly Statistics', 'value': 'yearly'},
            {'label': 'All Years Statistics', 'value': 'all'}
        ], value='yearly'),
    ], style={'width': '30%', 'padding': '10px'}),

    html.Div([
        html.Label("Select Year:"),
        dcc.Dropdown(id='year-select', style={'width': '30%', 'padding': '10px'})
    ]),

    dcc.Store(id='stock-store'),
    html.Div(id='graph-container', style={'padding': '20px'})
])


# --- Load stock data ---
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
    if not ticker:
        return None, "Enter a valid ticker.", [], None
    try:
        resp = requests.post(f"{API_URL}/stock/load",
                             json={"ticker": ticker.upper(), "start_date": start, "end_date": end})
        result = resp.json()

        if not result.get("success"):
            return None, result.get("message", "Failed to load data"), [], None

        # --- SAFELY convert to DataFrame ---
        data = result.get('data', [])
        if isinstance(data, str):
            # If API returns JSON string
            data = pd.read_json(data, orient='split').to_dict(orient='records')
        df = pd.DataFrame(data)
        if df.empty:
            return None, f"No data returned for {ticker.upper()}", [], None

        df_json = df.to_json(orient='split')
        years = sorted(result.get('available_years', df['date'].apply(lambda x: pd.to_datetime(x).year).unique()))
        year_options = [{'label': y, 'value': y} for y in years]
        return df_json, f"Data for {ticker.upper()} loaded!", year_options, years[-1] if years else None

    except Exception as e:
        return None, f"Error loading data: {str(e)}", [], None


# --- Enable/disable year dropdown ---
@app.callback(
    Output('year-select', 'disabled'),
    Input('stat-select', 'value')
)
def disable_year_dropdown(stat_type):
    return stat_type == 'all'


# --- Update charts ---
@app.callback(
    Output('graph-container', 'children'),
    [Input('stock-store', 'data'),
     Input('stat-select', 'value'),
     Input('year-select', 'value'),
     Input('ticker-input', 'value')]
)
def update_graph(json_data, stat_type, year, ticker):
    if not json_data:
        return html.Div("Please load stock data first.")

    df = pd.read_json(json_data, orient='split')
    df['date'] = pd.to_datetime(df['date'])
    stock_name = ticker.upper() if ticker else "Stock"

    graphs = []

    if stat_type == 'all':
        start_year, end_year = df['date'].dt.year.min(), df['date'].dt.year.max()
        # Candlestick
        fig1 = go.Figure(data=[go.Candlestick(
            x=df['date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Adj Close']
        )])
        fig1.update_layout(title=f"{stock_name} Candlestick ({start_year}-{end_year})",
                           xaxis_title="Date", yaxis_title="Price", xaxis_rangeslider_visible=True,
                           width=1900, height=700)
        graphs.append(dcc.Graph(figure=fig1))

        # Volume
        df['Year'] = df['date'].dt.year
        yearly_volume = df.groupby('Year')['Volume'].mean().reset_index()
        fig2 = px.area(yearly_volume, x='Year', y='Volume',
                       title=f"{stock_name} Avg Trading Volume per Year ({start_year}-{end_year})",
                       width=1900, height=700, markers=True)
        graphs.append(dcc.Graph(figure=fig2))

        # Daily Returns
        df['daily_return'] = df['Adj Close'].pct_change() * 100
        yearly_return = df.groupby('Year')['daily_return'].mean().reset_index()
        yearly_return['return_category'] = yearly_return['daily_return'].apply(lambda x: 'Positive' if x > 0 else 'Negative')
        fig3 = px.bar(yearly_return, x='Year', y='daily_return', color='return_category',
                      color_discrete_map={'Positive': 'green', 'Negative': 'red'},
                      title=f"{stock_name} Avg Daily Returns ({start_year}-{end_year})",
                      width=1900, height=700)
        fig3.update_layout(yaxis_title="Percent Daily Return (%)", xaxis_title="Year")
        graphs.append(dcc.Graph(figure=fig3))

        # Drawdowns
        df['Cumulative Max'] = df['Adj Close'].cummax()
        df['Drawdown'] = (df['Adj Close'] / df['Cumulative Max'] - 1) * 100
        fig4 = px.area(df, x='date', y='Drawdown', title=f"{stock_name} Drawdowns ({start_year}-{end_year})",
                       width=1900, height=700)
        graphs.append(dcc.Graph(figure=fig4))

    elif stat_type == 'yearly' and year:
        df_year = df[df['date'].dt.year == year]
        if df_year.empty:
            return html.Div(f"No data available for {stock_name} in {year}.")

        # Candlestick
        fig1 = go.Figure(data=[go.Candlestick(
            x=df_year['date'], open=df_year['Open'], high=df_year['High'],
            low=df_year['Low'], close=df_year['Adj Close']
        )])
        fig1.update_layout(title=f"{stock_name} Candlestick ({year})",
                           xaxis_title="Date", yaxis_title="Price", xaxis_rangeslider_visible=True,
                           width=1900, height=700)
        graphs.append(dcc.Graph(figure=fig1))

        # Volume
        fig2 = px.area(df_year, x='date', y='Volume',
                       title=f"{stock_name} Daily Trading Volume ({year})",
                       width=1900, height=700)
        fig2.update_layout(xaxis_title="Date")
        graphs.append(dcc.Graph(figure=fig2))

        # Daily Returns
        df_year['daily_return'] = df_year['Adj Close'].pct_change() * 100
        daily_return = df_year.groupby('date')['daily_return'].mean().reset_index()
        daily_return['return_category'] = daily_return['daily_return'].apply(lambda x: 'Positive' if x > 0 else 'Negative')
        fig3 = px.bar(daily_return, x='date', y='daily_return', color='return_category',
                      color_discrete_map={'Positive': 'green', 'Negative': 'red'},
                      title=f"{stock_name} Daily Returns ({year})",
                      width=1900, height=700)
        fig3.update_layout(yaxis_title="Percent Daily Return (%)", xaxis_title="Date")
        graphs.append(dcc.Graph(figure=fig3))

        # Drawdowns
        df_year['Cumulative Max'] = df_year['Adj Close'].cummax()
        df_year['Drawdown'] = (df_year['Adj Close'] / df_year['Cumulative Max'] - 1) * 100
        fig4 = px.area(df_year, x='date', y='Drawdown', title=f"{stock_name} Drawdowns ({year})",
                       width=1900, height=700)
        graphs.append(dcc.Graph(figure=fig4))

    return graphs


# --- Run server ---
if __name__ == "__main__":
    app.run_server(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
