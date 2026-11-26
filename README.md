# MSFT Value at Risk & Stress Testing

A Python and SQLite pipeline that estimates the one-day market risk of a position in Microsoft (MSFT) stock. Value at Risk (VaR) is calculated with a parametric (normal) model and with historical simulation, and the two are compared to show where the normal assumption breaks down.

*Status: in progress. The data pipeline and VaR estimates are complete; backtesting and stress testing are under way.*

## Results

1-day VaR on a hypothetical $100,000 MSFT position:

| Confidence | Parametric (normal) | Historical |
|---|---|---|
| 95% | 2.76% ($2,762.61) | 2.66% ($2,658.72) |
| 99% | 3.95% ($3,948.43) | 4.25% ($4,249.00) |

At 95% confidence the two methods are closely aligned. At 99%, the parametric estimate is about 7% lower than the historical estimate, meaning the normal model understates the size of extreme daily losses.

This is consistent with the distribution of returns. MSFT's daily returns have an excess kurtosis of 8.90, compared with 0 for a normal distribution, so large moves occur far more often than a normal model assumes. Skewness is mildly positive (0.33), meaning the largest up days have been somewhat larger than the largest down days over this period. The underestimation of losses at 99% is therefore driven by the heavy tails rather than by a negative skew.

| Statistic | Value |
|---|---|
| Mean daily return | 0.099% |
| Daily volatility | 1.74% |
| Annualized volatility | 27.62% |
| Excess kurtosis | 8.90 |
| Skewness | 0.33 |

Interpretation: on roughly 95% of trading days, the loss on a $100,000 position is not expected to exceed about $2,700. On approximately 1 day in 20, the loss will be larger.

## Pipeline

```
download_data.py  →  msft_daily.csv  →  ingest.py  →  risk.db  →  analyze_risk.py
```

`download_data.py` retrieves daily MSFT prices from Yahoo Finance and saves a fixed snapshot, so results remain reproducible.

`ingest.py` cleans the data and loads it into SQLite through a staging table. The target table enforces a primary key on date, NOT NULL on every column, and CHECK constraints that reject non-positive prices and internally inconsistent rows (for example, a high below the close). The script reports the number of rejected rows and lists them for review.

`analyze_risk.py` reads the validated prices and computes returns, volatility, VaR and distribution statistics.

## Data

| | |
|---|---|
| Source | Yahoo Finance (yfinance) |
| Period | January 2, 2015 – November 24, 2026 |
| Observations | 2,992 trading days |
| Adjustment | Split- and dividend-adjusted |
| Retrieved | November 24, 2026 |

### Validation note

The initial load rejected one row (May 30, 2017). On review, the row was valid: MSFT closed at its daily high, but dividend adjustment produced a floating-point difference of 1e-14, leaving the adjusted close marginally above the adjusted high and failing the `high >= close` constraint.

Excluding a valid trading day would have combined two days of returns into one, so a tolerance of 0.000001 was added to the price-consistency checks. Invalid prices are still rejected, and all 2,992 rows now load.

## Methodology

Daily simple returns are calculated from adjusted closing prices. Volatility is the sample standard deviation of returns, annualized using √252 trading days.

Parametric VaR assumes normally distributed returns:

```
VaR = −(μ + z · σ)
```

where μ is the mean daily return, σ is daily volatility, and z is the left-tail normal quantile (−1.645 at 95%, −2.326 at 99%).

Historical VaR is the negative of the 5th or 1st percentile of observed daily returns and makes no distributional assumption.

Returns are negative for losses; VaR is reported as a positive loss.

## Next Steps

- Rolling 250-day backtest of both methods, with the Kupiec proportion-of-failures test
- Stress testing: worst single days, maximum drawdown, and selected periods (August 2015, Q4 2018, March 2020, 2022)
- Charts: return distribution with VaR thresholds, rolling volatility, backtest exceptions
- Expected Shortfall and EWMA volatility

## Limitations

- Results apply to a single stock, not a diversified portfolio.
- Parametric VaR assumes normal returns, which the kurtosis result shows does not hold in the tails.
- Historical VaR assumes the past ~12 years are representative of future risk.
- Both methods assume constant volatility, although volatility clusters in practice.
- The sample begins in 2015 and does not include the 2008 financial crisis.

## Usage

```bash
pip install -r requirements.txt
python download_data.py   # only required to refresh the data
python ingest.py
python analyze_risk.py
```

**Tools:** Python (pandas, NumPy, SciPy, Matplotlib), SQLite, yfinance
