import pandas as pd
import logging

logger = logging.getLogger("FilterROI")

class FilterROIEngine:
    """
    Evaluates whether a specific trading filter actually creates edge or just 
    removes profitable trades alongside losers.
    """
    
    def __init__(self):
        self.ghost_trades = []
        
    def log_blocked_trade(self, filter_name: str, symbol: str, simulated_net_pnl: float, would_have_won: bool):
        """
        Logs a trade that was blocked by a specific filter.
        The trade must be fully simulated (ghost-traded) to know its PnL.
        """
        self.ghost_trades.append({
            "filter": filter_name,
            "symbol": symbol,
            "net_pnl": simulated_net_pnl,
            "would_have_won": 1 if would_have_won else 0,
            "would_have_lost": 0 if would_have_won else 1
        })
        
    def generate_report(self):
        """
        Outputs the Net ROI of each filter.
        A positive ROI means the filter successfully blocked more losses than wins (Good).
        A negative ROI means the filter blocked more wins than losses (Bad).
        """
        if not self.ghost_trades:
            logger.warning("No blocked trades to evaluate.")
            return None
            
        df = pd.DataFrame(self.ghost_trades)
        
        report = []
        for filter_name, group in df.groupby("filter"):
            total_blocked = len(group)
            won = group["would_have_won"].sum()
            lost = group["would_have_lost"].sum()
            
            # The edge contribution of the filter is the negative of the net PnL it blocked.
            # E.g., if it blocked trades that would have lost ₹500, its ROI is +₹500.
            # If it blocked trades that would have won ₹500, its ROI is -₹500.
            net_pnl_blocked = group["net_pnl"].sum()
            filter_roi = -net_pnl_blocked
            
            report.append({
                "Filter": filter_name,
                "Blocked_Trades": total_blocked,
                "Would_Have_Won": won,
                "Would_Have_Lost": lost,
                "Filter_ROI_INR": round(filter_roi, 2)
            })
            
        report_df = pd.DataFrame(report).sort_values(by="Filter_ROI_INR", ascending=False)
        logger.info("\n--- Filter ROI Attribution Report ---")
        for _, r in report_df.iterrows():
            logger.info(
                f"Filter: {r['Filter']:<20} | Blocked: {r['Blocked_Trades']:<4} | "
                f"Wins Blocked: {r['Would_Have_Won']:<3} | Losses Blocked: {r['Would_Have_Lost']:<3} | "
                f"ROI: ₹{r['Filter_ROI_INR']}"
            )
            
        return report_df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = FilterROIEngine()
    
    # Simulate a smart filter (ADX > 25) that blocks choppy losses
    for i in range(50):
        # 10 wins blocked (+100 each), 40 losses blocked (-50 each)
        pnl = 100 if i < 10 else -50
        engine.log_blocked_trade("ADX > 25", "NIFTY", pnl, pnl > 0)
        
    # Simulate a dumb filter (RSI < 70) that blocks massive trend continuation wins
    for i in range(50):
        # 30 wins blocked (+100 each), 20 losses blocked (-50 each)
        pnl = 100 if i < 30 else -50
        engine.log_blocked_trade("RSI Overbought", "BANKNIFTY", pnl, pnl > 0)
        
    engine.generate_report()
