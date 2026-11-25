import yfinance as yf

msft = yf.download("MSFT", start="2015-01-01")   # daily OHLCV, ends at the latest close
msft.to_csv("msft_daily.csv")