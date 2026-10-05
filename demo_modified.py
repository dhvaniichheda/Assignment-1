from datetime import date,timedelta
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

END = date.today()
START = date.today() - timedelta(days=365)

st.set_page_config(layout="wide",
                   page_title="Stock Price Analysis")

st.title("Stock Analysis")

st.sidebar.title("Inputs")
ticker = st.sidebar.text_input("Enter a stock ticker symbol",
                               value="AAPL")
col1, col2 = st.sidebar.columns(2)
start_date = col1.date_input("Start Date", START)
end_date = col2.date_input("End Date", END)
mv_avg = st.sidebar.slider("Short Moving Average",
                           min_value=0,
                           max_value=100,
                           value=50,
                           step=1)
mv_avg_long = st.sidebar.slider("Long Moving Average",
                                min_value=0,
                                max_value=200,
                                value=100,
                                step=1)
run_analysis = st.sidebar.button("Run Analysis",
                                 type="primary")

def get_stock_data(ticker, start_date, end_date):
    try:
        data=yf.download(ticker, start_date, end_date)
        if data.empty:
            return None, f"No data for {ticker}"
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)
        return data, f"Successfully downloaded data for {ticker}"
    except Exception as e:
        return None, f"Download failed due to {e}"

if run_analysis:
    with st.spinner(f"Fetching {ticker} data..."):
        df, msg= get_stock_data(ticker, start_date, end_date)
        if df is not None:
            st.sidebar.success(msg)
        else:
            st.sidebar.error(msg)
            st.stop()
        df['MA']=df['Close'].rolling(window=mv_avg).mean()
        df['MA_long']=df['Close'].rolling(window=mv_avg_long).mean()
        df['pct_change']=df.Close.pct_change()
        tab1,tab2,tab3= st.tabs(['Chart','Statistics','Raw Data'])

        with tab1:
            st.subheader(f"{ticker} Price Analysis")
            col1,col2,col3 = st.columns(3)
            col1.metric("Last Price", f"{df.Close.iloc[-1]:.2f}")
            col2.metric("Cum. Change", f"{df.Close.iloc[-1]/df.Close.iloc[0]-1:.2%}")
            col3.metric("Trading Days", f"{df.Close.count()}")
            fig = px.line(df, y=['Close', 'MA', 'MA_long'])
            fig.update_layout(hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            st.subheader(f"{ticker} Summary Statistics")
            col1,col2=st.columns(2)
            with col1:
                st.write("*Daily Change Stats*")
                summary=df["pct_change"].describe()
                st.dataframe(summary)
            with col2:
                st.write("*Price Stats*")
                price_stats=pd.DataFrame({
                    'Metric':['High','Low','Mean','Volatility'],
                    'Values':[
                        f"{df.Close.max():.2f}",
                        f"{df.Close.min():.2f}",
                        f"{df.Close.mean():.2f}",
                        f"{df.Close.std():.2f}"
                    ]
                })
                st.dataframe(price_stats)

        with tab3:
            st.subheader(f"{ticker} Raw Data")
            csv_data = df.to_csv()
            st.download_button(
                label="Download Raw Data",
                data=csv_data,
                file_name=f"{ticker}.Raw_Data.csv",
                mime="text/csv",
            )