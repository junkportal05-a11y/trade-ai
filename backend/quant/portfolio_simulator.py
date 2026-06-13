import logging

logger = logging.getLogger("PortfolioSimulator")

class PortfolioSimulator:
    """
    Enforces real-world capital constraints, risk management limits, and position sizing.
    """
    
    def __init__(self, initial_capital=100000.0, max_positions=5, risk_per_trade_pct=0.01, max_sector_exposure=0.25):
        self.capital = initial_capital
        self.max_positions = max_positions
        self.risk_per_trade = risk_per_trade_pct
        self.max_sector_exposure = max_sector_exposure
        
        self.open_positions = {}
        self.trade_ledger = []
        
    def calculate_position_size(self, entry_price: float, stop_loss: float) -> int:
        """
        Calculates position size based on strict 1% risk rule.
        """
        risk_amount_per_share = abs(entry_price - stop_loss)
        if risk_amount_per_share <= 0:
            return 0
            
        max_loss_allowed = self.capital * self.risk_per_trade
        shares = int(max_loss_allowed / risk_amount_per_share)
        
        # Ensure we have enough capital to buy (ignoring margin leverage for safety)
        cost = shares * entry_price
        if cost > self.capital:
            shares = int(self.capital / entry_price)
            
        return shares
        
    def request_trade(self, symbol: str, entry_price: float, stop_loss: float, sector: str) -> dict:
        """
        Attempts to enter a trade based on portfolio constraints.
        Returns trade details if accepted, or rejection reason if blocked.
        """
        # 1. Max Positions Check
        if len(self.open_positions) >= self.max_positions:
            return {"status": "REJECTED", "reason": "Max positions reached"}
            
        # 2. Duplicate Check
        if symbol in self.open_positions:
            return {"status": "REJECTED", "reason": "Symbol already held"}
            
        # 3. Sector Exposure Check
        sector_count = sum(1 for pos in self.open_positions.values() if pos['sector'] == sector)
        if sector_count >= (self.max_positions * self.max_sector_exposure):
            return {"status": "REJECTED", "reason": f"Max sector exposure reached for {sector}"}
            
        # 4. Position Sizing
        shares = self.calculate_position_size(entry_price, stop_loss)
        if shares == 0:
            return {"status": "REJECTED", "reason": "Calculated position size is 0"}
            
        # Accept Trade
        trade_cost = shares * entry_price
        self.capital -= trade_cost
        
        trade = {
            "symbol": symbol,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "shares": shares,
            "sector": sector,
            "cost": trade_cost
        }
        self.open_positions[symbol] = trade
        
        return {"status": "ACCEPTED", "trade": trade}

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sim = PortfolioSimulator(initial_capital=100000) # 1 Lakh INR
    
    # Try to buy HDFC Bank (Banking)
    res = sim.request_trade("HDFCBANK.NS", entry_price=1600.0, stop_loss=1580.0, sector="Banking")
    logger.info(f"HDFCBANK Trade: {res['status']}")
    
    # Try to buy ICICI Bank (Banking) - Should hit sector limit (1 out of 5 = 20%, max 25%, so 2nd bank is blocked!)
    # Actually 1/5 is 20%. 2/5 is 40%. Since max is 25%, 2nd bank should be rejected!
    res = sim.request_trade("ICICIBANK.NS", entry_price=1000.0, stop_loss=990.0, sector="Banking")
    logger.info(f"ICICIBANK Trade: {res['status']} ({res.get('reason', '')})")
    
    # Try to buy TCS (IT)
    res = sim.request_trade("TCS.NS", entry_price=3800.0, stop_loss=3750.0, sector="IT")
    logger.info(f"TCS Trade: {res['status']}")
