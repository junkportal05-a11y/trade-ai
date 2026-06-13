import random
import logging

logger = logging.getLogger("ExecutionEngine")

class BrokerExecutionSimulator:
    """
    Simulates the reality of interacting with a broker API in live markets.
    Injects network delays, slippage due to latency, partial fills, and timeouts.
    """
    
    def __init__(self, 
                 base_latency_ms: int = 150, 
                 volatility_multiplier: float = 1.0,
                 rejection_rate: float = 0.005,
                 partial_fill_rate: float = 0.02):
        self.base_latency_ms = base_latency_ms
        self.volatility_multiplier = volatility_multiplier
        self.rejection_rate = rejection_rate
        self.partial_fill_rate = partial_fill_rate
        
    def simulate_order(self, 
                       signal_price: float, 
                       order_qty: int, 
                       market_volatility: float,
                       bid_ask_spread: float) -> dict:
        """
        Takes an intended order and simulates its execution.
        Returns the actual filled quantity, executed price, and status.
        """
        # 1. API/Exchange Latency
        latency = int(random.gauss(self.base_latency_ms, 50)) * self.volatility_multiplier
        latency = max(20, latency) # Minimum 20ms physics limit
        
        # 2. Rejections (e.g. margin error, broker API down, freak trade limits)
        if random.random() < self.rejection_rate:
            return {
                "status": "REJECTED",
                "filled_qty": 0,
                "executed_price": 0.0,
                "latency_ms": latency,
                "reason": "Broker API Timeout or Margin Error"
            }
            
        # 3. Partial Fills (Happens in illiquid stocks)
        filled_qty = order_qty
        if random.random() < self.partial_fill_rate:
            # Filled between 10% and 90% of the requested quantity
            fill_pct = random.uniform(0.1, 0.9)
            filled_qty = int(order_qty * fill_pct)
            
        # 4. Latency Slippage (Price moved while packet was traveling)
        # If volatility is high, price moves further during the delay.
        # We assume 1 tick = 0.05 INR
        ticks_moved = int((latency / 100.0) * market_volatility)
        
        # Price shifts against the trader by 0 to `ticks_moved` ticks + half the spread
        slippage = (random.randint(0, max(1, ticks_moved)) * 0.05) + (bid_ask_spread / 2)
        executed_price = signal_price + slippage
        
        return {
            "status": "PARTIAL" if filled_qty < order_qty else "FILLED",
            "filled_qty": filled_qty,
            "executed_price": round(executed_price, 2),
            "latency_ms": round(latency, 2),
            "reason": "Execution Successful"
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sim = BrokerExecutionSimulator()
    
    # Simulate 5 trades
    for i in range(5):
        res = sim.simulate_order(signal_price=1000.0, order_qty=100, market_volatility=2.5, bid_ask_spread=0.1)
        print(f"Trade {i+1}: Requested 100 @ 1000.00 -> {res['status']}: {res['filled_qty']} @ {res['executed_price']} (Latency: {res['latency_ms']}ms)")
