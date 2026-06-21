class TradeQualityEngine:
    @staticmethod
    def calculate_tqs(confidence_score: float, is_long: bool, regime: str, volatility: float, volume_expansion: float) -> dict:
        """
        Calculates the Trade Quality Score (0-100) based on strict parameters.
        Returns the score and the routing classification.
        """
        tqs = confidence_score
        
        # Regime Alignment Bonus/Penalty
        if regime == "TRENDING":
            tqs += 10
        elif regime == "RANGING":
            tqs += 0
        elif regime == "VOLATILE":
            tqs -= 10
        elif regime == "UNCLEAR":
            tqs -= 25
            
        # Volume Expansion Bonus
        if volume_expansion > 1.5:
            tqs += 10
            
        tqs = max(0, min(100, tqs))
        
        # Classification Routing
        if tqs < 72:
            classification = "REJECT"
        elif tqs < 80:
            classification = "WATCHLIST"
        elif tqs < 90:
            classification = "INTRADAY_CANDIDATE"
        else:
            classification = "ELITE_CANDIDATE"
            
        return {
            "score": round(tqs, 2),
            "classification": classification
        }
