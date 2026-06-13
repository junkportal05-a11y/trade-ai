import logging

logger = logging.getLogger("LiquidityFilter")

class LiquidityFilter:
    """
    Prevents signals from executing on illiquid stocks, avoiding massive slippage
    and market impact costs in real live trading.
    """
    
    def __init__(self, min_avg_daily_volume=500000, min_traded_value_inr=50000000, max_spread_bps=15):
        """
        min_avg_daily_volume: Minimum average daily volume required to trade.
        min_traded_value_inr: Minimum traded value in INR required to trade.
        max_spread_bps: Maximum allowable bid-ask spread in basis points (1 bps = 0.01%).
        """
        self.min_avg_daily_volume = min_avg_daily_volume
        self.min_traded_value_inr = min_traded_value_inr
        self.max_spread_bps = max_spread_bps
        
    def is_tradable(self, symbol: str, current_volume: float, current_price: float, bid_ask_spread_inr: float) -> bool:
        """
        Checks if a stock meets strict institutional liquidity requirements.
        """
        traded_value = current_volume * current_price
        spread_bps = (bid_ask_spread_inr / current_price) * 10000
        
        if current_volume < self.min_avg_daily_volume:
            logger.debug(f"[{symbol}] BLOCKED: Volume {current_volume} < {self.min_avg_daily_volume}")
            return False
            
        if traded_value < self.min_traded_value_inr:
            logger.debug(f"[{symbol}] BLOCKED: Traded Value {traded_value} < {self.min_traded_value_inr}")
            return False
            
        if spread_bps > self.max_spread_bps:
            logger.debug(f"[{symbol}] BLOCKED: Spread {spread_bps:.1f} bps > {self.max_spread_bps} bps")
            return False
            
        return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    lf = LiquidityFilter()
    
    # Test a highly liquid stock (e.g. HDFC Bank)
    lf.is_tradable("HDFCBANK.NS", current_volume=5000000, current_price=1600.0, bid_ask_spread_inr=0.5)
    
    # Test an illiquid stock
    lf.is_tradable("ILLIQUID.NS", current_volume=50000, current_price=100.0, bid_ask_spread_inr=1.0)
