from app.core.logging import logger

class CostEngine:
    """
    Simulates real-world Indian Stock Market transaction costs for Intraday (Equity Cash).
    """

    def __init__(self, brokerage_per_order=20.0, slippage_bps=5.0):
        self.brokerage = brokerage_per_order
        self.slippage_pct = slippage_bps / 10000.0  # 5 bps = 0.05%

        # Current Indian Intraday Equity Charges (approx)
        self.stt_sell_pct = 0.00025      # 0.025% on sell side only for intraday
        self.exchange_txn_pct = 0.0000345 # 0.00345%
        self.sebi_turnover_pct = 0.000001 # 0.0001%
        self.stamp_duty_buy_pct = 0.00003 # 0.003% on buy side
        self.gst_pct = 0.18               # 18% on (brokerage + exchange txn + SEBI)

    def calculate_net_trade(self, entry_price: float, exit_price: float, qty: int, is_buy: bool) -> dict:
        """
        Calculates the net PnL after slippage and all taxes.
        Returns a dict with breakdown.
        """
        # 1. Apply Slippage (Worse fills than paper)
        if is_buy:
            actual_entry = entry_price * (1 + self.slippage_pct)
            actual_exit = exit_price * (1 - self.slippage_pct)
        else:
            actual_entry = entry_price * (1 - self.slippage_pct)
            actual_exit = exit_price * (1 + self.slippage_pct)

        buy_value = actual_entry * qty if is_buy else actual_exit * qty
        sell_value = actual_exit * qty if is_buy else actual_entry * qty
        turnover = buy_value + sell_value

        # 2. Brokerage (Max 20 or 0.03% whichever is lower, assuming flat 20 for large trades)
        # We apply flat 20 for entry, 20 for exit.
        total_brokerage = self.brokerage * 2

        # 3. Regulatory Charges
        stt = sell_value * self.stt_sell_pct
        exchange_txn_charge = turnover * self.exchange_txn_pct
        sebi_charge = turnover * self.sebi_turnover_pct
        stamp_duty = buy_value * self.stamp_duty_buy_pct

        # 4. GST
        taxable_amount = total_brokerage + exchange_txn_charge + sebi_charge
        gst = taxable_amount * self.gst_pct

        total_costs = total_brokerage + stt + exchange_txn_charge + sebi_charge + stamp_duty + gst

        gross_pnl = (actual_exit - actual_entry) * qty if is_buy else (actual_entry - actual_exit) * qty
        net_pnl = gross_pnl - total_costs

        return {
            "gross_pnl": round(gross_pnl, 2),
            "net_pnl": round(net_pnl, 2),
            "total_costs": round(total_costs, 2),
            "actual_entry": round(actual_entry, 2),
            "actual_exit": round(actual_exit, 2),
            "slippage_cost": round(abs((exit_price - entry_price) * qty - gross_pnl), 2)
        }

if __name__ == "__main__":
    engine = CostEngine()

    # Test a 100,000 INR trade that made 1% (1,000 gross)
    # Price 1000, qty 100
    res = engine.calculate_net_trade(1000.0, 1010.0, 100, is_buy=True)
    logger.info("Paper Trade: +1000 INR")
    logger.info(f"After Real Costs & Slippage: {res['net_pnl']} INR")
    logger.info(f"Total Fees: {res['total_costs']}, Slippage Cost: {res['slippage_cost']}")