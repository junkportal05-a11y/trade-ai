"""Weekly and daily scheduled jobs for ApexTrade.

Implements scheduled session refresh and market data maintenance.
"""
import threading
import time
from datetime import datetime, timezone
from app.core.logging import logger
from angelone_feed import get_angelone_feed
def refresh_angelone_session():
    """Refresh AngelOne session using stored refresh token.

    Returns:
        bool: True if refresh succeeded, False otherwise
    """
    try:
        feed = get_angelone_feed()
        saved = db.get_angelone_session() or {}
        refresh_token = saved.get('refresh_token')

        if not refresh_token:
            logger.warning("No refresh token found in storage — skipping scheduled refresh")
            return False

        # Decrypt refresh token if needed
        if fernet:
            try:
                refresh_token = fernet.decrypt(refresh_token.encode()).decode()
            except Exception:
                pass

        success = feed.refresh_session(refresh_token)
        if success:
            logger.info("Scheduled AngelOne session refresh completed successfully")
        else:
            logger.warning("Scheduled AngelOne session refresh failed")
        return success
    except Exception as e:
        logger.error(f"Error during scheduled session refresh: {e}")
        return False
def calculate_hours_until_next_refresh():
    """Calculate hours until next refresh based on session age.

    Tokens expire after ~23 hours, refresh when < 2 hours remaining.
    """
    try:
        import db
        saved = db.get_angelone_session() or {}
        updated_at = saved.get('updated_at')

        if not updated_at:
            return 23.0

        age_hours = (
            datetime.now(timezone.utc) - datetime.fromisoformat(updated_at)
        ).total_seconds() / 3600

        # Refresh when 2 hours remain before expiry
        hours_remaining = 23.0 - age_hours
        return max(0.1, hours_remaining)
    except Exception as e:
        logger.error(f"Error calculating refresh time: {e}")
        return 23.0
def run_scheduled_refresh(interval_minutes: int = 120):
    """Run scheduled refresh loop.

    Args:
        interval_minutes: How often to check and potentially refresh (default 2 hours)
    """
    while True:
        try:
            hours_until = calculate_hours_until_next_refresh()
            wait_minutes = min(interval_minutes, hours_until * 60)
            logger.info(f"Scheduled refresh: sleeping {wait_minutes:.0f} minutes")
            time.sleep(wait_minutes * 60)

            refresh_angelone_session()
        except Exception as e:
            logger.error(f"Scheduled refresh loop error: {e}")
            time.sleep(300)
_run_thread = None
def start_scheduled_refresh():
    """Start the scheduled refresh thread if not already running."""
    global _run_thread
    if _run_thread is None or not _run_thread.is_alive():
        _run_thread = threading.Thread(target=run_scheduled_refresh, daemon=True)
        _run_thread.start()
        logger.info("Started scheduled session refresh thread")
def run_weekly_tasks():
    """Run daily maintenance tasks.

    Called by external scheduler or can be run manually.
    """
    refresh_angelone_session()
    logger.info("Weekly tasks completed")