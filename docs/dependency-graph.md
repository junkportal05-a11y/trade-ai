# ApexTrade V3 - Dependency Graph

## Dependency Graph
*(Abstracted view of file interdependencies based on import statements)*
```text
main.py
 ├─ db.py
 ├─ signals.py
 │   ├─ data_mining.py
 │   ├─ candlestick_patterns.py
 │   ├─ angelone_feed.py
 │   └─ numba.py
 ├─ auth_helpers.py
 ├─ trading_agent.py
 │   ├─ signals.py
 │   └─ db.py
 ├─ backtest_engine.py
 │   └─ signals.py
 ├─ backtest_routes.py
 │   ├─ db.py
 │   ├─ backtest_engine.py
 │   └─ auth_helpers.py
 ├─ news_feed.py
 ├─ capital_allocator.py
 └─ data_validator.py
     └─ db.py
```

## Critical Files
- **`backend/signals.py`**: The central brain of the technical analysis engine. Nearly all other systems depend on its output.
- **`backend/db.py`**: The sole interface to the SQLite persistence layer. Every state change flows through this module.

## High Impact Files
- **`backend/main.py`**: The API gateway. Modifying routes here impacts the entire frontend immediately.
- **`backend/auth_helpers.py`**: Security layer. Modifying this could break session management or lock out the UI.
- **`frontend/src/api.js`**: The central fetch wrapper for the UI. Bugs here break all UI-to-Backend communication.

## Core System Files
- **`backend/trading_agent.py`**: The autonomous executor.
- **`backend/prediction_resolver_worker` (inside `main.py`)**: Responsible for closing out trades when stops/targets are hit.
- **`frontend/src/hooks/useMarketData.js`**: The state engine for the UI that aggregates live prices and historical data.

## Files that should not be modified lightly
- **`backend/trade_quality.py`**: Modifying the scoring thresholds here will drastically alter the win-rate and risk profile of the entire autonomous system.
- **`backend/data_validator.py`**: The failsafe mechanism that locks the UI if data is corrupt. Tweaking tolerances here could hide data feed errors resulting in massive financial losses.
- **`backend/angelone_feed.py`**: Direct interaction with the broker's API. Incorrect modifications can cause rejected orders or API rate-limit bans from AngelOne.
