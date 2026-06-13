import pandas as pd
import os
import glob
import logging

logger = logging.getLogger("MarketReplayEngine")

class MarketReplayEngine:
    """
    Zero-Lookahead Backtester. 
    Loads multiple symbol dataframes, interleaves them chronologically, 
    and yields ticks exactly as they occurred in reality.
    """
    
    def __init__(self, data_dir="historical_data/quant/intraday_1h"):
        self.data_dir = data_dir
        self.master_df = None
        
    def load_and_sort_data(self):
        """
        Loads all parquet files in the data directory, adds a 'Symbol' column,
        and sorts the entire master dataframe chronologically.
        """
        files = glob.glob(os.path.join(self.data_dir, "*.parquet"))
        if not files:
            logger.error("No data files found to replay.")
            return False
            
        dfs = []
        for file in files:
            symbol = os.path.basename(file).split("_")[0]
            df = pd.read_parquet(file)
            # Ensure Datetime index is a column for sorting
            df = df.reset_index()
            # If the index is already named Datetime, reset_index preserves it
            # Yfinance returns 'Datetime'
            if 'Datetime' not in df.columns and 'Date' in df.columns:
                df = df.rename(columns={'Date': 'Datetime'})
                
            df['Symbol'] = symbol
            dfs.append(df)
            
        logger.info(f"Loaded {len(dfs)} instruments. Merging and sorting chronologically...")
        self.master_df = pd.concat(dfs, ignore_index=True)
        
        # Sort strictly by time to prevent lookahead
        self.master_df = self.master_df.sort_values(by='Datetime').reset_index(drop=True)
        logger.info(f"Master DataFrame ready: {len(self.master_df)} rows spanning {self.master_df['Datetime'].min()} to {self.master_df['Datetime'].max()}")
        return True
        
    def replay(self, strategy_callback):
        """
        Yields rows strictly chronologically to the provided callback function.
        strategy_callback(row) -> executes strategy logic on the current tick/candle
        """
        if self.master_df is None:
            if not self.load_and_sort_data():
                return
                
        logger.info("Starting Zero-Lookahead Market Replay...")
        
        # Simulated memory of past bars (for calculating indicators without future peeking)
        # In a real heavy backtester, we maintain a rolling window of length N per symbol
        symbol_history = {}
        
        for idx, row in self.master_df.iterrows():
            sym = row['Symbol']
            if sym not in symbol_history:
                # Store up to 100 historical candles per symbol for indicator calculation
                symbol_history[sym] = []
                
            symbol_history[sym].append(row)
            if len(symbol_history[sym]) > 100:
                symbol_history[sym].pop(0)
                
            # Send current row AND strict historical context to the strategy
            # NO FUTURE DATA EXISTS IN THIS CONTEXT.
            strategy_callback(row, symbol_history[sym])
            
        logger.info("Market Replay complete. 0% Lookahead Bias achieved.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    # Dummy strategy
    def dummy_strategy(current_candle, past_candles):
        # A simple strategy that buys if current close > previous close
        if len(past_candles) < 2:
            return
        prev_candle = past_candles[-2]
        if current_candle['Close'] > prev_candle['Close']:
            pass # Emit buy signal (handled by portfolio simulator)
            
    engine = MarketReplayEngine()
    engine.replay(dummy_strategy)
