import logging

logger = logging.getLogger("CapacitySimulator")

class CapacitySimulator:
    """
    Estimates the maximum capital capacity of a strategy before market impact 
    (slippage) destroys the edge.
    """
    
    def __init__(self, max_volume_participation_pct=0.01):
        """
        max_volume_participation_pct: The maximum percentage of the candle's volume 
                                      we can take without moving the price.
                                      Typically 1-2% for retail/small prop.
        """
        self.max_participation = max_volume_participation_pct
        
    def estimate_capacity(self, average_trade_volume: float, average_price: float, net_pf: float) -> dict:
        """
        Estimates how much capital can be deployed per trade before the edge vanishes.
        """
        # Maximum shares we can buy without market impact
        max_shares = average_trade_volume * self.max_participation
        
        # Maximum capital deployed per trade
        max_capital_per_trade = max_shares * average_price
        
        # If we assume 5 open trades at a time, total account capacity:
        total_account_capacity = max_capital_per_trade * 5
        
        # If Net PF is very high, we can handle more slippage, 
        # so capacity technically scales with edge size.
        edge_multiplier = max(0.5, (net_pf - 1.0))
        adjusted_capacity = total_account_capacity * edge_multiplier
        
        logger.info(f"Capacity Estimate: Max trade size ₹{max_capital_per_trade:,.2f}. Total Account: ₹{adjusted_capacity:,.2f}")
        
        return {
            "max_capital_per_trade_inr": max_capital_per_trade,
            "max_account_capacity_inr": adjusted_capacity,
            "volume_participation_limit": self.max_participation
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sim = CapacitySimulator()
    
    # Estimate capacity for a highly liquid strategy (Avg volume = 1M, Price = 500)
    sim.estimate_capacity(average_trade_volume=1000000, average_price=500.0, net_pf=1.5)
