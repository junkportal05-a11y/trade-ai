"""Nautilus Trader Engine Wrapper for ApexTrade."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from decimal import Decimal

import pandas as pd
import numpy as np

from app.core.config import settings
from app.core.data_adapter import convert_bars, get_best_engine


@dataclass
class BacktestResult:
    """Standardized backtest result."""
    engine: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    total_return_pct: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    equity_curve: List[Dict]
    trades: List[Dict]
    metadata: Dict


@dataclass
class LiveSignal:
    """Live trading signal."""
    symbol: str
    signal_type: str  # ENTRY, EXIT, MODIFY
    side: str  # BUY, SELL
    quantity: float
    price: Optional[float]
    stop_loss: Optional[float]
    take_profit: Optional[float]
    confidence: float
    strategy_name: str
    timestamp: datetime
    metadata: Dict


class NautilusEngine:
    """Wrapper for Nautilus Trader engine."""

    def __init__(self):
        self.engine = None
        self.config = None
        self.is_running = False
        self.strategies = {}
        self.callbacks = []

    def initialize(self, config: Optional[Dict] = None) -> bool:
        """Initialize Nautilus Trader engine."""
        try:
            from nautilus_trader.config import TradingNodeConfig, LoggingConfig
            from nautilus_trader.live.node import TradingNode
            from nautilus_trader.config import ImportableStrategyConfig

            self.config = config or {
                'trading_node': {
                    'instance_id': 'apextrade-node',
                    'data_clients': {},
                    'exec_clients': {},
                    'strategies': [],
                }
            }

            # Create trading node config
            node_config = TradingNodeConfig(**self.config['trading_node'])
            self.engine = TradingNode(node_config)
            return True
        except Exception as e:
            print(f"Failed to initialize Nautilus: {e}")
            return False

    def add_strategy(self, strategy_class, config: Dict, strategy_id: str) -> bool:
        """Add a strategy to the engine."""
        try:
            from nautilus_trader.config import ImportableStrategyConfig

            strategy_config = ImportableStrategyConfig(
                strategy_path=strategy_class.__module__,
                class_name=strategy_class.__name__,
                config=config,
                strategy_id=strategy_id,
            )
            self.strategies[strategy_id] = {
                'class': strategy_class,
                'config': strategy_config,
                'config_dict': config,
            }
            return True
        except Exception as e:
            print(f"Failed to add strategy: {e}")
            return False

    def add_angelone_adapter(self, api_key: str, client_code: str, pin: str, totp: str) -> bool:
        """Add AngelOne broker adapter."""
        try:
            from nautilus_trader.config import ExecClientConfig
            from nautilus_trader.adapters.angelone import AngelOneExecClient

            exec_config = ExecClientConfig(
                client_id="ANGELONE",
                base_url="https://apiconnect.angelone.in",
                api_key=api_key,
                client_code=client_code,
                pin=pin,
                totp_secret=totp,
            )
            # Would need actual adapter implementation
            return True
        except Exception as e:
            print(f"AngelOne adapter not available: {e}")
            return False

    async def run_backtest(
        self,
        symbol: str,
        bars_df: pd.DataFrame,
        strategy_class,
        strategy_config: Dict,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float = 100000,
    ) -> BacktestResult:
        """Run backtest using Nautilus Trader."""
        try:
            from nautilus_trader.backtest.engine import BacktestEngine, BacktestEngineConfig
            from nautilus_trader.config import ImportableStrategyConfig
            from nautilus_trader.model.data import BarType
            from nautilus_trader.model.enums import BarAggregation, PriceType
            from nautilus_trader.model.instruments import Instrument
            from nautilus_trader.model.currencies import INR
            from nautilus_trader.core.datetime import dt_to_unix_nanos

            # Convert data
            bars = convert_bars(bars_df, 'nautilus', symbol)

            # Create instrument
            instrument = Instrument.from_str(symbol)

            # Bar type
            bar_type = BarType(
                instrument_id=instrument.id,
                aggregation=BarAggregation.MINUTE,
                price_type=PriceType.LAST,
            )

            # Strategy config
            strategy_config_obj = ImportableStrategyConfig(
                strategy_path=strategy_class.__module__,
                class_name=strategy_class.__name__,
                config=strategy_config,
                strategy_id=f"{strategy_class.__name__}_{symbol}",
            )

            # Backtest config
            bt_config = BacktestEngineConfig(
                start_time=start_date,
                end_time=end_date,
                initial_cash=Decimal(str(initial_capital)),
                currency=INR,
                bar_type=bar_type,
            )

            # Create engine
            engine = BacktestEngine(config=bt_config)

            # Add data
            engine.add_data(bars)

            # Add strategy
            engine.add_strategy(strategy_config_obj)

            # Run backtest
            engine.run()

            # Get results
            result = engine.get_result()

            # Convert to standard format
            return self._convert_result(result, symbol, start_date, end_date, initial_capital)

        except Exception as e:
            print(f"Backtest failed: {e}")
            return BacktestResult(
                engine="nautilus",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                final_capital=initial_capital,
                total_return=0,
                total_return_pct=0,
                max_drawdown=0,
                max_drawdown_pct=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                win_rate=0,
                profit_factor=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_win=0,
                avg_loss=0,
                equity_curve=[],
                trades=[],
                metadata={'error': str(e)},
            )

    def _convert_result(self, result, symbol: str, start_date: datetime, end_date: datetime, initial_capital: float) -> BacktestResult:
        """Convert Nautilus result to standard format."""
        try:
            stats = result.get_statistics()
            trades = result.get_trades()
            equity = result.get_equity_curve()

            equity_curve = [
                {'timestamp': ts, 'equity': float(eq)}
                for ts, eq in equity.items()
            ]

            trades_list = []
            for trade in trades:
                trades_list.append({
                    'symbol': trade.instrument_id.symbol,
                    'side': trade.side.name,
                    'entry_time': trade.entry_time,
                    'exit_time': trade.exit_time,
                    'entry_price': float(trade.entry_price),
                    'exit_price': float(trade.exit_price),
                    'quantity': float(trade.quantity),
                    'pnl': float(trade.realized_pnl),
                    'return_pct': float(trade.realized_pnl / initial_capital * 100),
                })

            return BacktestResult(
                engine="nautilus",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                final_capital=float(stats.get('final_balance', initial_capital)),
                total_return=float(stats.get('total_return', 0)),
                total_return_pct=float(stats.get('total_return_pct', 0)),
                max_drawdown=float(stats.get('max_drawdown', 0)),
                max_drawdown_pct=float(stats.get('max_drawdown_pct', 0)),
                sharpe_ratio=float(stats.get('sharpe_ratio', 0)),
                sortino_ratio=float(stats.get('sortino_ratio', 0)),
                win_rate=float(stats.get('win_rate', 0)),
                profit_factor=float(stats.get('profit_factor', 0)),
                total_trades=len(trades_list),
                winning_trades=len([t for t in trades_list if t['pnl'] > 0]),
                losing_trades=len([t for t in trades_list if t['pnl'] <= 0]),
                avg_win=np.mean([t['pnl'] for t in trades_list if t['pnl'] > 0]) if any(t['pnl'] > 0 for t in trades_list) else 0,
                avg_loss=np.mean([t['pnl'] for t in trades_list if t['pnl'] <= 0]) if any(t['pnl'] <= 0 for t in trades_list) else 0,
                equity_curve=equity_curve,
                trades=trades_list,
                metadata=dict(stats),
            )
        except Exception as e:
            return BacktestResult(
                engine="nautilus",
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                final_capital=initial_capital,
                total_return=0,
                total_return_pct=0,
                max_drawdown=0,
                max_drawdown_pct=0,
                sharpe_ratio=0,
                sortino_ratio=0,
                win_rate=0,
                profit_factor=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                avg_win=0,
                avg_loss=0,
                equity_curve=[],
                trades=[],
                metadata={'error': str(e)},
            )

    def start_live(self) -> bool:
        """Start live trading."""
        if not self.engine:
            return False
        try:
            self.engine.start()
            self.is_running = True
            return True
        except Exception as e:
            print(f"Failed to start live: {e}")
            return False

    def stop_live(self) -> bool:
        """Stop live trading."""
        if not self.engine:
            return False
        try:
            self.engine.stop()
            self.is_running = False
            return True
        except Exception as e:
            print(f"Failed to stop live: {e}")
            return False

    def register_signal_callback(self, callback: Callable[[LiveSignal], None]):
        """Register callback for live signals."""
        self.callbacks.append(callback)

    def _emit_signal(self, signal: LiveSignal):
        """Emit signal to all callbacks."""
        for cb in self.callbacks:
            try:
                cb(signal)
            except Exception as e:
                print(f"Callback error: {e}")


# Singleton instance
_nautilus_engine = None


def get_nautilus_engine() -> NautilusEngine:
    """Get singleton Nautilus engine instance."""
    global _nautilus_engine
    if _nautilus_engine is None:
        _nautilus_engine = NautilusEngine()
    return _nautilus_engine


# Strategy Base Class for ApexTrade
class ApexTradeStrategy:
    """Base strategy class for ApexTrade strategies on Nautilus."""

    def __init__(self, config: Dict):
        self.config = config
        self.symbol = config.get('symbol', 'RELIANCE.NS')
        self.timeframe = config.get('timeframe', '15m')
        self.risk_per_trade = config.get('risk_per_trade', 0.02)
        self.max_positions = config.get('max_positions', 3)

    def on_bar(self, bar):
        """Process new bar - override in subclass."""
        pass

    def on_signal(self, signal):
        """Handle signal - override in subclass."""
        pass

    def calculate_position_size(self, entry: float, stop: float, capital: float) -> float:
        """Calculate position size based on risk."""
        risk_amount = capital * self.risk_per_trade
        risk_per_share = abs(entry - stop)
        if risk_per_share > 0:
            return risk_amount / risk_per_share
        return 0


# Example Strategies
class OpeningRangeBreakout(ApexTradeStrategy):
    """Opening Range Breakout Strategy."""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.or_minutes = config.get('or_minutes', 15)
        self.or_high = None
        self.or_low = None
        self.or_established = False

    def on_bar(self, bar):
        # Establish opening range
        if not self.or_established:
            bar_time = bar.ts_event
            if bar_time.hour == 9 and bar_time.minute < self.or_minutes:
                if self.or_high is None or bar.high > self.or_high:
                    self.or_high = bar.high
                if self.or_low is None or bar.low < self.or_low:
                    self.or_low = bar.low
            elif bar_time.hour == 9 and bar_time.minute >= self.or_minutes:
                self.or_established = True

        # Breakout logic
        if self.or_established and self.or_high and self.or_low:
            if bar.close > self.or_high:
                # Long breakout
                return {
                    'type': 'ENTRY',
                    'side': 'BUY',
                    'price': bar.close,
                    'stop': self.or_low,
                    'target': bar.close + 2 * (bar.close - self.or_low),
                }
            elif bar.close < self.or_low:
                # Short breakout
                return {
                    'type': 'ENTRY',
                    'side': 'SELL',
                    'price': bar.close,
                    'stop': self.or_high,
                    'target': bar.close - 2 * (self.or_high - bar.close),
                }
        return None


class VWAPReversion(ApexTradeStrategy):
    """VWAP Mean Reversion Strategy."""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.vwap_period = config.get('vwap_period', 20)
        self.std_dev = config.get('std_dev', 2.0)

    def on_bar(self, bar):
        # This would need VWAP calculation from historical bars
        # Simplified version
        pass


class TrendFollowing(ApexTradeStrategy):
    """Trend Following with EMA Crossover."""

    def __init__(self, config: Dict):
        super().__init__(config)
        self.fast_ema = config.get('fast_ema', 9)
        self.slow_ema = config.get('slow_ema', 21)
        self.ema_fast = None
        self.ema_slow = None

    def on_bar(self, bar):
        if self.ema_fast is None:
            self.ema_fast = bar.close
            self.ema_slow = bar.close
            return None

        # Update EMAs
        k_fast = 2 / (self.fast_ema + 1)
        k_slow = 2 / (self.slow_ema + 1)

        self.ema_fast = bar.close * k_fast + self.ema_fast * (1 - k_fast)
        self.ema_slow = bar.close * k_slow + self.ema_slow * (1 - k_slow)

        # Crossover signals
        if self.ema_fast > self.ema_slow:
            # Bullish
            return {'type': 'ENTRY', 'side': 'BUY', 'price': bar.close}
        elif self.ema_fast < self.ema_slow:
            # Bearish
            return {'type': 'ENTRY', 'side': 'SELL', 'price': bar.close}

        return None


# Strategy Registry
STRATEGY_REGISTRY = {
    'opening_range_breakout': OpeningRangeBreakout,
    'vwap_reversion': VWAPReversion,
    'trend_following': TrendFollowing,
}


def get_strategy(name: str) -> type:
    """Get strategy class by name."""
    return STRATEGY_REGISTRY.get(name)


def list_strategies() -> list:
    """List available strategies."""
    return list(STRATEGY_REGISTRY.keys())