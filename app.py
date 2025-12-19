import dash
from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
import pandas as pd
import requests
import json
from datetime import date

# ------------------------------
# Colors from your HTML theme
# ------------------------------
colors = {
    'primary_bg': '#0a0e27',
    'secondary_bg': '#111630',
    'tertiary_bg': '#1a1f3a',
    'text_primary': '#ffffff',
    'text_secondary': '#b0b5c4',
    'accent': '#6366f1',
    'accent_light': '#818cf8',
    'border_color': '#2a2f4d',
    'positive': 'green',
    'negative': 'red',
    'volume_line': '#003366',
    'drawdown_line': '#ff6666'
}

API_URL = 'http://localhost:5001/api'  # adjust if needed

# ------------------------------
# Dash App
# ------------------------------
app = dash.Dash(__name__)
server = app.server

today = date.today().isoformat()

app.layout = html.Div(
    style={'backgroundColor': colors['primary_bg'], 'color': colors['text_primary'], 'padding': '20px',
           'fontFamily': 'Arial, sans-serif'},
    children=[
        html.H1("Stock Dashboard", style={
            'textAlign': 'center',
            'marginBottom': '30px',
            'fontSize': '2.5em',
            'background': f"linear-gradient(135deg, {colors['text_primary']}, {colors['text_secondary']})",
            '-webkit-background-clip': 'text',
            '-webkit-text-fill-color': 'transparent'
        }),

        # Controls
        html.Div(
            style={'backgroundColor': colors['tertiary_bg'], 'border': f'1px solid {colors["border_color"]}',
                   'borderRadius': '8px', 'padding': '20px', 'marginBottom': '20px'},
            children=[
                html.Div(
                    style={'display': 'grid', 'gridTemplateColumns': 'repeat(auto-fit, minmax(250px, 1fr))',
                           'gap': '20px', 'marginBottom': '20px'},
                    children=[
                        html.Div([
                            html.Label("Enter Stock Ticker:", style={'marginBottom': '8px'}),
                            dcc.Input(id='ticker-input', type='text', value='TSLA',
                                      style={'padding': '10px', 'borderRadius': '6px',
                                             'border': f'1px solid {colors["border_color"]}',
                                             'backgroundColor': colors['primary_bg'], 'color': colors['text_primary']})
                        ]),
                        html.Div([
                            html.Label("Start Date:", style={'marginBottom': '8px'}),
                            dcc.Input(id='start-date-input', type='date', value='2010-06-29',
                                      style={'padding': '10px', 'borderRadius': '6px',
                                             'border': f'1px solid {colors["border_color"]}',
                                             'backgroundColor': colors['primary_bg'], 'color': colors['text_primary']})
                        ]),
                        html.Div([
                            html.Label("End Date:", style={'marginBottom': '8px'}),
                            dcc.Input(id='end-date-input', type='date', value=today,
                                      style={'padding': '10px', 'borderRadius': '6px',
                                             'border': f'1px solid {colors["border_color"]}',
                                             'backgroundColor': colors['primary_bg'], 'color': colors['text_primary']})
                        ])
                    ]
                ),

                html.Div(
                    style={'display': 'flex', 'gap': '10px', 'marginTop': '20px'},
                    children=[
                        html.Button("Load Stock Data", id='load-button', n_clicks=0,
                                    style={'padding': '12px 20px', 'backgroundColor': colors['accent'],
                                           'color': 'white',
                                           'border': 'none', 'borderRadius': '6px', 'cursor': 'pointer'}),
                        html.Button("Clear", id='clear-button', n_clicks=0,
                                    style={'padding': '12px 20px', 'backgroundColor': colors['border_color'],
                                           'color': 'white',
                                           'border': 'none', 'borderRadius': '6px', 'cursor': 'pointer'})
                    ]
                ),

                html.Div(id='message', style={'marginTop': '15px'})
            ]
        ),

        # Statistics Controls
        html.Div(
            id='statistics-controls',
            style={'display': 'none', 'gridTemplateColumns': 'repeat(auto-fit, minmax(250px, 1fr))', 'gap': '20px',
                   'marginBottom': '20px'},
            children=[
                html.Div([
                    html.Label("Select Statistics:"),
                    dcc.Dropdown(
                        id='stat-select',
                        options=[
                            {'label': 'Yearly Statistics', 'value': 'Yearly Statistics'},
                            {'label': 'All Years Statistics', 'value': 'All Years Statistics'}
                        ],
                        value='Yearly Statistics',
                        style={'backgroundColor': colors['primary_bg'], 'color': colors['text_primary']}
                    )
                ]),
                html.Div([
                    html.Label("Select Year:"),
                    dcc.Dropdown(
                        id='year-select',
                        style={'backgroundColor': colors['primary_bg'], 'color': colors['text_primary']}
                    )
                ])
            ]
        ),

        # Charts Container
        html.Div(id='charts-container', style={'marginTop': '30px'})
    ]
)


# ------------------------------
# Callbacks
# ------------------------------
@app.callback(
    Output('message', 'children'),
    Output('statistics-controls', 'style'),
    Output('year-select', 'options'),
    Output('charts-container', 'children'),
    Input('load-button', 'n_clicks'),
    State('ticker-input', 'value'),
    State('start-date-input', 'value'),
    State('end-date-input', 'value'),
    prevent_initial_call=True
)
def load_stock_data(n_clicks, ticker, start_date, end_date):
    if not ticker:
        return "Please enter a valid ticker symbol", {'display': 'none'}, [], []

    try:
        response = requests.post(f"{API_URL}/stock/load", json={
            "ticker": ticker.upper(),
            "start_date": start_date,
            "end_date": end_date
        }, timeout=10)
        data = response.json()
        if not response.ok or not data.get('success'):
            return data.get('message', 'Failed to load data'), {'display': 'none'}, [], []

        df = pd.DataFrame(data['data'])
        df['date'] = pd.to_datetime(df['date'])
        available_years = sorted(df['date'].dt.year.unique(), reverse=True)

        # Prepare year dropdown options
        year_options = [{'label': str(y), 'value': y} for y in available_years]

        # Initial charts (latest year)
        children = render_yearly_charts(df, ticker.upper(), available_years[0])

        return f"Data for {ticker.upper()} loaded successfully!", {'display': 'grid',
                                                                   'gridTemplateColumns': 'repeat(auto-fit, minmax(250px, 1fr))',
                                                                   'gap': '20px'}, year_options, children
    except Exception as e:
        return f"Error loading data: {e}", {'display': 'none'}, [], []


# ------------------------------
# Helper functions for charts
# ------------------------------
def render_yearly_charts(df, ticker, year):
    year_df = df[df['date'].dt.year == year]
    if year_df.empty:
        return [html.Div(f"No data available for {ticker} in {year}", style={'color': colors['text_secondary']})]

    charts = []

    # Candlestick
    candlestick = go.Figure(data=[go.Candlestick(
        x=year_df['date'],
        open=year_df['Open'],
        high=year_df['High'],
        low=year_df['Low'],
        close=year_df['Adj Close']
    )])
    candlestick.update_layout(
        title=f"{ticker} Stock Candlestick Chart for {year}",
        yaxis_title='Price',
        xaxis_title='Date',
        plot_bgcolor=colors['secondary_bg'],
        paper_bgcolor=colors['secondary_bg'],
        font_color=colors['text_primary'],
        height=700
    )
    charts.append(dcc.Graph(figure=candlestick))

    # Volume
    volume = go.Figure(data=[go.Scatter(
        x=year_df['date'],
        y=year_df['Volume'],
        mode='lines',
        line={'color': colors['volume_line']},
        fill='tozeroy'
    )])
    volume.update_layout(
        title=f"{ticker} Daily Trading Volume for {year}",
        yaxis_title='Volume',
        xaxis_title='Date',
        plot_bgcolor=colors['secondary_bg'],
        paper_bgcolor=colors['secondary_bg'],
        font_color=colors['text_primary'],
        height=700
    )
    charts.append(dcc.Graph(figure=volume))

    # Daily returns
    daily_returns = ((year_df['Adj Close'].pct_change()) * 100).fillna(0)
    colors_list = [colors['positive'] if v >= 0 else colors['negative'] for v in daily_returns]
    returns_fig = go.Figure(data=[go.Bar(
        x=year_df['date'],
        y=daily_returns,
        marker_color=colors_list
    )])
    returns_fig.update_layout(
        title=f"{ticker} Daily Returns for {year}",
        yaxis_title='Percent Daily Return (%)',
        xaxis_title='Date',
        plot_bgcolor=colors['secondary_bg'],
        paper_bgcolor=colors['secondary_bg'],
        font_color=colors['text_primary'],
        height=700,
        showlegend=False
    )
    charts.append(dcc.Graph(figure=returns_fig))

    # Drawdowns
    cumulative_max = year_df['Adj Close'].cummax()
    drawdowns = ((year_df['Adj Close'] / cumulative_max - 1) * 100)
    drawdown_fig = go.Figure(data=[go.Scatter(
        x=year_df['date'],
        y=drawdowns,
        mode='lines',
        fill='tozeroy',
        line={'color': colors['drawdown_line']}
    )])
    drawdown_fig.update_layout(
        title=f"{ticker} Drawdowns for {year}",
        yaxis_title='Percent Drawdown (%)',
        xaxis_title='Date',
        plot_bgcolor=colors['secondary_bg'],
        paper_bgcolor=colors['secondary_bg'],
        font_color=colors['text_primary'],
        height=700
    )
    charts.append(dcc.Graph(figure=drawdown_fig))

    return charts


# ------------------------------
# Run server
# ------------------------------
if __name__ == '__main__':
    app.run_server(debug=True)

