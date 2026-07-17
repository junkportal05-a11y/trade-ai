import pandas as pd
import logging

logger = logging.getLogger("CorrelationMatrix")

class CorrelationEngine:
    """
    Prevents "fake diversification" by ensuring the portfolio does not hold 
    multiple highly correlated assets simultaneously in the same direction.
    """
    
    def __init__(self, data_dir="historical_data/quant/regime", max_correlation=0.75):
        self.data_dir = data_dir
        self.max_correlation = max_correlation
        self.correlation_matrix = None
        self.matrix_build_failed = False
        self.last_built_date = None
        
    def build_matrix(self, lookback_days=90):
        """
        Builds a Pearson correlation matrix from daily returns.
        For a real system, this should be rebuilt periodically (e.g. weekly).
        """
        # In a real scenario, we load all daily data for the universe.
        logger.info(f"Building Correlation Matrix (Lookback: {lookback_days} days)...")
        
        parquet_dir = os.path.join("historical_data", "quant", "intraday_1h")
        parquet_files = glob.glob(os.path.join(parquet_dir, "*.parquet"))
        
        if not parquet_files:
            logger.warning("No parquet files found for correlation matrix. Defaulting to fail-open.")
            self.matrix_build_failed = True
            return
            
        dfs = []
        for file in parquet_files:
            try:
                symbol = os.path.basename(file).split('_')[0]
                df = pd.read_parquet(file)
                if not df.empty and 'Close' in df.columns:
                    # we need to ensure index is datetime
                    close_series = df['Close'].rename(symbol)
                    dfs.append(close_series)
            except Exception as e:
                logger.error(f"Failed to read {file}: {e}")
                
        if not dfs:
            logger.warning("No valid data found in parquet files. Defaulting to fail-open.")
            self.matrix_build_failed = True
            return
            
        merged_df = pd.concat(dfs, axis=1)
        # Sort by index (time) and forward fill
        merged_df = merged_df.sort_index().ffill().tail(lookback_days * 24) # approx 1h bars
        
        returns_df = merged_df.pct_change().dropna(how='all')
        self.correlation_matrix = returns_df.corr()
        self.matrix_build_failed = False
        self.last_built_date = datetime.now()
        logger.info(f"Correlation Matrix built at {self.last_built_date.isoformat()}. Shape: {self.correlation_matrix.shape}")
        
    def check_trade_allowed(self, candidate_symbol: str, current_portfolio: list) -> bool:
        """
        Returns False if the candidate symbol is highly correlated (>max_correlation)
        with any existing position in the portfolio.
        """
        if self.correlation_matrix is None and not self.matrix_build_failed:
            self.build_matrix()
            
        if self.matrix_build_failed or self.correlation_matrix is None:
            # Fail-open: if no data, allow the trade
            return True
        
        # Warn if matrix is stale (> 14 days old)
        if self.last_built_date:
            age_days = (datetime.now() - self.last_built_date).days
            if age_days > 14:
                logger.warning(
                    f"Correlation matrix is {age_days} days old (built {self.last_built_date.date()}). "
                    f"Consider rebuilding — sector correlations may have shifted."
                )
            
        if candidate_symbol not in self.correlation_matrix.index:
            # If we don't have correlation data for this symbol, allow it
            return True
            
        for held_symbol in current_portfolio:
            if held_symbol in self.correlation_matrix.columns:
                corr = self.correlation_matrix.loc[candidate_symbol, held_symbol]
                if corr >= self.max_correlation:
                    logger.debug(f"Blocked {candidate_symbol}: Highly correlated ({corr:.2f}) with held position {held_symbol}")
                    return False
                    
        return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    engine = CorrelationEngine()
    
    portfolio = ["HDFCBANK.NS"]
    logger.info(f"Current Portfolio: {portfolio}")
    
    # Trying to buy ICICI Bank
    allowed = engine.check_trade_allowed("ICICIBANK.NS", portfolio)
    logger.info(f"Can buy ICICIBANK? {allowed}")
    
    # Trying to buy Reliance
    allowed = engine.check_trade_allowed("RELIANCE.NS", portfolio)
    logger.info(f"Can buy RELIANCE? {allowed}")
