"""
10-Year Free Historical Market Data Downloader & Local Storage for ApexTrade AI
Downloads 10 years of daily OHLCV data for top Indian liquid tickers (NIFTY 50 leaders)
and saves CSV files to backend/historical_data/
"""
import os
import sys
import logging
import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("download_10y_data")

TOP_NSE_TICKERS = [
    "RELIANCE.NS",
    "TCS.NS",
    "INFY.NS",
    "HDFCBANK.NS",
    "ICICIBANK.NS",
    "SBIN.NS",
    "BHARTIARTL.NS",
    "ITC.NS",
    "KOTAKBANK.NS",
    "LT.NS",
    "AXISBANK.NS",
    "HINDUNILVR.NS",
    "TATAMOTORS.NS",
    "TATASTEEL.NS",
    "MARUTI.NS",
    "SUNPHARMA.NS",
    "TITAN.NS",
    "BAJFINANCE.NS",
    "WIPRO.NS",
    "ULTRACEMCO.NS",
    "NTPC.NS",
    "POWERGRID.NS",
    "ONGC.NS",
    "COALINDIA.NS",
    "ADANIENT.NS",
    "^NSEI",
    "^NSEBANK",
]

def main():
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    target_dir = os.path.join(backend_dir, "historical_data")
    os.makedirs(target_dir, exist_ok=True)

    logger.info(f"Starting 10-Year Historical Data Batch Download for {len(TOP_NSE_TICKERS)} tickers...")
    summary = []

    for idx, symbol in enumerate(TOP_NSE_TICKERS, start=1):
        logger.info(f"[{idx}/{len(TOP_NSE_TICKERS)}] Fetching 10y daily data for {symbol}...")
        try:
            df = yf.download(symbol, period="10y", interval="1d", auto_adjust=True, progress=False)
            if df is None or df.empty:
                logger.warning(f"No data returned for {symbol}")
                continue

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df = df.dropna(subset=["Close", "High", "Low", "Open"])
            df = df.rename(columns={
                "open": "Open",
                "high": "High",
                "low": "Low",
                "close": "Close",
                "volume": "Volume",
                "adj close": "Adj Close"
            })

            clean_symbol = symbol.replace("^", "INDEX_").replace(".NS", "")
            out_filename = f"{clean_symbol}_10y_daily.csv"
            out_path = os.path.join(target_dir, out_filename)

            df.to_csv(out_path)
            file_size_kb = round(os.path.getsize(out_path) / 1024, 1)
            row_count = len(df)
            start_date = df.index[0].strftime("%Y-%m-%d")
            end_date = df.index[-1].strftime("%Y-%m-%d")

            logger.info(f"Successfully saved {symbol} -> {out_filename} ({row_count} bars, {start_date} to {end_date}, {file_size_kb} KB)")
            summary.append({
                "symbol": symbol,
                "filename": out_filename,
                "bars": row_count,
                "start": start_date,
                "end": end_date,
                "size_kb": file_size_kb,
            })
        except Exception as e:
            logger.error(f"Failed downloading {symbol}: {e}")

    logger.info("=" * 60)
    logger.info(f"DOWNLOAD COMPLETE: {len(summary)} / {len(TOP_NSE_TICKERS)} datasets downloaded and saved!")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()
