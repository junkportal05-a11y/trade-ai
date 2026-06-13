import yfinance as yf
import pandas as pd
import os
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("QuantDataFetcher")

class HistoricalDataFetcher:
    def __init__(self, data_dir="historical_data/quant"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "regime"), exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, "intraday_1h"), exist_ok=True)

        # NIFTY 50 Universe (Representative sample for testing)
        self.universe = [
            "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS",
            "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "L&T.NS", "BAJFINANCE.NS",
            "AXISBANK.NS", "KOTAKBANK.NS", "ASIANPAINT.NS", "HINDUNILVR.NS",
            "MARUTI.NS", "SUNPHARMA.NS", "TATASTEEL.NS", "M&M.NS", "TATAMOTORS.NS"
        ]
        
    def fetch_regime_data(self):
        """Fetch 10 years of daily data for NIFTY 50 index (^NSEI) for regime mapping."""
        logger.info("Fetching 10 years of 1d data for ^NSEI (Regime Mapping)...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * 10)
        
        try:
            nifty = yf.Ticker("^NSEI")
            df = nifty.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval="1d")
            
            if df.empty:
                logger.error("Failed to fetch ^NSEI data.")
                return
                
            file_path = os.path.join(self.data_dir, "regime", "NIFTY50_1d_10Y.parquet")
            df.to_parquet(file_path)
            logger.info(f"Saved ^NSEI regime data: {len(df)} days.")
        except Exception as e:
            logger.error(f"Error fetching regime data: {e}")

    def fetch_intraday_walkforward_data(self):
        """Fetch 730 days of 1h data for F&O universe."""
        logger.info("Fetching 730 days of 1h data for Intraday Walk-Forward...")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=729) # yf limit is 730 days
        
        for symbol in self.universe:
            logger.info(f"Fetching 1h data for {symbol}...")
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(start=start_date.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), interval="1h")
                
                if df.empty:
                    logger.warning(f"No 1h data found for {symbol}.")
                    continue
                    
                file_path = os.path.join(self.data_dir, "intraday_1h", f"{symbol}_1h_2Y.parquet")
                df.to_parquet(file_path)
                logger.info(f"Saved {symbol}: {len(df)} 1h candles.")
            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")

if __name__ == "__main__":
    fetcher = HistoricalDataFetcher()
    fetcher.fetch_regime_data()
    fetcher.fetch_intraday_walkforward_data()
    logger.info("Data acquisition complete.")
