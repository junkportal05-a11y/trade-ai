"""
backend/bot_trainer.py — Bot Strategy Trainer & Weight Optimizer for ApexTrade AI
Optimizes live signal parameters based on 30-Strategy Tournament results.
"""
import os
import json
import logging
from typing import Dict, Any
from strategy_tournament import run_full_tournament

logger = logging.getLogger("bot_trainer")
backend_dir = os.path.dirname(os.path.abspath(__file__))
WEIGHTS_FILE = os.path.join(backend_dir, "bot_strategy_weights.json")

def train_and_export_weights() -> Dict[str, Any]:
    """Execute tournament, select top strategies, and save optimal weights."""
    logger.info("Executing 30-strategy quantitative tournament...")
    results = run_full_tournament()
    if not results:
        logger.warning("No tournament results generated.")
        return {}

    top_5 = results[:5]
    total_score = sum(max(r["score"], 0.1) for r in top_5)
    weights = {r["strategy"]: round(max(r["score"], 0.1) / total_score, 4) for r in top_5}

    export_payload = {
        "best_strategy": results[0]["strategy"],
        "best_strategy_id": results[0]["strat_id"],
        "best_strategy_score": results[0]["score"],
        "best_strategy_win_rate": results[0]["win_rate"],
        "best_strategy_sharpe": results[0]["sharpe_ratio"],
        "ensemble_weights": weights,
        "total_strategies_evaluated": len(results),
        "total_datasets_evaluated": results[0]["datasets_tested"] if results else 0,
        "leaderboard": results,
    }

    with open(WEIGHTS_FILE, "w") as f:
        json.dump(export_payload, f, indent=2)

    logger.info(f"Bot strategy weights successfully saved to {WEIGHTS_FILE}")
    return export_payload

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_and_export_weights()
