"""
Weekly Jobs — Operational Hygiene

Runs Sunday night maintenance tasks:
  1. Rebuild the correlation matrix from fresh historical data
  2. (Future) Recompute ATR percentiles, regime baselines, etc.

Can be triggered from trading_agent.py's weekend block
or run standalone via cron/task scheduler.
"""

import logging
from datetime import datetime
from quant.correlation_matrix import CorrelationEngine

logger = logging.getLogger("WeeklyJobs")


def run_weekly_maintenance():
    """
    Execute all weekly maintenance tasks.
    Should be called once per week (Sunday night preferred).
    """
    logger.info(f"=== Weekly Maintenance Started at {datetime.now().isoformat()} ===")

    # 1. Rebuild Correlation Matrix
    try:
        engine = CorrelationEngine()
        engine.build_matrix(lookback_days=90)
        if engine.matrix_build_failed:
            logger.error("Correlation matrix rebuild FAILED (no data)")
        else:
            logger.info(
                f"Correlation matrix rebuilt successfully. "
                f"Shape: {engine.correlation_matrix.shape}. "
                f"Built at: {engine.last_built_date.isoformat()}"
            )
    except Exception as e:
        logger.error(f"Correlation matrix rebuild error: {e}")

    # 2. (Future) Recompute ATR historical percentiles
    # 3. (Future) Purge stale prediction_history records

    logger.info("=== Weekly Maintenance Complete ===")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    run_weekly_maintenance()
