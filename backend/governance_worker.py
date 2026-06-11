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
            
            # Calculate metrics
            total_trades = c.execute("SELECT COUNT(*) as c FROM predictions_history WHERE setup_type=? AND status IN ('WIN', 'LOSS')", (setup,)).fetchone()["c"] or 0
            wins_count = c.execute("SELECT COUNT(*) as c FROM predictions_history WHERE setup_type=? AND status='WIN'", (setup,)).fetchone()["c"] or 0
            
            win_rate = (wins_count / total_trades) * 100 if total_trades > 0 else 0
            
            wins_val = c.execute("SELECT SUM(pnl_inr) as gp FROM predictions_history WHERE setup_type=? AND status='WIN'", (setup,)).fetchone()["gp"] or 0
            losses_val = c.execute("SELECT SUM(abs(pnl_inr)) as gl FROM predictions_history WHERE setup_type=? AND status='LOSS'", (setup,)).fetchone()["gl"] or 0
            
            lifetime_pf = (wins_val / losses_val) if losses_val > 0 else (wins_val if wins_val > 0 else 0)
            
            total_pnl = wins_val - losses_val
            ev = (total_pnl / total_trades) if total_trades > 0 else 0
            
            # Simplified for now
            last_30_pf = lifetime_pf * 0.9 # Mock
            last_90_pf = lifetime_pf * 0.95 # Mock
            
            # Dummy drawdown & calibration for edge score
            drawdown = 5.0
            calibration_accuracy = 95.0
            
            # Edge Score Formula: PF*10 + EV_normalized + WinRate*0.5 + Calibration - Drawdown
            # Bounded 0-100
            raw_edge = (lifetime_pf * 10) + min(ev, 20) + (win_rate * 0.5) + calibration_accuracy - drawdown
            edge_score = max(0.0, min(100.0, raw_edge))
            
            # Determine status
            status = 'ACTIVE'
            if total_trades < 100:
                status = 'COLLECTING_DATA'
            elif last_30_pf < 0.8:
                status = 'QUARANTINED'
            elif last_30_pf < 1.0:
                status = 'DECAY_WARNING'
                
            c.execute("""
                INSERT INTO strategy_health (setup_type, lifetime_pf, last_30_pf, last_90_pf, edge_score, status)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(setup_type) DO UPDATE SET 
                    lifetime_pf=excluded.lifetime_pf,
                    last_30_pf=excluded.last_30_pf,
                    last_90_pf=excluded.last_90_pf,
                    edge_score=excluded.edge_score,
                    status=excluded.status
            """, (setup, lifetime_pf, last_30_pf, last_90_pf, edge_score, status))
            
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
