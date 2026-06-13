import yfinance as yf
import pandas as pd
import sys

sys.path.append('backend')
from signals import analyse_symbol
import db

def test_sim():
    # Download 5m data for 10 days
    print("Downloading data...")
    df = yf.download("RELIANCE.NS", period="30d", interval="5m")
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.droplevel(1)
        
    df.dropna(inplace=True)
    if df.empty:
        print("No data.")
        return
        
    print(f"Downloaded {len(df)} rows.")
    
    wins = 0
    losses = 0
    timeouts = 0
    total = 0
    
    # Process day by day just like simulator
    # Group by day
    df['date'] = df.index.date
    for date, df_day in df.groupby('date'):
        for i in range(50, len(df_day) - 1):
            current_time = df_day.index[i]
            # Use data up to i
            df_slice = df_day.iloc[:i+1]
            
            # analyse_symbol needs more data for MACD (usually > 50 periods)
            # So we pass the last 100 rows from the FULL dataframe up to current_time
            full_slice_idx = df.index.get_loc(current_time)
            if full_slice_idx < 100:
                continue
            
            full_slice = df.iloc[full_slice_idx-100:full_slice_idx+1]
            
            # Mock analyse_symbol internally fetching data? 
            # No, analyse_symbol takes ticker symbol and fetches it. We can't mock yfinance easily for thousands of calls without it being slow.
            pass

test_sim()
