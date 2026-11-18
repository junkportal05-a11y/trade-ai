"""
Database Seeder Script for ApexTrade AI
"""
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_db")

from app.core.database import engine, init_db, SessionLocal
from app.db.migrations import run_migrations
from app.db.models import RiskSettings, PortfolioState, PredictionsHistory

def seed():
    logger.info("Initializing database schema...")
    init_db()

    logger.info("Running migrations...")
    run_migrations(engine)

    db = SessionLocal()
    try:
        # Seed RiskSettings
        if db.query(RiskSettings).count() == 0:
            db.add(RiskSettings(
                daily_loss_limit=-3.0,
                daily_drawdown_limit=-4.0,
                max_consecutive_losses=5,
            ))
            logger.info("Seeded RiskSettings.")

        # Seed PortfolioState
        if db.query(PortfolioState).count() == 0:
            db.add(PortfolioState(
                current_equity=100000.0,
                peak_equity=100000.0,
                daily_equity=100000.0,
                sector_exposure="{}",
                active_positions="[]",
            ))
            logger.info("Seeded PortfolioState.")

        # Seed Sample Predictions History
        if db.query(PredictionsHistory).count() == 0:
            sample_predictions = [
                PredictionsHistory(
                    symbol="RELIANCE.NS",
                    prediction_type="BULLISH",
                    entry_price=2450.0,
                    target_price=2520.0,
                    stop_loss=2410.0,
                    confidence_score=85,
                    status="WIN",
                    pnl_pct=2.85,
                    actual_outcome="TARGET_HIT",
                ),
                PredictionsHistory(
                    symbol="TCS.NS",
                    prediction_type="BULLISH",
                    entry_price=3800.0,
                    target_price=3910.0,
                    stop_loss=3750.0,
                    confidence_score=78,
                    status="WIN",
                    pnl_pct=2.89,
                    actual_outcome="TARGET_HIT",
                ),
                PredictionsHistory(
                    symbol="INFY.NS",
                    prediction_type="BEARISH",
                    entry_price=1620.0,
                    target_price=1570.0,
                    stop_loss=1645.0,
                    confidence_score=72,
                    status="LOSS",
                    pnl_pct=-1.54,
                    actual_outcome="STOP_HIT",
                )
            ]
            db.add_all(sample_predictions)
            logger.info("Seeded sample PredictionsHistory.")

        db.commit()
        logger.info("[seed_db] Database seeded successfully!")
    except Exception as e:
        db.rollback()
        logger.error(f"[seed_db] Error seeding database: {e}", exc_info=True)
    finally:
        db.close()

if __name__ == "__main__":
    seed()
