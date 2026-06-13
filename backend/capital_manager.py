class CapitalManagementEngine:
    @staticmethod
    def calculate_risk_percentage(classification: str) -> float:
        """
        Determines the percentage of capital to risk based on Trade Quality Engine classification.
        """
        if classification == "ELITE_CANDIDATE":
            return 0.0100 # 1.00%
        elif classification == "INTRADAY_CANDIDATE":
            return 0.0075 # 0.75%
        elif classification == "WATCHLIST":
            return 0.0025 # 0.25%
        else: # REJECT
            return 0.0000 # 0%
