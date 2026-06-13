import pandas as pd
import logging

logger = logging.getLogger("FeatureAttribution")

class FeatureAttributionEngine:
    """
    Calculates the exact Net Expected Value (EV) contribution of individual 
    signal components (Volume, News, Sector RS, etc.).
    """
    
    def __init__(self):
        # We track the performance of trades that had a specific feature active vs inactive
        self.feature_ledger = []
        
    def log_trade(self, trade_result: dict, features_active: dict):
        """
        trade_result: {"net_pnl": float, "is_win": bool}
        features_active: {"high_volume": True, "strong_sector": False, ...}
        """
        record = {
            "net_pnl": trade_result["net_pnl"],
            "is_win": 1 if trade_result["is_win"] else 0
        }
        record.update(features_active)
        self.feature_ledger.append(record)
        
    def generate_report(self):
        """
        Outputs the edge contribution of each feature.
        """
        if not self.feature_ledger:
            logger.warning("No trades logged for feature attribution.")
            return None
            
        df = pd.DataFrame(self.feature_ledger)
        total_ev = df["net_pnl"].mean()
        
        report = []
        feature_cols = [c for c in df.columns if c not in ["net_pnl", "is_win"]]
        
        for feature in feature_cols:
            # EV when feature is present
            with_feature = df[df[feature] == True]
            without_feature = df[df[feature] == False]
            
            ev_with = with_feature["net_pnl"].mean() if not with_feature.empty else 0
            ev_without = without_feature["net_pnl"].mean() if not without_feature.empty else 0
            
            # Marginal contribution
            contribution = ev_with - ev_without
            
            report.append({
                "Feature": feature,
                "EV_With": round(ev_with, 2),
                "EV_Without": round(ev_without, 2),
                "Net_Edge_Contribution": round(contribution, 2)
            })
            
        report_df = pd.DataFrame(report).sort_values(by="Net_Edge_Contribution", ascending=False)
        logger.info("\n--- Feature Attribution Report ---")
        for _, r in report_df.iterrows():
            logger.info(f"Feature: {r['Feature']:<15} | Edge Contribution: ₹{r['Net_Edge_Contribution']}")
            
        return report_df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    engine = FeatureAttributionEngine()
    
    # Simulate trades
    for i in range(100):
        # High volume usually means higher win rate
        high_vol = i % 2 == 0
        # News is random noise
        news = i % 3 == 0
        
        pnl = 100 if high_vol else -50
        pnl += 10 if news else -10 # Minimal impact
        
        engine.log_trade(
            {"net_pnl": pnl, "is_win": pnl > 0},
            {"High_Volume": high_vol, "Positive_News": news}
        )
        
    engine.generate_report()
