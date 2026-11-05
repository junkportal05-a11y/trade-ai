"""
Download 7-Year Historical Market Data for Indian Stock Market (NSE).
Uses yfinance (free, standard Yahoo Finance market data).
Saves CSV & Parquet files in historical_data/daily_7y/
"""
import os
import time
import pandas as pd
import yfinance as yf

# Target directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "historical_data", "daily_7y")
os.makedirs(OUTPUT_DIR, exist_ok=True)

SYMBOLS = {
    # Benchmark Indices
    "^NSEI": "NIFTY_50_INDEX",
    "^NSEBANK": "BANK_NIFTY_INDEX",
    # Major Large-Caps across Sectors
    "RELIANCE.NS": "RELIANCE",
    "TCS.NS": "TCS",
    "HDFCBANK.NS": "HDFCBANK",
    "ICICIBANK.NS": "ICICIBANK",
    "INFY.NS": "INFY",
    "SBIN.NS": "SBIN",
    "BHARTIARTL.NS": "BHARTIARTL",
    "ITC.NS": "ITC",
    "KOTAKBANK.NS": "KOTAKBANK",
    "LT.NS": "LT",
    "AXISBANK.NS": "AXISBANK",
    "HINDUNILVR.NS": "HINDUNILVR",
    "BAJFINANCE.NS": "BAJFINANCE",
    "MARUTI.NS": "MARUTI",
    "TATAMOTORS.NS": "TATAMOTORS",
    "TATASTEEL.NS": "TATASTEEL",
    "SUNPHARMA.NS": "SUNPHARMA",
    "TITAN.NS": "TITAN",
    "NTPC.NS": "NTPC",
    "POWERGRID.NS": "POWERGRID",
}

def download_data():
    print(f"==================================================")
    print(f"Downloading 7-Year Historical Data for Indian Equities")
    print(f"Destination: {OUTPUT_DIR}")
    print(f"Total Instruments: {len(SYMBOLS)}")
    print(f"==================================================\n")

    summary = []

    for ticker_symbol, clean_name in SYMBOLS.items():
        print(f"Fetching {ticker_symbol} ({clean_name})...", end=" ", flush=True)
        try:
            ticker = yf.Ticker(ticker_symbol)
            # Fetch 7 years of daily data
            df = ticker.history(period="7y", interval="1d")
            
            if df.empty:
                print("FAILED (No data returned)")
                continue

            # Standardize index & columns
            df.index.name = "Date"
            df.reset_index(inplace=True)
            # Normalize timezone
            if hasattr(df['Date'].dt, 'tz') and df['Date'].dt.tz is not None:
                df['Date'] = df['Date'].dt.tz_localize(None)

            # File paths
            csv_path = os.path.join(OUTPUT_DIR, f"{clean_name}_7y_daily.csv")
            parquet_path = os.path.join(OUTPUT_DIR, f"{clean_name}_7y_daily.parquet")

            df.to_csv(csv_path, index=False)
            df.to_parquet(parquet_path, index=False)

            start_dt = df['Date'].iloc[0].strftime('%Y-%m-%d')
            end_dt = df['Date'].iloc[-1].strftime('%Y-%m-%d')
            row_count = len(df)
            size_kb = os.path.getsize(csv_path) / 1024

            print(f"DONE | {row_count} rows | {start_dt} to {end_dt} | {size_kb:.1f} KB")

            summary.append({
                "Symbol": ticker_symbol,
                "Name": clean_name,
                "Rows": row_count,
                "Start_Date": start_dt,
                "End_Date": end_dt,
                "CSV_Path": csv_path,
                "Parquet_Path": parquet_path
            })
            time.sleep(0.3)  # Gentle rate limiting
        except Exception as e:
            print(f"ERROR: {e}")

    summary_df = pd.DataFrame(summary)
    summary_csv = os.path.join(OUTPUT_DIR, "_manifest_summary.csv")
    summary_df.to_csv(summary_csv, index=False)
    print("\n==================================================")
    print(f"Successfully downloaded {len(summary)} / {len(SYMBOLS)} instruments.")
    print(f"Manifest written to: {summary_csv}")
    print("==================================================")

if __name__ == "__main__":
    download_data()

