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

    # Pruned roster: only ACTIVE (positive OOS expectancy) strategies may form
    # the live ensemble; RETIRED rows stay in the audit leaderboard only.
    active_results = [r for r in results if r.get("status", "ACTIVE") == "ACTIVE"]
    top_5 = active_results[:5]
    if not top_5:
        logger.warning("No ACTIVE strategies survived walk-forward pruning; weights not updated.")
        return {"leaderboard": results, "active_strategies": 0}

    total_score = sum(max(r["score"], 0.1) for r in top_5)
    weights = {r["strategy"]: round(max(r["score"], 0.1) / total_score, 4) for r in top_5}

    best = top_5[0]
    export_payload = {
        "generated_by": "bot_trainer.walk_forward",
        "validation": {
            "split": {"in_sample": "2019-2023", "out_of_sample": "2024-2026"},
            "weights": {"in_sample": 0.40, "out_of_sample": 0.60},
        },
        "best_strategy": best["strategy"],
        "best_strategy_id": best["strat_id"],
        "best_strategy_score": best["score"],
        "best_strategy_win_rate": best["win_rate"],
        "best_strategy_sharpe": best["sharpe_ratio"],
        "best_strategy_profit_factor": best.get("profit_factor", 0.0),
        "best_strategy_selected_params": best.get("selected_params", {}),
        "ensemble_weights": weights,
        "active_strategies": len(active_results),
        "retired_strategies": len(results) - len(active_results),
        "total_strategies_evaluated": len(results),
        "total_datasets_evaluated": best.get("datasets_tested", 0),
        "leaderboard": results,
    }

    with open(WEIGHTS_FILE, "w") as f:
        json.dump(export_payload, f, indent=2)

    logger.info(f"Bot strategy weights successfully saved to {WEIGHTS_FILE}")
    return export_payload

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_and_export_weights()
