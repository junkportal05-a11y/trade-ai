"""Unified data adapter layer for multiple trading engines."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional
import pandas as pd
import numpy as np


@dataclass
class UnifiedBar:
    """Unified bar format compatible with all engines."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str


@dataclass
class UnifiedQuote:
    """Unified quote format."""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    timestamp: datetime


class DataAdapter:
    """Convert between different engine data formats."""

    @staticmethod
    def to_nautilus_bars(df: pd.DataFrame, symbol: str) -> list:
        """Convert DataFrame to Nautilus Trader Bar format."""
        try:
            from nautilus_trader.model.data import Bar, BarType
            from nautilus_trader.model.instruments import Instrument
            from nautilus_trader.model.enums import BarAggregation, PriceType
            from nautilus_trader.core.datetime import dt_to_unix_nanos

            bars = []
            for _, row in df.iterrows():
                bar = Bar(
                    bar_type=BarType(
                        instrument_id=Instrument.from_str(symbol),
                        aggregation=BarAggregation.MINUTE,
                        price_type=PriceType.LAST,
                    ),
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    ts_event=dt_to_unix_nanos(row['timestamp']),
                    ts_init=dt_to_unix_nanos(row['timestamp']),
                )
                bars.append(bar)
            return bars
        except ImportError:
            # Return unified format if Nautilus not available
            return [
                UnifiedBar(
                    timestamp=row['timestamp'],
                    open=row['open'],
                    high=row['high'],
                    low=row['low'],
                    close=row['close'],
                    volume=row['volume'],
                    symbol=symbol
                )
                for _, row in df.iterrows()
            ]

    @staticmethod
    def to_lean_bars(df: pd.DataFrame) -> list:
        """Convert DataFrame to Lean TradeBar format (dict for Python)."""
        bars = []
        for _, row in df.iterrows():
            bars.append({
                'time': row['timestamp'],
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
            })
        return bars

    @staticmethod
    def to_timeseries_input(df: pd.DataFrame, lookback: int = 512) -> np.ndarray:
        """Convert to format for TimesFM/Kronos forecasting."""
        # Normalize prices
        close_prices = df['close'].values[-lookback:]
        if len(close_prices) < lookback:
            # Pad with first value
            pad = np.full(lookback - len(close_prices), close_prices[0])
            close_prices = np.concatenate([pad, close_prices])

        # Return log returns for stationarity
        log_returns = np.diff(np.log(close_prices))
        return log_returns.reshape(1, -1)

    @staticmethod
    def from_angelone_response(data: dict) -> pd.DataFrame:
        """Convert AngelOne API response to standard DataFrame."""
        if 'data' not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data['data'])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.rename(columns={
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'volume': 'volume'
        })
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].sort_values('timestamp')

    @staticmethod
    def from_yfinance(df: pd.DataFrame) -> pd.DataFrame:
        """Convert yfinance DataFrame to standard format."""
        df = df.reset_index()
        df = df.rename(columns={
            'Datetime': 'timestamp',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        return df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]


class EngineRegistry:
    """Registry of available engines and their capabilities."""

    ENGINES = {
        'nautilus': {
            'name': 'Nautilus Trader',
            'backtest': True,
            'live': True,
            'indicators': True,
            'risk': True,
            'multi_asset': True,
        },
        'lean': {
            'name': 'QuantConnect Lean',
            'backtest': True,
            'live': True,
            'indicators': True,
            'risk': False,
            'multi_asset': True,
        },
        'timesfm': {
            'name': 'Google TimesFM',
            'forecast': True,
            'backtest': False,
            'quantile': True,
            'covariates': True,
        },
        'kronos': {
            'name': 'Kronos',
            'forecast': True,
            'backtest': False,
            'finetune': True,
        },
        'prophet': {
            'name': 'Facebook Prophet',
            'forecast': True,
            'backtest': False,
            'seasonality': True,
        },
    }

    @classmethod
    def get_available(cls) -> list:
        """Get list of available engines."""
        available = []
        for key, info in cls.ENGINES.items():
            try:
                if key == 'nautilus':
                    import nautilus_trader
                elif key == 'timesfm':
                    import timesfm
                elif key == 'kronos':
                    import torch  # Kronos uses PyTorch
                elif key == 'prophet':
                    import prophet
                available.append(key)
            except ImportError:
                pass
        return available


# Convenience functions
def convert_bars(df: pd.DataFrame, target: str, symbol: str = "UNKNOWN") -> Any:
    """Convert DataFrame to target engine format."""
    adapter = DataAdapter()
    if target == 'nautilus':
        return adapter.to_nautilus_bars(df, symbol)
    elif target == 'lean':
        return adapter.to_lean_bars(df)
    elif target == 'timeseries':
        return adapter.to_timeseries_input(df)
    else:
        raise ValueError(f"Unknown target: {target}")


def get_best_engine(task: str) -> str:
    """Get best available engine for a task."""
    available = EngineRegistry.get_available()

    if task == 'backtest':
        for engine in ['nautilus', 'lean']:
            if engine in available:
                return engine
    elif task == 'forecast':
        for engine in ['timesfm', 'kronos', 'prophet']:
            if engine in available:
                return engine
    elif task == 'live':
        if 'nautilus' in available:
            return 'nautilus'

    return available[0] if available else 'none'