import pandas as pd
import json
import sys
import numpy as np

import psycopg2

import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), 'backend', '.env'), override=False)
DATABASE_URL = os.getenv('DATABASE_URL')


print("Fetching trades from DB...")
try:
    conn = psycopg2.connect(DATABASE_URL)
    query = "SELECT * FROM predictions_history WHERE setup_type = 'BACKTEST';"
    df = pd.read_sql(query, conn)
    conn.close()
except Exception as e:
    print(f"Error connecting to DB: {e}")
    sys.exit()

print("\n--- RUNNING CRUD VERIFICATION (RLS TEST) ---")
try:
    conn_crud = psycopg2.connect(DATABASE_URL)
    cur = conn_crud.cursor()
    
    # 1. INSERT
    cur.execute("INSERT INTO predictions_history (symbol, prediction_date, prediction_type, entry_price, target_price, stop_loss, confidence_score, status, setup_type) VALUES ('TEST.NS', '2026-01-01', 'BULLISH', 100, 110, 90, 80, 'OPEN', 'RLS_TEST') RETURNING id;")
    test_id = cur.fetchone()[0]
    print(f"[OK] INSERT successful (ID: {test_id})")

    # 2. SELECT
    cur.execute("SELECT symbol FROM predictions_history WHERE id = %s;", (test_id,))
    res = cur.fetchone()
    print(f"[OK] SELECT successful (Symbol: {res[0]})")

    # 3. UPDATE
    cur.execute("UPDATE predictions_history SET status = 'CLOSED' WHERE id = %s;", (test_id,))
    print(f"[OK] UPDATE successful")

    # 4. DELETE
    cur.execute("INSERT INTO signals_history (symbol, name, sector, signal_type, confidence, score, entry_price, target, stop_loss, rr_ratio, atr, status, scanned_at, scan_type) VALUES ('TEST_SIG', 'Test', 'TECH', 'BUY', 80, 80, 100, 110, 90, 2, 1, 'ACTIVE', '2026-01-01', 'RLS_TEST') RETURNING id;")
    sig_id = cur.fetchone()[0]
    cur.execute("DELETE FROM signals_history WHERE id = %s;", (sig_id,))
    print(f"[OK] DELETE successful (Signals ID: {sig_id})")

    # Cleanup
    cur.execute("DELETE FROM predictions_history WHERE id = %s;", (test_id,))
    
    conn_crud.commit()
    cur.close()
    conn_crud.close()
    print("[OK] All CRUD Operations Passed!\n")
except Exception as e:
    print(f"[FAIL] CRUD Test Failed: {e}")
    sys.exit(1)

if df.empty:
    print("No backtest trades found in DB!")
    sys.exit()

print(f"Loaded {len(df)} trades.")

# Basic formatting
df['pnl_inr'] = pd.to_numeric(df['pnl_inr'], errors='coerce').fillna(0)
df['pnl_pct'] = pd.to_numeric(df['pnl_pct'], errors='coerce').fillna(0)
df['r_multiple'] = pd.to_numeric(df['r_multiple'], errors='coerce').fillna(0)
df['holding_time_minutes'] = pd.to_numeric(df['holding_time_minutes'], errors='coerce').fillna(0)
df['confidence_probability'] = pd.to_numeric(df['confidence_probability'], errors='coerce').fillna(0)
df['confidence_score'] = pd.to_numeric(df['confidence_score'], errors='coerce').fillna(0)

# Save for reference
df.to_csv('audit_data.csv', index=False)

def print_section(title, data_df):
    print(f"\n{'='*50}")
    print(f" {title} ")
    print(f"{'='*50}")
    print(data_df.to_markdown())

# 1. Strategy Level
strategies = []
for strategy, group in df.groupby('setup_type'):
    total = len(group)
    wins = len(group[group['status'] == 'WIN'])
    losses = len(group[group['status'] == 'LOSS'])
    timeouts = len(group[group['status'] == 'TIMEOUT'])
    win_rate = (wins / total * 100) if total > 0 else 0
    pf = abs(group[group['status'] == 'WIN']['pnl_inr'].sum() / group[group['status'] == 'LOSS']['pnl_inr'].sum()) if group[group['status'] == 'LOSS']['pnl_inr'].sum() != 0 else 0
    ev = group['pnl_inr'].mean()
    avg_hold = group['holding_time_minutes'].mean()
    avg_r = group['r_multiple'].mean()
    strategies.append({
        'Strategy': strategy, 'Trades': total, 'Wins': wins, 'Losses': losses, 'Timeouts': timeouts,
        'WinRate%': round(win_rate, 2), 'PF': round(pf, 2), 'EV': round(ev, 2), 
        'AvgHold': round(avg_hold, 1), 'Avg_R': round(avg_r, 2)
    })
print_section("1. Strategy-Level Breakdown", pd.DataFrame(strategies).sort_values('Trades', ascending=False))

# 2. Market Regime
regimes = []
for regime, group in df.groupby('market_regime_snapshot'):
    total = len(group)
    wins = len(group[group['status'] == 'WIN'])
    losses = len(group[group['status'] == 'LOSS'])
    timeouts = len(group[group['status'] == 'TIMEOUT'])
    pf = abs(group[group['status'] == 'WIN']['pnl_inr'].sum() / group[group['status'] == 'LOSS']['pnl_inr'].sum()) if group[group['status'] == 'LOSS']['pnl_inr'].sum() != 0 else 0
    ev = group['pnl_inr'].mean()
    drawdown = group['pnl_inr'].min() # approximate
    regimes.append({
        'Regime': regime, 'Trades': total, 'Wins': wins, 'Losses': losses, 'Timeouts': timeouts,
        'PF': round(pf, 2), 'EV': round(ev, 2), 'Drawdown': round(drawdown, 2)
    })
print_section("2. Market Regime Breakdown", pd.DataFrame(regimes).sort_values('Trades', ascending=False))

# 3. TQS Validation
df['tqs_bucket'] = pd.cut(df['confidence_probability'], bins=[0, 69, 79, 89, 100], labels=['Below 70', '70-79 TQS', '80-89 TQS', '90-100 TQS'])
tqs = []
for bucket, group in df.groupby('tqs_bucket', observed=False):
    total = len(group)
    if total == 0: continue
    wins = len(group[group['status'] == 'WIN'])
    losses = len(group[group['status'] == 'LOSS'])
    timeouts = len(group[group['status'] == 'TIMEOUT'])
    win_rate = (wins / total * 100)
    pf = abs(group[group['status'] == 'WIN']['pnl_inr'].sum() / group[group['status'] == 'LOSS']['pnl_inr'].sum()) if group[group['status'] == 'LOSS']['pnl_inr'].sum() != 0 else 0
    tqs.append({
        'Bucket': bucket, 'Trades': total, 'Wins': wins, 'Losses': losses, 'Timeouts': timeouts,
        'WinRate%': round(win_rate, 2), 'PF': round(pf, 2)
    })
print_section("3. Trade Quality Score Validation", pd.DataFrame(tqs))

# 4. Confidence Calibration
df['conf_bucket'] = pd.cut(df['confidence_score'], bins=[0, 59, 69, 79, 89, 100], labels=['<60%', '60-70%', '70-80%', '80-90%', '90-100%'])
cals = []
for bucket, group in df.groupby('conf_bucket', observed=False):
    total = len(group)
    if total == 0: continue
    wins = len(group[group['status'] == 'WIN'])
    win_rate = (wins / total * 100)
    predicted = group['confidence_score'].mean()
    error = predicted - win_rate
    cals.append({
        'Bucket': bucket, 'Trades': total, 'Pred WinRate': round(predicted, 2), 
        'Act WinRate': round(win_rate, 2), 'Error': round(error, 2)
    })
print_section("4. Confidence Calibration Audit", pd.DataFrame(cals))

# 7. Resolution Engine Audit
# Show a random timeout and loss
sample = df[df['status'] == 'LOSS'].head(1)
print("\n--- Sample Loss Trade ---")
print(sample[['symbol', 'prediction_date', 'prediction_type', 'entry_price', 'target_price', 'stop_loss', 'exit_price', 'resolved_at']].to_dict('records'))

# 8. Timeout Investigation
timeouts_df = df[df['status'] == 'TIMEOUT']
if len(timeouts_df) > 0:
    avg_pnl = timeouts_df['pnl_pct'].mean()
    pos = len(timeouts_df[timeouts_df['pnl_pct'] > 0.1]) / len(timeouts_df) * 100
    neg = len(timeouts_df[timeouts_df['pnl_pct'] < -0.1]) / len(timeouts_df) * 100
    be = len(timeouts_df[(timeouts_df['pnl_pct'] >= -0.1) & (timeouts_df['pnl_pct'] <= 0.1)]) / len(timeouts_df) * 100
    print("\n--- Timeout Investigation ---")
    print(f"Total Timeouts: {len(timeouts_df)}")
    print(f"Avg PnL: {avg_pnl:.2f}%")
    print(f"Positive (>0.1%): {pos:.2f}%")
    print(f"Negative (<-0.1%): {neg:.2f}%")
    print(f"Breakeven (+/- 0.1%): {be:.2f}%")

# 9. Risk/Reward
rr_data = []
for strategy, group in df.groupby('setup_type'):
    total = len(group)
    avg_stop = abs(group['entry_price'] - group['stop_loss']).mean()
    avg_target = abs(group['entry_price'] - group['target_price']).mean()
    avg_atr = group['atr'].mean()
    avg_hold = group['holding_time_minutes'].mean()
    rr_data.append({
        'Strategy': strategy, 'Avg Stop Dist': round(avg_stop, 2), 
        'Avg Target Dist': round(avg_target, 2), 'Avg ATR': round(avg_atr, 2),
        'Avg Hold Time': round(avg_hold, 1)
    })
print_section("9. Risk/Reward Audit", pd.DataFrame(rr_data))
