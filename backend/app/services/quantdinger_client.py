"""QuantDinger MCP Client for ApexTrade."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class QuantDingerStrategy:
    """QuantDinger strategy representation."""
    id: str
    name: str
    description: str
    code: str
    parameters: Dict[str, Any]
    performance: Dict[str, float]
    created_at: datetime
    updated_at: datetime


@dataclass
class BacktestResult:
    """QuantDinger backtest result."""
    strategy_id: str
    symbol: str
    start_date: datetime
    end_date: datetime
    initial_capital: float
    final_capital: float
    total_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: List[Dict]
    equity_curve: List[Dict]


class QuantDingerMCPClient:
    """Client for QuantDinger MCP server."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=60.0)
        self.connected = False

    async def connect(self) -> bool:
        """Connect to QuantDinger MCP server."""
        try:
            response = await self.client.get(f"{self.base_url}/health")
            if response.status_code == 200:
                self.connected = True
                logger.info("Connected to QuantDinger MCP server")
                return True
        except Exception as e:
            logger.warning(f"QuantDinger MCP server not available: {e}")
        return False

    async def disconnect(self):
        """Disconnect from MCP server."""
        await self.client.aclose()
        self.connected = False

    async def call_tool(self, tool_name: str, arguments: Dict) -> Any:
        """Call a QuantDinger MCP tool."""
        if not self.connected:
            await self.connect()
            if not self.connected:
                raise RuntimeError("QuantDinger MCP server not available")

        try:
            response = await self.client.post(
                f"{self.base_url}/tools/call",
                json={"name": tool_name, "arguments": arguments},
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"MCP tool call failed: {e}")
            raise

    # Strategy Management
    async def create_strategy(
        self,
        name: str,
        description: str,
        code: str,
        parameters: Dict[str, Any],
    ) -> QuantDingerStrategy:
        """Create a new strategy."""
        result = await self.call_tool("create_strategy", {
            "name": name,
            "description": description,
            "code": code,
            "parameters": parameters,
        })
        return QuantDingerStrategy(**result)

    async def get_strategy(self, strategy_id: str) -> QuantDingerStrategy:
        """Get strategy by ID."""
        result = await self.call_tool("get_strategy", {"strategy_id": strategy_id})
        return QuantDingerStrategy(**result)

    async def list_strategies(self) -> List[QuantDingerStrategy]:
        """List all strategies."""
        result = await self.call_tool("list_strategies", {})
        return [QuantDingerStrategy(**s) for s in result]

    async def update_strategy(
        self,
        strategy_id: str,
        code: Optional[str] = None,
        parameters: Optional[Dict] = None,
    ) -> QuantDingerStrategy:
        """Update strategy."""
        args = {"strategy_id": strategy_id}
        if code:
            args["code"] = code
        if parameters:
            args["parameters"] = parameters
        result = await self.call_tool("update_strategy", args)
        return QuantDingerStrategy(**result)

    async def delete_strategy(self, strategy_id: str) -> bool:
        """Delete strategy."""
        await self.call_tool("delete_strategy", {"strategy_id": strategy_id})
        return True

    # Backtesting
    async def run_backtest(
        self,
        strategy_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000,
        timeframe: str = "15m",
    ) -> BacktestResult:
        """Run backtest on QuantDinger."""
        result = await self.call_tool("run_backtest", {
            "strategy_id": strategy_id,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "initial_capital": initial_capital,
            "timeframe": timeframe,
        })
        return BacktestResult(**result)

    async def get_backtest_result(self, backtest_id: str) -> BacktestResult:
        """Get backtest result."""
        result = await self.call_tool("get_backtest", {"backtest_id": backtest_id})
        return BacktestResult(**result)

    # Watchlist Management
    async def create_watchlist(self, name: str, symbols: List[str]) -> Dict:
        """Create watchlist."""
        return await self.call_tool("create_watchlist", {"name": name, "symbols": symbols})

    async def get_watchlist(self, watchlist_id: str) -> Dict:
        """Get watchlist."""
        return await self.call_tool("get_watchlist", {"watchlist_id": watchlist_id})

    async def list_watchlists(self) -> List[Dict]:
        """List watchlists."""
        return await self.call_tool("list_watchlists", {})

    async def update_watchlist(self, watchlist_id: str, symbols: List[str]) -> Dict:
        """Update watchlist."""
        return await self.call_tool("update_watchlist", {"watchlist_id": watchlist_id, "symbols": symbols})

    # Live Trading
    async def start_live_trading(self, strategy_id: str, config: Dict) -> Dict:
        """Start live trading."""
        return await self.call_tool("start_live", {"strategy_id": strategy_id, "config": config})

    async def stop_live_trading(self, session_id: str) -> bool:
        """Stop live trading."""
        await self.call_tool("stop_live", {"session_id": session_id})
        return True

    async def get_live_status(self, session_id: str) -> Dict:
        """Get live trading status."""
        return await self.call_tool("get_live_status", {"session_id": session_id})


# Synchronous wrapper for non-async contexts
class QuantDingerClient:
    """Synchronous QuantDinger client."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.async_client = QuantDingerMCPClient(base_url)

    def _run_async(self, coro):
        """Run async coroutine synchronously."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)

    def connect(self) -> bool:
        return self._run_async(self.async_client.connect())

    def create_strategy(self, name: str, description: str, code: str, parameters: Dict) -> QuantDingerStrategy:
        return self._run_async(self.async_client.create_strategy(name, description, code, parameters))

    def get_strategy(self, strategy_id: str) -> QuantDingerStrategy:
        return self._run_async(self.async_client.get_strategy(strategy_id))

    def list_strategies(self) -> List[QuantDingerStrategy]:
        return self._run_async(self.async_client.list_strategies())

    def run_backtest(
        self,
        strategy_id: str,
        symbol: str,
        start_date: str,
        end_date: str,
        initial_capital: float = 100000,
        timeframe: str = "15m",
    ) -> BacktestResult:
        return self._run_async(self.async_client.run_backtest(
            strategy_id, symbol, start_date, end_date, initial_capital, timeframe
        ))

    def create_watchlist(self, name: str, symbols: List[str]) -> Dict:
        return self._run_async(self.async_client.create_watchlist(name, symbols))

    def list_watchlists(self) -> List[Dict]:
        return self._run_async(self.async_client.list_watchlists())


# Global client instance
_quantdinger_client = None


def get_quantdinger_client() -> QuantDingerClient:
    """Get global QuantDinger client instance."""
    global _quantdinger_client
    if _quantdinger_client is None:
        _quantdinger_client = QuantDingerClient()
    return _quantdinger_client


# Example ApexTrade Strategies for QuantDinger
QUANTDINGER_STRATEGIES = {
    "apextrade_orbreakout": {
        "name": "ApexTrade Opening Range Breakout",
        "description": "Trades breakouts from the opening range using volume confirmation",
        "code": """
class ORBreakoutStrategy:
    def __init__(self, params):
        self.or_minutes = params.get('or_minutes', 15)
        self.volume_threshold = params.get('volume_threshold', 1.5)
        self.risk_per_trade = params.get('risk_per_trade', 0.02)
        
    def initialize(self, data):
        self.or_high = None
        self.or_low = None
        self.or_volume = None
        self.or_established = False
        
    def on_bar(self, bar):
        # Establish opening range
        if not self.or_established:
            if bar.timestamp.hour == 9 and bar.timestamp.minute < self.or_minutes:
                if self.or_high is None or bar.high > self.or_high:
                    self.or_high = bar.high
                if self.or_low is None or bar.low < self.or_low:
                    self.or_low = bar.low
                if self.or_volume is None or bar.volume > self.or_volume:
                    self.or_volume = bar.volume
            elif bar.timestamp.hour == 9 and bar.timestamp.minute >= self.or_minutes:
                self.or_established = True
                return None
                
        # Check breakout with volume confirmation
        if self.or_established and self.or_high and self.or_low:
            if bar.close > self.or_high and bar.volume > self.or_volume * self.volume_threshold:
                return {
                    'action': 'BUY',
                    'price': bar.close,
                    'stop': self.or_low,
                    'target': bar.close + 2 * (bar.close - self.or_low),
                    'size': self.calculate_size(bar.close, self.or_low)
                }
            elif bar.close < self.or_low and bar.volume > self.or_volume * self.volume_threshold:
                return {
                    'action': 'SELL',
                    'price': bar.close,
                    'stop': self.or_high,
                    'target': bar.close - 2 * (self.or_high - bar.close),
                    'size': self.calculate_size(self.or_high, bar.close)
                }
        return None
        
    def calculate_size(self, entry, stop):
        risk_amount = self.capital * self.risk_per_trade
        risk_per_share = abs(entry - stop)
        return int(risk_amount / risk_per_share) if risk_per_share > 0 else 0
""",
        "parameters": {
            "or_minutes": {"type": "int", "default": 15, "min": 5, "max": 60},
            "volume_threshold": {"type": "float", "default": 1.5, "min": 1.0, "max": 5.0},
            "risk_per_trade": {"type": "float", "default": 0.02, "min": 0.005, "max": 0.05},
        },
    },
    "apextrade_vwap_reversion": {
        "name": "ApexTrade VWAP Reversion",
        "description": "Trades mean reversion to VWAP with standard deviation bands",
        "code": """
class VWAPReversionStrategy:
    def __init__(self, params):
        self.vwap_period = params.get('vwap_period', 20)
        self.entry_std = params.get('entry_std', 2.0)
        self.exit_std = params.get('exit_std', 0.5)
        self.risk_per_trade = params.get('risk_per_trade', 0.02)
        
    def initialize(self, data):
        self.vwap = None
        self.upper_band = None
        self.lower_band = None
        
    def on_bar(self, bar):
        # Update VWAP and bands
        # Simplified - would use proper rolling calculation
        pass
""",
        "parameters": {
            "vwap_period": {"type": "int", "default": 20, "min": 10, "max": 50},
            "entry_std": {"type": "float", "default": 2.0, "min": 1.0, "max": 3.0},
            "exit_std": {"type": "float", "default": 0.5, "min": 0.1, "max": 1.5},
            "risk_per_trade": {"type": "float", "default": 0.02, "min": 0.005, "max": 0.05},
        },
    },
}


async def sync_strategies_to_quantdinger():
    """Sync ApexTrade strategies to QuantDinger."""
    client = QuantDingerMCPClient()
    if not await client.connect():
        logger.warning("QuantDinger not available for sync")
        return

    for strategy_id, config in QUANTDINGER_STRATEGIES.items():
        try:
            existing = await client.get_strategy(strategy_id)
            if existing:
                await client.update_strategy(strategy_id, code=config["code"], parameters=config["parameters"])
            else:
                await client.create_strategy(
                    name=config["name"],
                    description=config["description"],
                    code=config["code"],
                    parameters=config["parameters"],
                )
            logger.info(f"Synced strategy: {strategy_id}")
        except Exception as e:
            logger.error(f"Failed to sync {strategy_id}: {e}")

    await client.disconnect()


def get_quantdinger_strategies() -> Dict:
    """Get ApexTrade strategies for QuantDinger."""
    return QUANTDINGER_STRATEGIES