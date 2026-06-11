import asyncio
from datetime import datetime
import db

async def governance_loop():
    """
    Phase Omega Nightly Governance Worker
    Recalculates Strategy Health, Confidence Calibration, Portfolio State,
    and produces the Nightly Governance Report.
    """
    while True:
        try:
            # For testing purposes, we can run this check frequently but only execute once per day
            now = db._now_ist()
            # In a production environment this should trigger at midnight
            
            # Let's perform the governance tasks
            run_governance_tasks()
            
            # Sleep for 1 hour to avoid busy looping
            await asyncio.sleep(3600)
            
        except Exception as e:
            print(f"[governance_loop] Error: {e}")
            await asyncio.sleep(3600)


def run_governance_tasks():
    # 1. Recalculate Strategy Health
    # In a real scenario we aggregate the PnL of each setup_type over lifetime, last 30 days, last 90 days.
    # For now we'll do a basic pass that scans predictions_history and updates strategy_health.
    
    with db._conn() as c:
        # Simple strategy update logic
        rows = c.execute("SELECT setup_type, SUM(pnl_inr) as total_pnl FROM predictions_history WHERE status IN ('WIN', 'LOSS') GROUP BY setup_type").fetchall()
        for r in rows:
            setup = r["setup_type"]
            if not setup: continue
            
            # Dummy calculate PF
            wins = c.execute("SELECT SUM(pnl_inr) as gross_profit FROM predictions_history WHERE setup_type=? AND status='WIN'", (setup,)).fetchone()["gross_profit"] or 0
            losses = c.execute("SELECT SUM(abs(pnl_inr)) as gross_loss FROM predictions_history WHERE setup_type=? AND status='LOSS'", (setup,)).fetchone()["gross_loss"] or 0
            
            lifetime_pf = (wins / losses) if losses > 0 else (wins if wins > 0 else 0)
            
            # Last 30 days
            # Simplified for now
            last_30_pf = lifetime_pf * 0.9 # Mock
            last_90_pf = lifetime_pf * 0.95 # Mock
            
            # Determine status
            status = 'ACTIVE'
            if last_30_pf < 0.8:
                status = 'QUARANTINED'
            elif last_30_pf < 1.0:
                status = 'DECAY_WARNING'
                
            c.execute("""
                INSERT INTO strategy_health (setup_type, lifetime_pf, last_30_pf, last_90_pf, status)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(setup_type) DO UPDATE SET 
                    lifetime_pf=excluded.lifetime_pf,
                    last_30_pf=excluded.last_30_pf,
                    last_90_pf=excluded.last_90_pf,
                    status=excluded.status
            """, (setup, lifetime_pf, last_30_pf, last_90_pf, status))
            
        # 2. Update Daily Governance Report
        today = db._now_ist()[:10]
        report = c.execute("SELECT * FROM daily_governance_reports WHERE report_date=?", (today,)).fetchone()
        
        if not report:
            c.execute("""
                INSERT INTO daily_governance_reports 
                (report_date, pf, ev, drawdown, regime, best_strategy, worst_strategy, calibration_error, kill_switch_events, exposure_violations)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (today, 0.0, 0.0, 0.0, "UNKNOWN", "NONE", "NONE", 0.0, 0, 0))
            
        c.commit()
    print("[governance_loop] Governance tasks completed.")
