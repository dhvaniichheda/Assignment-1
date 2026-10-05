"""
Assignment 1: Stock Analysis Streamlit App
Run with:  streamlit run assignment_1.py

All data retrieval and calculation goes through the Stock class in stock.py.
This file only handles the interface.
"""

import datetime as dt

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from stock import Stock

st.set_page_config(page_title="Stock Analysis App", layout="wide")


# ---------------------------------------------------------------------------
# Cached data loader: creating a Stock IS the data fetch, so we cache it.
# Every argument becomes part of the cache key, so changing the ticker,
# dates, or MA window triggers a fresh fetch; anything else reuses the cache.
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_stock(ticker, start, end, ma_window, ma_long):
    return Stock(ticker, start=start, end=end, ma_window=ma_window, ma_long=ma_long)


# ---------------------------------------------------------------------------
# Shared sidebar (used by both tabs)
# ---------------------------------------------------------------------------
st.sidebar.header("Settings")

ticker = st.sidebar.text_input("Ticker symbol", value="AAPL").strip().upper()

today = dt.date.today()
start_date = st.sidebar.date_input(
    "Start date", value=today - dt.timedelta(days=365), max_value=today
)
end_date = st.sidebar.date_input("End date", value=today, max_value=today)

ma_window = st.sidebar.slider(
    "Short moving average window (days)", min_value=5, max_value=200, value=20
)
ma_long = st.sidebar.slider(
    "Long moving average window (days)", min_value=5, max_value=200, value=50
)
if ma_window >= ma_long:
    st.sidebar.warning("The long window should be larger than the short window.")

dates_ok = start_date < end_date
if not dates_ok:
    st.sidebar.error("Start date must be before end date.")

st.title("Stock Analysis App")
tab1, tab2 = st.tabs(["Single Stock Analysis", "Portfolio Comparison"])


# ---------------------------------------------------------------------------
# Tab 1: Single Stock Analysis
# ---------------------------------------------------------------------------
with tab1:
    st.header("Single Stock Analysis")

    # A Streamlit button is only True on the rerun right after the click.
    # Saving a flag in session_state keeps the results on screen when the
    # user moves the slider or changes a date afterwards.
    if st.button("Fetch data", key="fetch_single"):
        st.session_state["show_single"] = True

    if not st.session_state.get("show_single"):
        st.info("Set your options in the sidebar, then click **Fetch data**.")
    elif not ticker:
        st.warning("Please enter a ticker symbol.")
    elif not dates_ok:
        st.warning("Fix the date range in the sidebar.")
    else:
        with st.spinner(f"Fetching data for {ticker}..."):
            stock = load_stock(ticker, start_date, end_date, ma_window, ma_long)

        if stock.data is None:
            st.error(stock.message)
        else:
            st.success(stock.message)
            data = stock.data

            # ---- Metrics ------------------------------------------------
            last_close = data["Close"].iloc[-1]
            last_change = data["change"].iloc[-1]
            cum_log_return = data["return"].sum()
            cum_simple_return = np.exp(cum_log_return) - 1
            trading_days = len(data)
            daily_vol = data["return"].std()

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Last close", f"${last_close:,.2f}", f"{last_change:+.2f}")
            c2.metric("Cumulative return", f"{cum_simple_return:.2%}")
            c3.metric("Trading days", f"{trading_days}")
            c4.metric("Daily volatility (std of return)", f"{daily_vol:.4f}")

            # ---- Price + moving average chart (built in the app) --------
            longest = max(ma_window, ma_long)
            if longest >= trading_days:
                st.warning(
                    f"The {longest} day window is longer than the {trading_days} "
                    "trading days in your range, so that moving average line will be empty. "
                    "Pick a wider date range or a smaller window."
                )

            price_fig = go.Figure()
            price_fig.add_trace(
                go.Scatter(x=data.index, y=data["Close"], mode="lines", name="Close")
            )
            price_fig.add_trace(
                go.Scatter(
                    x=data.index, y=data["MA"], mode="lines", name=f"{ma_window} day MA"
                )
            )
            price_fig.add_trace(
                go.Scatter(
                    x=data.index, y=data["MA_long"], mode="lines", name=f"{ma_long} day MA"
                )
            )
            price_fig.update_layout(
                title=f"{ticker} Close Price with {ma_window} and {ma_long} Day Moving Averages",
                xaxis_title="Date",
                yaxis_title="Price ($)",
                hovermode="x unified",
            )
            st.plotly_chart(price_fig)

            # ---- Charts produced by the class ---------------------------
            col_a, col_b = st.columns(2)
            with col_a:
                st.plotly_chart(stock.plot_performance())
            with col_b:
                st.plotly_chart(stock.plot_return_dist())

            # ---- Summary statistics table -------------------------------
            st.subheader("Summary statistics for daily log return")
            stats = data["return"].describe().to_frame(name="return")
            st.dataframe(stats)


# ---------------------------------------------------------------------------
# Tab 2: Portfolio Comparison
# ---------------------------------------------------------------------------
with tab2:
    st.header("Portfolio Comparison")
    st.caption("Uses the start and end dates from the sidebar.")

    tickers_text = st.text_input(
        "Ticker symbols (comma separated)", value="AAPL, MSFT, GOOG"
    )

    if st.button("Compare", key="fetch_portfolio"):
        st.session_state["show_portfolio"] = True

    # Clean the input: split on commas, strip spaces, uppercase, drop blanks
    # and duplicates while keeping the order the user typed.
    tickers = list(
        dict.fromkeys(t.strip().upper() for t in tickers_text.split(",") if t.strip())
    )

    if not st.session_state.get("show_portfolio"):
        st.info("Enter tickers above, then click **Compare**.")
    elif not tickers:
        st.warning("Please enter at least one ticker symbol.")
    elif not dates_ok:
        st.warning("Fix the date range in the sidebar.")
    else:
        with st.spinner("Fetching portfolio data..."):
            stocks = {t: load_stock(t, start_date, end_date, ma_window, ma_long) for t in tickers}

        performance = {}
        for t, s in stocks.items():
            if s.data is None:
                # Show why this ticker failed, then keep going with the rest.
                st.error(f"{t}: {s.message}")
                continue

            # Zero based cumulative log return built from the return column.
            # cumsum() alone would start at the first day's return, not 0.
            # Subtracting the first value makes every line start at exactly 0.0
            # and each later point equals log(Close_t / Close_first_day).
            cum = s.data["return"].fillna(0).cumsum()
            cum = cum - cum.iloc[0]
            performance[t] = cum

        if performance:
            perf_df = pd.DataFrame(performance)

            port_fig = go.Figure()
            for t in perf_df.columns:
                port_fig.add_trace(
                    go.Scatter(x=perf_df.index, y=perf_df[t], mode="lines", name=t)
                )
            port_fig.add_hline(y=0, line_dash="dot", line_color="gray")
            port_fig.update_layout(
                title="Zero Based Cumulative Performance (cumulative log return)",
                xaxis_title="Date",
                yaxis_title="Cumulative log return",
                legend_title="Ticker",
                hovermode="x unified",
            )
            st.plotly_chart(port_fig)

            # Proof that every line starts at 0.0 on the first day
            first_values = {t: float(perf_df[t].dropna().iloc[0]) for t in perf_df.columns}
            st.caption(
                "Starting value of each line: "
                + ", ".join(f"{t} = {v:.4f}" for t, v in first_values.items())
            )

            # Helper for the write up: where do two lines cross?
            if len(perf_df.columns) == 2:
                a, b = perf_df.columns
                diff = (perf_df[a] - perf_df[b]).dropna()
                sign = np.sign(diff)
                crossings = diff.index[(sign != sign.shift()) & sign.shift().notna() & (sign != 0)]
                with st.expander("Dates where the two lines cross"):
                    if len(crossings) == 0:
                        st.write("These two lines never cross in this range. Try a different pair.")
                    else:
                        st.write([d.strftime("%Y-%m-%d") for d in crossings])

            with st.expander("Daily returns for each ticker"):
                returns_df = pd.DataFrame(
                    {t: s.data["return"] for t, s in stocks.items() if s.data is not None}
                )
                st.dataframe(returns_df)