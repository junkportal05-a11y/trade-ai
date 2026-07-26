# ApexTrade Quant Server - System Architecture

ApexTrade is an end-to-end quantitative trading infrastructure for real-time market data streaming, technical signal generation, algorithmic capital allocation, automated trade execution, and performance tracking.

---

## 1. High-Level System Architecture

ApexTrade follows a modular split-service architecture separating data visualization and user interaction from heavy quantitative computation and broker background execution daemons.

```mermaid
graph TD
    subgraph Client ["Client Layer (React + Vite SPA)"]
        UI["ApexCharts Terminal & UI"]
        Journal["Trade Journal Panel"]
        ScannerUI["Scanner & Signals Panel"]
        SimUI["Backtest & Simulator"]
    end

    subgraph Proxy ["Edge & Routing Layer"]
        Vercel["Vercel SPA Proxy"]
    end

    subgraph Backend ["FastAPI Quantitative Engine"]
        API["FastAPI REST & WebSockets (/api/v1)"]
        AuthModule["JWT Auth & Rate Limiter"]
        
        subgraph Signals ["Quant Signal Engine"]
            Indicators["Vectorized Indicators (RSI, MACD, VWAP, OBV)"]
            Patterns["Candlestick Pattern Analyzer"]
            QualityEngine["Trade Quality Engine (0-100 Score)"]
        end

        subgraph Execution ["Execution & Risk Daemons"]
            AgentDaemon["Autonomous Trading Agent"]
            CapitalAlloc["Algorithmic Capital Allocator"]
            Governance["Governance Worker (Drawdown Kill-Switch)"]
            Resolver["Prediction Resolver Worker"]
        end

        subgraph Backtester ["Simulation Engine"]
            BacktestEngine["Vectorized Backtester"]
            HistoricalSim["Historical Market Simulator"]
        end
    end

    subgraph External ["External Data & Broker Services"]
        AngelAPI["AngelOne SmartAPI (REST & WS)"]
        NewsFeed["News Aggregator & Gemini AI"]
        LocalLLM["Local Ollama / LiteLLM Pipeline"]
    end

    subgraph Persistence ["Persistence Layer"]
        SQLite[("SQLite / Supabase Postgres DB")]
    end

    UI -->|HTTPS / API Requests| Vercel
    Vercel -->|Proxy Rewrites| API
    UI <-->|WSS Live Tickers| API
    
    API --> AuthModule
    API --> Signals
    API --> Backtester
    
    AgentDaemon --> QualityEngine
    AgentDaemon --> CapitalAlloc
    AgentDaemon --> Governance
    AgentDaemon --> AngelAPI
    
    Resolver --> AngelAPI
    Resolver --> SQLite
    
    Signals --> NewsFeed
    NewsFeed --> LocalLLM
    
    API --> SQLite
    CapitalAlloc --> SQLite
```

---

## 2. Bot Execution Pipeline

The automated trading loop continuously scans instruments, scores technical setups, sizes risk, and monitors active trade exits.

```mermaid
flowchart TD
    Start([Market Open 09:15 AM IST]) --> ScanTrigger{Scheduled Scan Triggered}
    
    ScanTrigger -->|Fetch Candles| FetchData[AngelOne / YFinance Data Feed]
    FetchData --> CalcIndicators[Vectorized NumPy Technical Calculation]
    
    CalcIndicators --> IndicatorCheck{Technical Confluence Filter}
    
    IndicatorCheck -->|Failed| Skip[Skip Symbol]
    IndicatorCheck -->|Passed| VWAPCheck{VWAP Veto Check}
    
    VWAPCheck -->|Long & Below VWAP / Short & Above VWAP| Vetoed[Signal Vetoed]
    VWAPCheck -->|Aligned| ScoreQuality[Trade Quality Engine Scoring]
    
    ScoreQuality --> QualityFilter{Quality Score >= 70?}
    
    QualityFilter -->|No| Watchlist[Add to Watchlist Only]
    QualityFilter -->|Yes| AllocRisk[Capital Allocator Sizing]
    
    AllocRisk --> CheckGovernance{Governance Drawdown Limit Exceeded?}
    
    CheckGovernance -->|Yes| Halt[Kill-Switch Activated: Halt Execution]
    CheckGovernance -->|No| PlaceOrder[Execute Order via Broker API]
    
    PlaceOrder --> DBLog[(Log Trade & Initial SL/TP to DB)]
    
    DBLog --> ResolutionLoop[Prediction Resolver Worker Loop]
    
    ResolutionLoop --> MonitorPrice{Price Reached SL or TP?}
    
    MonitorPrice -->|Target Hit| ExitTarget[Close Position: Profit Locked]
    MonitorPrice -->|Stop Loss Hit| ExitSL[Close Position: Risk Controlled]
    MonitorPrice -->|Open| ResolutionLoop
```

---

## 3. Real-Time Data Streaming & WebSockets

Live market quotes flow from AngelOne SmartAPI WebSockets through the internal normalizer into the client dashboard.

```mermaid
sequenceDiagram
    autonumber
    actor User as React Client
    participant API as FastAPI Backend
    participant WS as WebSocket Hub
    participant SmartAPI as AngelOne WebSocket
    participant DB as SQLite DB

    User->>API: POST /api/angelone/login (Credentials)
    API->>SmartAPI: Authenticate & Generate Session Token
    SmartAPI-->>API: Auth Success + Feed Token
    API->>DB: Persist Encrypted Session
    API-->>User: Return Auth Token

    User->>WS: Connect wss://.../ws/market (Token)
    WS-->>User: Connection Established

    loop Ticker Feed (200ms)
        SmartAPI-->>WS: Binary Ticker Packet (LTP, Volume, Depth)
        WS->>WS: Normalize & Calculate Instant VWAP/RSI
        WS-->>User: Push JSON Ticker Update
    end
```

---

## 4. Component Deep Dive

### 4.1 Market Data Layer
- **AngelOne SmartAPI Feed (`angelone_feed.py`)**: Broker REST & WebSocket client for fetching live market quotes, depth, and historical OHLCV data.
- **Data Mining Engine (`data_mining.py`)**: Fetches historical candlestick batches across NIFTY50 symbols and calculates base technical arrays.
- **News Sentiment Analyzer (`news_feed.py`)**: Aggregates market headlines and uses Google Gemini / local LiteLLM models to return sentiment confidence scores.

### 4.2 Quant Strategy & Signal Scoring
- **Signal Engine (`signals.py`)**: Fast NumPy-vectorized indicators:
  - **RSI (14)**: Momentum oscillator with overbought/oversold boundaries.
  - **MACD (12, 26, 9)**: Moving average convergence divergence histogram.
  - **VWAP**: Volume-Weighted Average Price benchmark.
  - **OBV**: On-Balance Volume accumulation line.
- **Candlestick Pattern Recognizer (`candlestick_patterns.py`)**: Vectorized detection of Doji, Hammer, Shooting Star, Bullish Engulfing, and Bearish Engulfing patterns.
- **Trade Quality Engine (`trade_quality.py`)**: Synthesizes indicator confluence, market regime, sentiment score, and candlestick patterns into a normalized quality score (0–100).

### 4.3 Execution & Risk Governance
- **Autonomous Agent (`trading_agent.py`)**: Background loop running during NSE market hours (09:15 to 15:20 IST) for automated scanning and order placement.
- **Capital Allocator (`capital_manager.py`)**: Calculates dynamic position sizing based on risk tiers:
  - **Elite Setup (Score 85–100)**: Allocates up to 1.0% account equity risk.
  - **Standard Setup (Score 70–84)**: Allocates 0.5% account equity risk.
  - **Low Setup (Score < 70)**: Flagged for manual review only.
- **Governance Worker (`governance_worker.py`)**: Enforces risk boundaries. If daily max drawdown exceeds the safety threshold (e.g., 3%), it triggers a global kill-switch halting all automated order placement.
- **Prediction Resolver (`main.py` -> `prediction_resolver_worker`)**: High-frequency loop monitoring open positions against real-time high/low candles to record stop loss and take profit resolutions accurately.

---

## 5. Technology Stack & Environment

| Layer | Technology |
|---|---|
| **Frontend UI** | React 19, Vite 8, Lightweight-Charts / ApexCharts, Vanilla CSS |
| **Backend Framework** | FastAPI 0.111, Uvicorn, Python 3.10+ |
| **Quant Computing** | NumPy, Pandas, PyArrow |
| **AI & LLM Pipeline** | Google GenAI SDK, Local Ollama / LiteLLM Offline Server |
| **Database** | SQLite ORM (`trade_ai.db`), Supabase Postgres |
| **Broker Integration** | AngelOne SmartAPI, yfinance fallback |
