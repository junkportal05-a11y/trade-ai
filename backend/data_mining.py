import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DataMining")

class MarketDataCollector:
    def __init__(self):
        self.symbols = [
            "^NSEI",      # Nifty 50
            "^NSEBANK",   # Bank Nifty
            "RELIANCE.NS",
            "TCS.NS",
            "INFY.NS",
            "HDFCBANK.NS",
            "ICICIBANK.NS"
        ]
    
    def collect_nifty50_data(self, start_date: str, end_date: str):
        """Collect 5000+ candles for AI training"""
        all_data = {}
        
        for symbol in self.symbols:
            logger.info(f"Fetching {symbol} from {start_date} to {end_date}...")
            
            try:
                import upstox_feed
                
                # Fetch 60 days of 5-minute data from Upstox
                df = upstox_feed.get_historical_candles(symbol, "60d", "5m")
                
                if df is None or df.empty:
                    logger.warning(f"❌ {symbol}: No data found for given period.")
                    continue

                if self.validate_data_quality(df, symbol):
                    prepared_df = self.prepare_features(df)
                    all_data[symbol] = prepared_df
                    logger.info(f"✅ {symbol}: {len(prepared_df)} candles collected and prepared")
                else:
                    logger.warning(f"❌ {symbol}: Failed data quality validation")

            except Exception as e:
                logger.error(f"Error fetching {symbol}: {e}")

        return all_data
    
    def prepare_features(self, df):
        """Prepare features for AI training"""
        df = df.copy()
        
        # Flatten multi-level columns if returned by provider
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Price features
        df['returns'] = df['Close'].pct_change()
        df['log_returns'] = np.log(df['Close']/df['Close'].shift(1))
        
        # Volume features
        df['volume_ma'] = df['Volume'].rolling(20).mean()
        df['volume_ratio'] = df['Volume'] / df['volume_ma']
        
        # Volatility
        df['volatility'] = df['returns'].rolling(20).std()
        
        # OHLCV ratios
        df['hl_ratio'] = (df['High'] - df['Low']) / df['Close']
        df['co_ratio'] = (df['Close'] - df['Open']) / df['Open']
        
        # Moving averages
        for period in [5, 10, 20, 50, 200]:
            df[f'sma_{period}'] = df['Close'].rolling(period).mean()
            df[f'ema_{period}'] = df['Close'].ewm(span=period).mean()
        
        # RSI
        df['rsi'] = self.calculate_rsi(df['Close'])
        
        # MACD
        df['macd'], df['signal'] = self.calculate_macd(df['Close'])
        
        # Bollinger Bands
        df['bb_upper'], df['bb_lower'] = self.calculate_bollinger(df['Close'])
        
        df.dropna(inplace=True)
        return df
    
    def calculate_rsi(self, prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    def calculate_macd(self, prices):
        ema12 = prices.ewm(span=12).mean()
        ema26 = prices.ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        return macd, signal
    
    def calculate_bollinger(self, prices, period=20):
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        return sma + (2 * std), sma - (2 * std)

    def validate_data_quality(self, df: pd.DataFrame, symbol: str) -> bool:
        """Ensure data meets minimum quality standards"""
        
        # Check for sufficient data points
        if len(df) < 1000:
            logger.warning(f"{symbol}: Insufficient data ({len(df)} rows)")
            return False
        
        # Check for excessive gaps
        # In Indian market, overnight gaps are normal! Check max intraday gap instead.
        df_copy = df.copy()
        df_copy['date'] = df_copy.index.date
        max_intraday_gap = df_copy.groupby('date').apply(lambda x: x.index.to_series().diff().max()).max()
        
        if pd.notna(max_intraday_gap) and max_intraday_gap > pd.Timedelta(hours=2):
            logger.warning(f"{symbol}: Intraday data gap detected ({max_intraday_gap})")
            return False
        
        # Check for data anomalies
        if (df['Close'] <= 0).any():
            logger.error(f"{symbol}: Invalid prices detected")
            return False
        
        return True

    def save_to_parquet(self, df: pd.DataFrame, symbol: str, year: int):
        """Save prepared data with metadata"""
        output_dir = Path("historical_data/NIFTY50")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Replace ^ in symbols like ^NSEI to avoid filesystem issues
        safe_symbol = symbol.replace("^", "")
        filepath = output_dir / f"{safe_symbol}_5m_{year}.parquet"
        
        # Ensure column names are strings to support parquet
        df.columns = df.columns.astype(str)
        
        df.to_parquet(
            filepath,
            engine='pyarrow',
            compression='snappy',
            index=True  # Preserve datetime index
        )
        
        # Update metadata
        self._update_metadata(safe_symbol, year, len(df))
        
    def _update_metadata(self, symbol: str, year: int, rows: int):
        """Track downloaded data for incremental updates"""
        metadata_file = Path("historical_data/metadata.json")
        
        metadata = {}
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
                
        if symbol not in metadata:
            metadata[symbol] = {}
            
        metadata[symbol][str(year)] = {
            "rows": rows,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=4)

if __name__ == "__main__":
    collector = MarketDataCollector()
    
    # Collect data (yfinance max limit for 5m is last 60 days, so using recent dates for testing)
    end_date_dt = datetime.now()
    start_date_dt = end_date_dt - timedelta(days=59)
    start_date_str = start_date_dt.strftime("%Y-%m-%d")
    end_date_str = end_date_dt.strftime("%Y-%m-%d")
    
    # For actual 1 year collection, yfinance API restrictions require chunking or using paid API
    all_data = collector.collect_nifty50_data(
        start_date=start_date_str,
        end_date=end_date_str
    )
    
    # Save to parquet
    year = end_date_dt.year
    for symbol, df in all_data.items():
        collector.save_to_parquet(df, symbol, year=year)
    
    print(f"SUCCESS: Saved {len(all_data)} symbols to parquet files")
