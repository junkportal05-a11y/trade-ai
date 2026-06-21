# ApexTrade V3 - Architecture

## High-Level Architecture
ApexTrade V3 uses a split monolithic architecture with a decoupled frontend and backend.
- **Frontend**: A React Single Page Application (SPA) built with Vite. It handles data visualization, order book management, and performance monitoring.
- **Backend**: A FastAPI Python application handling data mining, strategy execution, signal scoring, and trade management.

## Component Overview

### 1. Market Data Layer
- **AngelOne Feed (`angelone_feed.py`)**: Primary broker integration for live quotes, historical candle retrieval, and order placement via WebSockets/REST.
- **Data Mining (`data_mining.py`)**: Responsible for batch downloading historical NIFTY50 data and preparing base technical features.
- **News Feed (`news_feed.py`)**: Uses NewsAPI and Gemini to evaluate market sentiment on specific symbols.

### 2. Strategy & Analysis Layer
- **Signals Engine (`signals.py`)**: The core analytical engine. Computes RSI, MACD, ADX, VWAP, Bollinger Bands, and other indicators. Dispatches scanning tasks.
- **Candlestick Patterns (`candlestick_patterns.py`)**: Detects price-action formations (Doji, Engulfing, Pin Bars, etc.) to confirm technical indicators.
- **Trade Quality Engine (`trade_quality.py`)**: Filters output from the signals engine, applying regime alignment (Bullish/Bearish/Panic) and returning a normalized score out of 100.

### 3. Execution & Management Layer
- **Autonomous Agent (`trading_agent.py`)**: The background daemon that actively monitors the market from 9:15 AM to 3:20 PM IST, placing trades automatically if the system confidence allows.
- **Capital Manager (`capital_manager.py` / `capital_allocator.py`)**: Determines position sizing (e.g., risking 1% for Elite signals, 0.25% for Watchlist signals).
- **Governance Worker (`governance_worker.py`)**: A risk-management daemon that checks daily loss percentages and triggers kill switches to halt trading during severe drawdowns.
- **Prediction Resolver (`main.py` -> `prediction_resolver_worker`)**: A background loop evaluating open trades against live market data to lock in stop losses or take profits.

### 4. Backtesting & Simulation Layer
- **Backtest Engine (`backtest_engine.py`)**: Processes historical candles to evaluate the strategy without risking real capital.
- **Historical Simulator (`historical_simulator.py`)**: Simulates past trading conditions to evaluate how the autonomous agent would have behaved under specific market regimes.

### 5. Persistence Layer
- **Database (`db.py`)**: SQLite (`trade_ai.db`) for storing signals, trade predictions, journal entries, and system state (like API tokens).

## System Boundaries & Environments
- **Environment Constraints**: The system is designed to run locally or in specialized cloud containers (like Hugging Face Spaces) that restrict standard root access (requires UID 1000, specific exposed ports).
- **External Dependencies**: Requires active API keys for AngelOne, Google Gemini, and NewsAPI.
