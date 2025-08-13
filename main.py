#import required libraries
import streamlit as st # pyright: ignore[reportMissingImports]
import pandas as pd
import plotly.graph_objects as go
import requests
from datetime import timedelta

#Streamlit Page Configuration
st.set_page_config(page_title="Stock Dashboard", layout="wide")

# API call and Data Transformation
def get_stock_data(symbol):
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&outputsize=full&apikey=YVNU3EHQSDVI5UF3'
    r = requests.get(url)
    data =  r.json()

    df = pd.DataFrame(data["Time Series (Daily)"]).transpose()
    df.index = pd.to_datetime(df.index)
    df.rename(columns={
        '1. open': 'open',
        '2. high': 'high',
        '3. low': 'low',
        '4. close': 'close',
        '5. volume': 'volume'
    }, inplace=True)
    df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
    df = df[::-1]
    df['50dma'] = df['close'].rolling(window=50).mean()
    return df

# Price Change Calculation Function
def calculate_price_change(df, days):
    end_price = df['close'].iloc[-1]
    if days == 'All':
        start_price = df['close'].iloc[0]
        start_date = df.index[0]
    else:
        try:
            days_map = {'1D': 1, '1W':7, '1M':30, '3M':90, '1Y':365, '5Y': 5*365}
            start_date = df.index[-1] - timedelta(days=days_map[days])
            df_filtered = df[df.index <= start_date]
            start_price = df_filtered['close'].iloc[-1]
        except:
            return None
    abs_change = end_price - start_price
    pct_change = (abs_change / start_price) * 100
    return {
        'start': start_date.date(),
        'end': df.index[-1].date(),
        'start_price': round(start_price, 2),
        'end_price': round(end_price, 2),
        'abs_change': round(abs_change, 2),
        'pct_change': round(pct_change, 2)
    }

#Streamlit Layout and Sidebar Inputs
st.title("Stock Dashboard")
st.markdown("Built by Chimezie, with Streamlit and Plotly / Data from Alpha Vantage")

with st.sidebar:
    st.header("Settings")
    symbol = st.text_input("Enter Stock Symbol", value="IBM")
    chart_type = st.selectbox("Select Chart Type", ["Candlestick", "Area"])
    period = st.selectbox("Select Time Period", ['1D', '1W', '1M', '3M', '1Y', '5Y'])

#Data Loading and Handling Missing Dates
if not symbol:
    st.warning("Enter a valid Stock Symbol in the textarea")
    st.stop()

with st.spinner("Loading Data..."):
    df = get_stock_data(symbol)

    start_date = df.index.min()
    end_date = df.index.max()
    full_date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    missing_dates = full_date_range.difference(df.index).to_list()
    missing_dates_str = [d.strftime('%Y-%m-%d') for d in missing_dates]

if df is None:
    st.error("Error retrieving data. Check Symbol")
    st.stop()

#Time-Based Filtering
if period != 'All':
    days_map = {'1D': 1, '1W': 7, '1M': 30, '3M': 90, '1Y': 365, '5Y': 5*365}
    days = days_map[period]
    df_period = df[df.index >= df.index[-1] - timedelta(days=days)]
else:
    df_period = df

#Price Metrics Display
price_change = calculate_price_change(df, period)
if price_change:
    col1, col2, col3 = st.columns(3)
    col1.metric("Start Price", f"${price_change['start_price']}")
    col2.metric("End Price", f"${price_change['end_price']}")
    delta_var = price_change['pct_change']
    col3.metric("Change", f"${price_change['abs_change']}", delta=f"{delta_var}%", delta_color="normal")

area_color = "green" if df_period["close"].iloc[-1] > df_period["close"].iloc[0] else "red"

#Chart Plotting with Plotly
fig = go.Figure()
if chart_type == "Candlestick":
    fig.add_trace(go.Candlestick(
        x=df_period.index,
        open=df_period["open"],
        high=df_period["high"],
        low=df_period["low"],
        close=df_period["close"],
        name='OHLC'
    ))
else:
    fig.add_trace(go.Scatter(
        x=df_period.index,
        y=df_period['close'],
        mode="lines",
        fill="tozeroy",
        line=dict(color=area_color, width=2),
        fillcolor=f"rgba(255, 0, 0, 0.2)" if area_color == "red" else "rgba(0, 255, 0, 0.2)",
        name="Price"
    ))


#Chart Customization and Missing Dates Handling
fig.update_layout(
    title=f"{symbol.upper()} {"Area" if chart_type == "Area" else 'Candlestick'} Price Chart",
    xaxis_title="Date",
    yaxis_title="Price (USD)",
    template="simple_white",
    height=600,
    xaxis=dict(
        rangebreaks=[dict(values=missing_dates_str)],
        rangeslider=dict(visible=False)
    ),
    showlegend=False
)

st.plotly_chart(fig)