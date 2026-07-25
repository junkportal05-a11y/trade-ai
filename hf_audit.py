"""Audit ApexTrade HF Space backtest predictions.

Fetches BACKTEST trades from the deployed API and prints strategy-level and
market-regime breakdowns. Requires ADMIN_PASSWORD in the environment; exits
early if it is missing.
"""

import os
import sys
import requests
import pandas as pd
import json

base_url = "https://apextrade-core-trade-ai-backend.hf.space"

admin_password = os.getenv("ADMIN_PASSWORD")
if not admin_password:
    sys.exit("ADMIN_PASSWORD environment variable is not set — refusing to send empty credentials.")

print("Logging in to HF Space...")
login_resp = requests.post(f"{base_url}/api/login", json={"username": "admin", "password": admin_password})
if login_resp.status_code != 200:
    print(f"Login failed: {login_resp.text}")
    import sys; sys.exit(1)

cookies = login_resp.cookies
print("Fetching predictions...")
resp = requests.get(f"{base_url}/api/predictions", cookies=cookies)
if resp.status_code != 200:
    print(f"Failed to fetch predictions: {resp.text}")
    import sys; sys.exit(1)

data = resp.json()
trades = [t for t in data if t.get('setup_type') == 'BACKTEST']

if not trades:
    print("No backtest trades found from API.")
    import sys; sys.exit(0)

df = pd.DataFrame(trades)
print(f"Loaded {len(df)} backtest trades.")

# Basic formatting
df['pnl_inr'] = pd.to_numeric(df['pnl_inr'], errors='coerce').fillna(0)
df['pnl_pct'] = pd.to_numeric(df['pnl_pct'], errors='coerce').fillna(0)
df['r_multiple'] = pd.to_numeric(df['r_multiple'], errors='coerce').fillna(0)
df['holding_time_minutes'] = pd.to_numeric(df['holding_time_minutes'], errors='coerce').fillna(0)
df['confidence_probability'] = pd.to_numeric(df['confidence_probability'], errors='coerce').fillna(0)
df['confidence_score'] = pd.to_numeric(df['confidence_score'], errors='coerce').fillna(0)

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
    strategies.append({
        'Strategy': strategy, 'Trades': total, 'Wins': wins, 'Losses': losses, 'Timeouts': timeouts,
        'WinRate%': round(win_rate, 2), 'PF': round(pf, 2), 'EV': round(ev, 2)
    })
print("\n--- Strategy-Level Breakdown ---")
print(pd.DataFrame(strategies).sort_values('Trades', ascending=False).to_markdown())

# 2. Market Regime
regimes = []
for regime, group in df.groupby('market_regime_snapshot'):
    total = len(group)
    wins = len(group[group['status'] == 'WIN'])
    losses = len(group[group['status'] == 'LOSS'])
    timeouts = len(group[group['status'] == 'TIMEOUT'])
    regimes.append({
        'Regime': regime, 'Trades': total, 'Wins': wins, 'Losses': losses, 'Timeouts': timeouts
    })
print("\n--- Market Regime Breakdown ---")
print(pd.DataFrame(regimes).sort_values('Trades', ascending=False).to_markdown())

# Print some loss samples
print("\n--- Sample Losses ---")
samples = df[df['status'] == 'LOSS'][['prediction_type', 'entry_price', 'target_price', 'stop_loss', 'exit_price', 'pnl_pct']].head(5)
print(samples.to_markdown())
