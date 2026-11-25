import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / 'msft_daily.csv'
DB_PATH = BASE_DIR / 'risk.db'

# yfinance CSVs have 3 header rows (Price/Ticker/Date), so skip them and set names directlyprint("Loading Dataset...", flush=True)
col_names = ["Date", "Close", "High", "Low", "Open", "Volume", "Symbol"]
df = pd.read_csv(CSV_PATH, names=col_names, skiprows=3)

print("Cleaning dataset...", flush=True)
df = df.drop_duplicates(subset=['Date'])
df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d')

print(df.isnull().sum())

print("Creating SQLite Database...", flush=True)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Staging table: raw rows land here before validation
df.to_sql('raw_prices', conn, if_exists='replace', index=False)
print("Applying SQL transformations...", flush=True)

# PRIMARY KEY blocks duplicate dates; CHECK rejects non-positive or inconsistent OHLC prices
cursor.execute("DROP TABLE IF EXISTS msft_stock")
cursor.execute("""
CREATE TABLE msft_stock (
    date TEXT NOT NULL,
    symbol TEXT NOT NULL, 
    close REAL NOT NULL, 
    high REAL NOT NULL, 
    low REAL NOT NULL,
    open REAL NOT NULL, 
    volume REAL NOT NULL,
    PRIMARY KEY (date),
    CONSTRAINT check_positives CHECK (
        close > 0 AND high > 0 AND low > 0 AND open > 0 AND volume > 0
        AND high >= close AND high >= low AND high >= open AND low <= close AND low <= open)
)
""")

# WHERE pre-filters blanks and non-positive values;
# OR IGNORE skips any row that still breaks the PRIMARY KEY or CHECK constraints
cursor.execute("""
INSERT OR IGNORE INTO msft_stock (date, close, high, low, open, volume, symbol)
    SELECT Date, Close, High, Low, Open, Volume, 'MSFT' AS Symbol
    FROM raw_prices
    WHERE Date IS NOT NULL AND TRIM(Date) != ''
    AND Close > 0 AND High > 0 AND Low > 0 AND Open > 0 AND Volume > 0
""")

rejected_rows = cursor.execute("""
SELECT * FROM raw_prices
WHERE (Date IS NULL OR TRIM(Date) = '') OR close <= 0 OR high <= 0 OR low <= 0
OR open <= 0 OR volume <= 0 OR high < close OR high < low OR high < open 
OR low > close OR low > open 
""").fetchall()

print(f'Rejected Row: {rejected_rows}')

# Compare counts so silently rejected rows are visible
raw_rows = cursor.execute("SELECT COUNT(*) FROM raw_prices").fetchone()[0]
kept_rows = cursor.execute("SELECT COUNT(*) FROM msft_stock").fetchone()[0]
first_date, last_date = cursor.execute("SELECT MIN(date), MAX(date) FROM msft_stock").fetchone()
print(f"Rows loaded: {kept_rows} of {raw_rows} ({raw_rows - kept_rows} rejected)")
print(f"Date range: {first_date} to {last_date}")

cursor.execute("DROP TABLE IF EXISTS raw_prices")
conn.commit()
conn.close()

print("Database successfully created.", flush=True)