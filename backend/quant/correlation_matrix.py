import pandas as pd
import numpy as np
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
        
    def build_matrix(self, lookback_days=90):
        """
        Builds a Pearson correlation matrix from daily returns.
        For a real system, this should be rebuilt periodically (e.g. weekly).
        """
        # In a real scenario, we load all daily data for the universe.
        # For this prototype, we'll generate a dummy matrix that forces 
        # banks to be highly correlated to test the logic.
        
        logger.info(f"Building Correlation Matrix (Lookback: {lookback_days} days)...")
        
        # Mock Correlation Matrix
        universe = ["HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS", "SBIN.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS"]
        
        # Create identity matrix
        corr = pd.DataFrame(np.eye(len(universe)), index=universe, columns=universe)
        
        # Manually inject high correlations for banks
        banks = ["HDFCBANK.NS", "ICICIBANK.NS", "AXISBANK.NS", "KOTAKBANK.NS", "SBIN.NS"]
        for b1 in banks:
            for b2 in banks:
                if b1 != b2:
                    corr.loc[b1, b2] = 0.85
                    
        # IT highly correlated
        it = ["TCS.NS", "INFY.NS"]
        corr.loc[it[0], it[1]] = 0.90
        corr.loc[it[1], it[0]] = 0.90
        
        self.correlation_matrix = corr
        logger.info("Correlation Matrix built.")
        
    def check_trade_allowed(self, candidate_symbol: str, current_portfolio: list) -> bool:
        """
        Returns False if the candidate symbol is highly correlated (>max_correlation)
        with any existing position in the portfolio.
        """
        if self.correlation_matrix is None:
            self.build_matrix()
            
        if candidate_symbol not in self.correlation_matrix.index:
            # If we don't have correlation data, allow it (or block it if strict)
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
