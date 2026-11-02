import pandas as pd
import numpy as np
import logging
from pathlib import Path
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
        from backtest_engine import resolve_candle_pessimistic
        for idx, row in df_forward.iterrows():
            close = row['Close']

            c_dict = {
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "open": float(row.get("Open", row["Close"])),
                "close": float(close)
            }
            direction = "BUY" if is_long else "SELL"
            
            res_status, res_price = resolve_candle_pessimistic(c_dict, entry_price, target, stop_loss, direction)
            
            if res_status == "LOSS":
                return 'LOSS', res_price, idx
            elif res_status == "WIN":
                return 'WIN', res_price, idx
                    
            # Timeout if it's the last tick of the day
            if idx == df_forward.index[-1]:
                return 'TIMEOUT', close, idx

        # If loop finishes without hitting
        return 'TIMEOUT', df_forward.iloc[-1]['Close'], df_forward.index[-1]

    async def simulate(self, start_date: str, end_date: str, atr_multiplier: float = 1.0, rr_target: float = 1.5):
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
                                    capital=self.BASE_CAPITAL * (self.POSITION_SIZE_PERCENT / 100),
                                    atr_multiplier=atr_multiplier,
                                    rr_target=rr_target
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
                                            stop_loss = entry_price - (atr_multiplier * atr)
                                            target = entry_price + (rr_target * atr_multiplier * atr)
                                        else:
                                            stop_loss = entry_price + (atr_multiplier * atr)
                                            target = entry_price - (rr_target * atr_multiplier * atr)
                                            
                                    is_long = signal_type == 'BUY'
                                    
                                    # Hybrid Trading Model - Tier 1 vs Tier 2
                                    target_pct = abs((target - entry_price) / entry_price) * 100 if entry_price else 0.0
                                    
                                    if target_pct > 5.0:
                                        # Tier 2: Swing Trade (Allow up to 10 days hold)
                                        df_forward = df.iloc[i+1 : i+1+(75*10)]
                                    else:
                                        # Tier 1: Intraday Trade (Close EOD)
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
                                        pnl_pct = ((exit_price - entry_price) / entry_price) * 100 if entry_price else 0.0
                                    else:
                                        pnl_pct = ((entry_price - exit_price) / entry_price) * 100 if entry_price else 0.0
                                        
                                    quantity = result.get('quantity', 0)
                                    if quantity > 0:
                                        capital_deployed = quantity * entry_price
                                    else:
                                        # Fallback if CME didn't set it
                                        capital_deployed = self.BASE_CAPITAL * (self.POSITION_SIZE_PERCENT / 100)
                                        
                                    risk_amount = result.get('risk_amount', self.BASE_CAPITAL * (self.RISK_PERCENT / 100))
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
                                            # Persist the entry, then resolve it so exit/pnl
                                            # fields actually land (add_prediction's INSERT
                                            # does not include them).
                                            pred_id = db.add_prediction(trade_record)
                                            db.resolve_prediction(
                                                pred_id,
                                                actual_outcome=trade_record["actual_outcome"],
                                                status=trade_record["status"],
                                                exit_price=trade_record["exit_price"],
                                                holding_time_minutes=trade_record["holding_time_minutes"],
                                                pnl_pct=trade_record["pnl_pct"],
                                                pnl_inr=trade_record["pnl_inr"],
                                                r_multiple=trade_record["r_multiple"],
                                                resolution_reason=trade_record["resolution_reason"],
                                            )
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
        print(f"Errors (Data Corruptions): {simulation_status.stats['errors']}")
        
        # Data Confidence Score Calculation
        # Base 100
        # Penalties: timeouts (-1 point each), errors (-5 points each)
        # Scaled by total signals so it's realistic
        if total > 0:
            penalty = (simulation_status.stats['timeouts'] * 1 + simulation_status.stats['errors'] * 5) / max(total * 0.1, 1)
            dcs = max(0, min(100, 100 - penalty))
            print("="*50)
            print(f"DATA CONFIDENCE SCORE: {dcs:.2f}/100")
            if dcs < 90:
                print("WARNING: Data Confidence < 90. Strategy analytics cannot be trusted.")
        
        print("="*50)

def run_simulation_task(start_date: str, end_date: str, user: str, symbols: list = None):
    simulator = HistoricalSimulator()
    asyncio.run(simulator.simulate(start_date, end_date))

if __name__ == "__main__":
    import sys
    
    start = "2024-11-01"
    end = "2024-12-31"
    
    if "--phase1" in sys.argv:
        print("Running Phase 1 validation on core watchlist...")
    
    run_simulation_task(start, end, "admin")
