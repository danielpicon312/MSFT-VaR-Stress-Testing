import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'risk.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Orders date and close by date in ascending order
prices_df = pd.read_sql_query('SELECT date, close FROM msft_stock ORDER BY date ASC', conn)

prices_df['date'] = pd.to_datetime(prices_df['date'])
prices_df = prices_df.set_index('date')

# Hypothetical MSFT holdings
msft_holdings = 100000

# Calculate Daily and Annualized Volatility
daily_returns = prices_df['close'].pct_change().dropna()
daily_vol = daily_returns.std()
annualized_vol = daily_vol * np.sqrt(252)
print(f'\nDaily Volatility: {np.round(daily_vol*100, decimals=2)}%, Annual Volatility: {np.round(annualized_vol*100, decimals=2)}%')

# Calculate VaR (Value at Risk)
h_var_95 = -np.percentile(daily_returns, 5) # 5th percentile
h_var_99 = -np.percentile(daily_returns, 1) # 1st percentile

# Hypothetical Value of $100,000 in MSFT holdings
h_var_95_price = msft_holdings * h_var_95
h_var_99_price = msft_holdings * h_var_99

print(f'\nOn a ${msft_holdings:,} MSFT position, 1-day 95% VaR = ${h_var_95_price:,.2f}')
print(f'On a ${msft_holdings:,} MSFT position, 1-day 99% VaR = ${h_var_99_price:,.2f}')

mean_return = np.mean(daily_returns)

z_score_05 = stats.norm.ppf(0.05)
z_score_01 = stats.norm.ppf(0.01)

p_var_05 = -(mean_return + z_score_05 * daily_vol)
p_var_01 = -(mean_return + z_score_01 * daily_vol)

p_var_05_price = msft_holdings * p_var_05
p_var_01_price = msft_holdings * p_var_01

print('\n1-Day VaR on a $100,000 MSFT position')
print('Confidence      Parametric              Historical')
print(f'95%             {(p_var_05_price/msft_holdings):.2%}  (${p_var_05_price:,.2f})      {(h_var_95_price/msft_holdings):.2%}  (${h_var_95_price:,.2f})')
print(f'99%             {(p_var_01_price/msft_holdings):.2%}  (${p_var_01_price:,.2f})      {(h_var_99_price/msft_holdings):.2%}  (${h_var_99_price:,.2f})\n')

daily_returns_kurtosis = daily_returns.kurt()
print(f'Excess kurtosis: {daily_returns_kurtosis:.2f}\n')