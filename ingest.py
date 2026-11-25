import sqlite3
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / 'msft_daily.csv'
DB_PATH = BASE_DIR / 'risk.db'

# yfinance CSVs have 3 header rows (Price/Ticker/Date), so skip them and set names directlyprint("Loading Dataset...", flush=True)
col_names = ["Date", "Close", "High", "Low", "Open", "Volume"]
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
        AND high >= close - 0.000001 AND high >= low - 0.000001 
        AND high >= open - 0.000001 AND low <= close + 0.000001 
        AND low <= open + 0.000001)
)
""")

rejected_rows = cursor.execute("""
SELECT * FROM raw_prices
WHERE (Date IS NULL OR TRIM(Date) = '') OR Close <= 0 OR High <= 0 OR Low <= 0
OR Open <= 0 OR Volume <= 0 OR High < Close - 0.000001 OR High < Low - 0.000001 OR High < Open - 0.000001
OR Low > Close + 0.000001 OR Low > Open + 0.000001
""").fetchall()

# WHERE pre-filters blanks and non-positive values;
# OR IGNORE skips any row that still breaks the PRIMARY KEY or CHECK constraints
cursor.execute("""
INSERT OR IGNORE INTO msft_stock (date, close, high, low, open, volume, symbol)
    SELECT Date, Close, High, Low, Open, Volume, 'MSFT' AS Symbol
    FROM raw_prices
    WHERE Date IS NOT NULL AND TRIM(Date) != ''
    AND Close > 0 AND High > 0 AND Low > 0 AND Open > 0 AND Volume > 0
""")

print(f'Rejected Row(s): {rejected_rows}')

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