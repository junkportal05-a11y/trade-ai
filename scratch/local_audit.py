import asyncio
import pandas as pd
from unittest.mock import patch
import sys
import os

sys.path.append('backend')
from historical_simulator import HistoricalSimulator, simulation_status
import db

local_trades = []

def mock_insert_prediction(trade):
    local_trades.append(trade)

async def main():
    sim = HistoricalSimulator()
    sim.SYMBOLS = ['RELIANCE.NS', 'TCS.NS', 'INFY.NS', 'HDFCBANK.NS']  # Subset for speed
    
    with patch('historical_simulator.db.insert_prediction', side_effect=mock_insert_prediction, create=True):
        await sim.simulate('2024-01-01', '2024-12-31')
        
    print(f"Total trades generated: {len(local_trades)}")
    
    if not local_trades:
        print("No trades generated. Bug exists in generation.")
        return
        
    df = pd.DataFrame(local_trades)
    
    # Let's check win rate
    wins = len(df[df['status'] == 'WIN'])
    losses = len(df[df['status'] == 'LOSS'])
    timeouts = len(df[df['status'] == 'TIMEOUT'])
    total = len(df)
    
    print(f"\n--- Results for Subset ---")
    print(f"Wins: {wins}")
    print(f"Losses: {losses}")
    print(f"Timeouts: {timeouts}")
    print(f"Win Rate: {(wins/total)*100:.2f}%")
    
    if total > 0:
        print("\nSample Loss:")
        print(df[df['status'] == 'LOSS'][['prediction_type', 'entry_price', 'target_price', 'stop_loss', 'exit_price', 'pnl_pct']].head(2).to_string())
        
        print("\nSample Win:")
        if wins > 0:
            print(df[df['status'] == 'WIN'][['prediction_type', 'entry_price', 'target_price', 'stop_loss', 'exit_price', 'pnl_pct']].head(2).to_string())

if __name__ == "__main__":
    asyncio.run(main())
