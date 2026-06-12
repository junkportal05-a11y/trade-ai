import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
from unittest import mock
import asyncio
from tqdm import tqdm

import db
import signals

logger = logging.getLogger("HistoricalSimulator")

class SimulationStatus:
    def __init__(self):
        self.is_running = False
        self.progress = 0.0
        self.current_symbol = ""
        self.stats = {
            "total_signals": 0,
            "wins": 0,
            "losses": 0,
            "timeouts": 0,
            "errors": 0
        }

simulation_status = SimulationStatus()

class HistoricalSimulator:
    def __init__(self):
        self.logger = logging.getLogger("HistoricalSimulator")
        self.data_dir = Path("historical_data/NIFTY50")
        
        # Default Simulation Parameters
        self.BASE_CAPITAL = 100000  # ₹1,00,000 starting capital
        self.RISK_PERCENT = 1.0     # 1% risk per trade
        self.POSITION_SIZE_PERCENT = 10.0  # 10% of capital per position

    def validate_trade_record(self, trade: dict) -> bool:
        """Validate all 25 required fields are present"""
        required_fields = [
            'symbol', 'prediction_date', 'prediction_type', 'entry_price', 'target_price',
            'stop_loss', 'confidence_score', 'rsi', 'macd', 'adx',
            'sector', 'market_cap', 'volume_ratio', 'vwap_distance', 'atr',
            'news_score', 'market_breadth', 'sector_strength', 'nifty_trend',
            'actual_outcome', 'status', 'reason', 'resolved_at', 'manual_override_reason',
            'setup_type', 'market_regime_snapshot', 'risk_amount', 'confidence_probability',
            'r_multiple', 'exit_price', 'holding_time_minutes', 'pnl_pct', 'pnl_inr',
            'resolution_reason'
        ]
        
        missing = [f for f in required_fields if f not in trade]
        if missing:
            self.logger.error(f"Missing fields: {missing}")
            return False
        return True

    def _load_data(self, start_date: str, end_date: str):
        """Load parquet data for the given date range"""
        all_data = {}
        if not self.data_dir.exists():
            self.logger.error("No historical data found.")
            return all_data

        for filepath in self.data_dir.glob("*.parquet"):
            symbol = filepath.stem.split("_")[0]
            try:
                df = pd.read_parquet(filepath)
                # Filter by date
                df = df.loc[start_date:end_date]
                if not df.empty:
                    all_data[symbol] = df
            except Exception as e:
                self.logger.error(f"Error loading {filepath}: {e}")
                
        return all_data

    def _resolve_trade(self, df_forward: pd.DataFrame, entry_price: float, target: float, stop_loss: float, is_long: bool):
        """Auto-resolver logic for generated signals."""
        for idx, row in df_forward.iterrows():
            high = row['High']
            low = row['Low']
            close = row['Close']

            if is_long:
                if high >= target:
                    return 'WIN', target, idx
                if low <= stop_loss:
                    return 'LOSS', stop_loss, idx
            else:
                if low <= target:
                    return 'WIN', target, idx
                if high >= stop_loss:
                    return 'LOSS', stop_loss, idx
                    
            # Timeout if it's the last tick of the day
            if idx == df_forward.index[-1]:
                return 'TIMEOUT', close, idx

        # If loop finishes without hitting
        return 'TIMEOUT', df_forward.iloc[-1]['Close'], df_forward.index[-1]

    async def simulate(self, start_date: str, end_date: str):
        try:
            simulation_status.is_running = True
            simulation_status.stats = {
                "total_signals": 0, "wins": 0, "losses": 0, "timeouts": 0, "errors": 0
            }
            
            all_data = self._load_data(start_date, end_date)
            
            if not all_data:
                self.logger.warning("No data to simulate.")
                return
            
            total_symbols = len(all_data)
            processed_symbols = 0

            for symbol, df in all_data.items():
                simulation_status.current_symbol = symbol
                
                # Group by day
                days = np.unique(df.index.date)
                
                for day in tqdm(days, desc=f"Simulating {symbol}"):
                    df_day = df[df.index.date == day]
                    
                    for i in range(20, len(df_day) - 5): # Ensure there's some forward data for resolution
                        current_time = df_day.index[i]
                            
                        # The sliding window
                        historical_window = df_day.iloc[:i+1]
                        
                        def mock_download_market_data(sym, period, interval):
                            if interval == "1d":
                                return None # Ignore daily trend caching for backtesting
                            return historical_window

                        # Clear macro cache to prevent pollution across symbols and days
                        if hasattr(signals, "_MACRO_CACHE"):
                            signals._MACRO_CACHE.clear()

                        # Mocking live data fetch and market open check
                        with mock.patch('signals._download_market_data', side_effect=mock_download_market_data), \
                             mock.patch('signals.is_nse_market_open', return_value=True):
                            
                            try:
                                result = signals.analyse_symbol(
                                    symbol=symbol,
                                    name=symbol,
                                    sector="General",
                                    style="Intraday Momentum",
                                    risk="Medium",
                                    segment="NSE",
                                    capital=self.BASE_CAPITAL * (self.POSITION_SIZE_PERCENT / 100)
                                )
                                
                                if result and abs(result.get('score', 0)) >= 4:
                                    simulation_status.stats["total_signals"] += 1
                                    
                                    # Signal Details
                                    signal_type = 'BUY' if result.get('score', 0) > 0 else 'SELL'
                                    entry_price = result.get('current_price', df_day.iloc[i]['Close'])
                                    
                                    # Fallback to ATR-based stops if target/stop is 0
                                    target = result.get('target', 0)
                                    stop_loss = result.get('stop_loss', 0)
                                    atr = result.get('atr', 20.0)
                                    if target == 0 or stop_loss == 0:
                                        if signal_type == 'BUY':
                                            stop_loss = entry_price - (2 * atr)
                                            target = entry_price + (4 * atr)
                                        else:
                                            stop_loss = entry_price + (2 * atr)
                                            target = entry_price - (4 * atr)
                                            
                                    is_long = signal_type == 'BUY'
                                    
                                    # Auto Resolver
                                    df_forward = df_day.iloc[i+1:]
                                    if df_forward.empty:
                                        continue
                                        
                                    outcome, exit_price, exit_time = self._resolve_trade(df_forward, entry_price, target, stop_loss, is_long)
                                    
                                    if outcome == 'WIN':
                                        simulation_status.stats["wins"] += 1
                                    elif outcome == 'LOSS':
                                        simulation_status.stats["losses"] += 1
                                    else:
                                        simulation_status.stats["timeouts"] += 1
                                        
                                    # PnL Calculation
                                    if is_long:
                                        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
                                    else:
                                        pnl_pct = ((entry_price - exit_price) / entry_price) * 100
                                        
                                    capital_deployed = self.BASE_CAPITAL * (self.POSITION_SIZE_PERCENT / 100)
                                    risk_amount = self.BASE_CAPITAL * (self.RISK_PERCENT / 100)
                                    pnl_inr = capital_deployed * (pnl_pct / 100)
                                    
                                    # Construct trade record
                                    trade_record = {
                                        'symbol': symbol,
                                        'prediction_date': current_time.isoformat(),
                                        'prediction_type': signal_type,
                                        'entry_price': entry_price,
                                        'target_price': target,
                                        'stop_loss': stop_loss,
                                        'confidence_score': result.get('confidence', 0),
                                        'rsi': result.get('metrics', {}).get('rsi', 0),
                                        'macd': result.get('metrics', {}).get('macd', 0),
                                        'adx': result.get('metrics', {}).get('adx', 0),
                                        'sector': "General",
                                        'market_cap': 0,
                                        'volume_ratio': 1.0,
                                        'vwap_distance': 0.0,
                                        'atr': 0.0,
                                        'news_score': 0.0,
                                        'market_breadth': 0.0,
                                        'sector_strength': 0.0,
                                        'nifty_trend': "UNKNOWN",
                                        'actual_outcome': pnl_pct,
                                        'status': outcome,
                                        'reason': result.get('reason', ''),
                                        'resolved_at': exit_time.isoformat(),
                                        'manual_override_reason': "",
                                        'setup_type': "BACKTEST",
                                        'market_regime_snapshot': "",
                                        'risk_amount': risk_amount,
                                        'confidence_probability': result.get('confidence', 0),
                                        'r_multiple': pnl_pct / self.RISK_PERCENT if self.RISK_PERCENT else 0,
                                        'exit_price': exit_price,
                                        'holding_time_minutes': (exit_time - current_time).total_seconds() / 60,
                                        'pnl_pct': pnl_pct,
                                        'pnl_inr': pnl_inr,
                                        'resolution_reason': f"Hit {outcome}"
                                    }
                                    
                                    if self.validate_trade_record(trade_record):
                                        try:
                                            # Assuming predictions_history allows insertion like this
                                            db.insert_prediction(trade_record)
                                        except Exception as e:
                                            self.logger.error(f"DB Insert failed: {e}")
                                        
                            except Exception as e:
                                simulation_status.stats["errors"] += 1
                                self.logger.error(f"Error analyzing {symbol} at {current_time}: {e}")
                                
                processed_symbols += 1
                simulation_status.progress = (processed_symbols / total_symbols) * 100
                                
        except Exception as e:
            self.logger.error(f"Simulation failed: {e}")
            raise
        finally:
            simulation_status.is_running = False
            self._print_summary()

    def _print_summary(self):
        """Print detailed statistics"""
        print("\n" + "="*50)
        print("SIMULATION SUMMARY")
        print("="*50)
        print(f"Total Signals: {simulation_status.stats['total_signals']}")
        total = simulation_status.stats['total_signals']
        if total > 0:
            print(f"Wins: {simulation_status.stats['wins']} ({simulation_status.stats['wins']/total*100:.2f}%)")
            print(f"Losses: {simulation_status.stats['losses']} ({simulation_status.stats['losses']/total*100:.2f}%)")
            print(f"Timeouts: {simulation_status.stats['timeouts']} ({simulation_status.stats['timeouts']/total*100:.2f}%)")
        print(f"Errors: {simulation_status.stats['errors']}")
        print("="*50)

def run_simulation_task(start_date: str, end_date: str, user: str):
    simulator = HistoricalSimulator()
    asyncio.run(simulator.simulate(start_date, end_date))
