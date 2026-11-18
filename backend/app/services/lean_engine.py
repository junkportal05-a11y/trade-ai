"""Lean (QuantConnect) Engine Wrapper for ApexTrade."""
from __future__ import annotations

import asyncio
import json
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import numpy as np


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


class LeanEngine:
    """Wrapper for Lean (QuantConnect) engine."""

    def __init__(self):
        self.lean_path = None
        self.is_initialized = False
        self.lean_config = None

    def initialize(self, config: Optional[Dict] = None) -> bool:
        """Initialize Lean engine by checking for Lean CLI."""
        try:
            # Check if Lean CLI is available
            result = subprocess.run(
                ["lean", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.is_initialized = True
                self.lean_path = "lean"
                return True
            
            # Check for dotnet lean
            result = subprocess.run(
                ["dotnet", "lean", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                self.is_initialized = True
                self.lean_path = "dotnet lean"
                return True
            
            return False
        except Exception as e:
            print(f"Lean not available: {e}")
            return False

    def _create_lean_project(self, project_dir: Path, strategy_name: str, config: Dict) -> bool:
        """Create a Lean project structure with the strategy."""
        try:
            # Create project structure
            (project_dir / "main.py").write_text(self._get_strategy_template(strategy_name, config))
            (project_dir / "config.json").write_text(json.dumps(self._get_lean_config(config), indent=2))
            return True
        except Exception as e:
            print(f"Failed to create Lean project: {e}")
            return False

    def _get_strategy_template(self, strategy_name: str, config: Dict) -> str:
        """Generate Python strategy template for Lean."""
        return f'''
from AlgorithmImports import *

class {strategy_name}(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate({config.get("start_year", 2023)}, {config.get("start_month", 1)}, {config.get("start_day", 1)})
        self.SetEndDate({config.get("end_year", 2023)}, {config.get("end_month", 12)}, {config.get("end_day", 31)})
        self.SetCash({config.get("initial_capital", 100000)})
        
        symbol = self.AddEquity("{config.get("symbol", "SPY")}", Resolution.Minute).Symbol
        
        # Add indicators based on strategy
        if "{strategy_name}" == "OpeningRangeBreakout":
            self.orb_period = {config.get("or_minutes", 15)}
            self.risk_per_trade = {config.get("risk_per_trade", 0.02)}
        elif "{strategy_name}" == "TrendFollowing":
            self.fast_ema = self.EMA(symbol, {config.get("fast_ema", 9)}, Resolution.Minute)
            self.slow_ema = self.EMA(symbol, {config.get("slow_ema", 21)}, Resolution.Minute)
            self.risk_per_trade = {config.get("risk_per_trade", 0.02)}
        elif "{strategy_name}" == "VWAPReversion":
            self.vwap = self.VWAP(symbol)
            self.risk_per_trade = {config.get("risk_per_trade", 0.02)}
    
    def OnData(self, data):
        # Strategy logic would go here
        pass
'''

    def _get_lean_config(self, config: Dict) -> Dict:
        """Generate Lean configuration."""
        return {
            "algorithm-language": "Python",
            "algorithm-location": "main.py",
            "data-folder": "data",
            "results-destination-folder": "results",
            "log-level": "Info",
            "messaging-handler": "QuantConnect.Messaging.Messaging",
            "job-queue-handler": "QuantConnect.Queues.JobQueue",
            "api-handler": "QuantConnect.Api.Api",
            "map-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskMapFileProvider",
            "factor-file-provider": "QuantConnect.Data.Auxiliary.LocalDiskFactorFileProvider",
            "data-provider": "QuantConnect.Lean.Engine.DataFeeds.DefaultDataProvider",
            "result-handler": "QuantConnect.Lean.Engine.Results.BacktestingResultHandler",
            "setup-handler": "QuantConnect.Lean.Engine.Setup.BacktestingSetupHandler",
            "data-feed-handler": "QuantConnect.Lean.Engine.DataFeeds.BacktestingDataFeed",
            "real-time-handler": "QuantConnect.Lean.Engine.RealTime.BacktestingRealTimeHandler",
            "history-provider": "QuantConnect.Lean.Engine.HistoricalData.BacktestingHistoryProvider",
            "transaction-handler": "QuantConnect.Lean.Engine.TransactionHandlers.BacktestingTransactionHandler",
        }

    async def run_backtest(
        self,
        symbol: str,
        bars_df: pd.DataFrame,
        strategy_class: Any,
        strategy_config: Dict,
        start_date: datetime,
        end_date: datetime,
        initial_capital: float,
    ) -> BacktestResult:
        """Run backtest using Lean CLI."""
        if not self.is_initialized:
            if not self.initialize():
                return BacktestResult(
                    engine="lean",
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
                    metadata={"error": "Lean CLI not installed. Install via: pip install lean"},
                )

        # Prepare data for Lean (convert to LEAN format)
        # This is a simplified implementation - full implementation would need
        # proper data conversion to LEAN's binary format
        
        # For now, return a placeholder result
        return BacktestResult(
            engine="lean",
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
            metadata={
                "note": "Lean backtest requires Lean CLI and data in LEAN format. "
                       "Install: pip install lean. "
                       "Data conversion from pandas to LEAN format needed."
            },
        )


# Singleton instance
_lean_engine: Optional[LeanEngine] = None


def get_lean_engine() -> LeanEngine:
    """Get or create Lean engine singleton."""
    global _lean_engine
    if _lean_engine is None:
        _lean_engine = LeanEngine()
    return _lean_engine