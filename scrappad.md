# ==============================================================================
# OPENCODE TASK DIRECTIVE — READ & EXECUTE FROM THIS SCRATCHPAD
# ApexTrade v6.1.1 — Black, Red & Gold Workstation Redesign
# ==============================================================================

> ### 📢 NEW HISTORICAL DATASET AVAILABLE FOR STRATEGY ENGINE & BACKTESTING
> **7 Years of Real NSE Daily Market Data (2019 – 2026)** has been downloaded and ready to use:
> - **Path**: `historical_data/daily_7y/`
> - **Formats**: `.parquet` (fast) and `.csv`
> - **Instruments**:
>   - **Indices**: `NIFTY_50_INDEX`, `BANK_NIFTY_INDEX` (1,733 bars each)
>   - **Core Equities**: `RELIANCE`, `TCS`, `HDFCBANK`, `ICICIBANK`, `INFY`, `SBIN`, `BHARTIARTL`, `ITC`, `KOTAKBANK`, `LT`, `AXISBANK`, `HINDUNILVR`, `BAJFINANCE`, `MARUTI`, `TATASTEEL`, `SUNPHARMA`, `TITAN`, `NTPC`, `POWERGRID` (1,735 bars each)
> - **Manifest**: `historical_data/daily_7y/_manifest_summary.csv`
> - **Python Usage**:
>   ```python
>   import pandas as pd
>   df = pd.read_parquet(r"historical_data\daily_7y\NIFTY_50_INDEX_7y_daily.parquet")
>   # Columns: Date, Open, High, Low, Close, Adj Close, Volume
>   ```
>
> ---
>
> ### 🛡️ FULL AUTONOMY MANDATE FOR OPENCODE: STRATEGY & ENGINE OVERHAUL
> **You have 100% full authorization to:**
> 1. **Create, Refactor, or Delete Strategies**: Freely add new quantitative strategies, prune underperforming/negative-expectancy strategies, and rewrite existing logic in `backend/strategy_tournament.py`, `backend/signals.py`, `backend/trading_agent.py`, and `backend/historical_simulator.py`.
> 2. **Calibrate on Real 7-Year Data**: Train on 2019–2023, validate on 2024–2026. Target Sharpe Ratio > 1.2, positive profit factor (> 1.5), and max drawdown < 15%.
> 3. **Implement Real Quant Features**: Dynamic ATR volatility stops, NIFTY regime filters (bull/bear/sideways regime switching), volume exhaustion triggers, and execution slippage modeling.
> 4. **Only Requirement**: Keep the test suite passing (`.venv\Scripts\python -m pytest backend/tests`) and preserve paper-only mode safety.

**Locked in.** Zero blue, zero purple, zero green. 

The workstation is now exclusively built on the **Black, Red & Gold** palette:
1. **Pitch Obsidian Black (`#050506` & `#0c0a09`):** Deep, distraction-free canvas and smoked glass panels.
2. **24K Imperial Gold (`#f59e0b`, `#fbbf24`, `#d97706`):** Primary triggers (`START BOT`, `RUN BACKTEST`), active navigation tabs, P&L profit metrics, `#1` Leaderboard crown, and hairline card highlights.
3. **Crimson Blood Red (`#ef4444`, `#dc2626`, `#991b1b`):** Danger triggers (`STOP ALL`), loss telemetry, negative tick indicators, and high-risk strategy badges.

---

## 1. Visual Hierarchy (Black + Red + Gold Only)

```text
+=======================================================================================================================+
| [● GOLD PULSE] NSE TICK STREAM (SIM)   | NIFTY 50 24,180.20 (+0.32% GOLD) | BANKNIFTY 51,240.10 (-0.14% RED) | YESBANK ₹0.00 [SIM] | <- TIER 1
+-----------------------------------------------------------------------------------------------------------------------+
| [AT GOLD] ApexTrade [v6.1.1] [PAPER ONLY RED] | [Home] [Bot Engine* GOLD] [Terminal] [Scanner]... | [ 🔍 Search... ⌘K ] [OW] | <- TIER 2
+-----------------------------------------------------------------------------------------------------------------------+
| CASH: ₹0.00   |   HOLDINGS: ₹0.00   |   TODAY'S REALIZED P&L: +₹0.00 (GOLD PILL)   |   BOT: [ STOPPED (RED PILL) ]        | <- TIER 3
+=======================================================================================================================+

┌─ BOT ENGINE CONTROL MATRIX ──────────────────────────────────────────────────────────────────────────────────────────┐
│ STATUS: [ STOPPED (RED) ]   PAPER RUNTIME (GOLD)            [ ▶ START (24K Gold) ]  [ ⏸ PAUSE ]  [ ⏹ STOP (Crimson) ] │
│ Today's P&L: +₹0.00 (Gold)   |   Signals: 0   |   Stop Limit: ₹2,500.00 (Red)   |   Circuit: [✔ ARMED (Gold)]            │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

┌─ 30-STRATEGY LEADERBOARD ─────────────────────────────────────────────────────────────────────────────────────────────┐
│ [#1 GOLD]  SuperTrend Quant (10, 3.0) [LEADER RED]   Win: 51.2% (Gold)   Sharpe: 0.63   Avg: +800.38 (Gold)   Score: 170.94│
│ [#2]       VWAP Institutional Pullback               Win: 56.4%          Sharpe: 0.61   Avg: +742.10          Score: 164.20│
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Interactive Standalone Preview (`preview.html`)

Save this code into a file named **`preview.html`** in your project folder (`C:\Users\aryan\OneDrive\Desktop\app\projects\trade.ai\preview.html`) and double-click it. It runs locally with the exact Black, Red, and Gold styling:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ApexTrade v6.1.1 — Black, Red & Gold Workstation</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

    :root {
      --bg: #050506;
      --surface: #0c0a09;
      --surface-border: rgba(245, 158, 11, 0.15);
      --surface-card: #0e0c0a;
      
      /* Gold */
      --gold: #f59e0b;
      --gold-light: #fbbf24;
      --gold-glow: rgba(245, 158, 11, 0.25);
      --gold-border: rgba(245, 158, 11, 0.35);

      /* Red */
      --red: #ef4444;
      --red-light: #f87171;
      --red-glow: rgba(239, 68, 68, 0.25);
      --red-border: rgba(239, 68, 68, 0.35);
    }

    body {
      font-family: 'Plus Jakarta Sans', sans-serif;
      background-color: var(--bg);
      color: #f8fafc;
      overflow-x: hidden;
    }

    .font-mono {
      font-family: 'JetBrains Mono', monospace;
      font-variant-numeric: tabular-nums;
    }

    .glass-panel {
      background-color: var(--surface);
      border: 1px solid var(--surface-border);
      box-shadow: 0 16px 36px -12px rgba(0, 0, 0, 0.9);
    }

    .glass-input {
      background: #000000;
      border: 1px solid rgba(245, 158, 11, 0.2);
      color: #ffffff;
      transition: all 0.15s ease;
    }
    .glass-input:focus {
      outline: none;
      border-color: #f59e0b;
      box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.2);
    }

    /* Scrollbars */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #050506; }
    ::-webkit-scrollbar-thumb { background: rgba(245, 158, 11, 0.2); border-radius: 999px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(245, 158, 11, 0.4); }
  </style>
</head>
<body class="min-h-screen flex flex-col antialiased">

  <!-- ================= TIER 1: LIVE SIMULATED TICKER ================= -->
  <div class="h-8 border-b border-white/[0.08] bg-black px-4 lg:px-8 flex items-center justify-between text-xs text-slate-400 overflow-x-auto whitespace-nowrap">
    <div class="flex items-center space-x-5">
      <div class="flex items-center space-x-2">
        <span class="relative flex h-2 w-2">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
        </span>
        <span class="text-[10px] font-bold tracking-wider text-amber-400 uppercase">NSE TICK FEED</span>
        <span class="px-1.5 py-0.2 rounded bg-amber-500/10 border border-amber-500/30 text-[9px] font-semibold text-amber-300 font-mono">SIMULATED</span>
      </div>

      <div class="h-3 w-[1px] bg-white/[0.1]"></div>

      <div class="flex items-center space-x-6 font-mono text-[11px]">
        <span>NIFTY 50: <strong class="text-amber-400 font-medium">24,180.20 (+0.32%)</strong></span>
        <span>BANKNIFTY: <strong class="text-red-400 font-medium">51,240.10 (-0.14%)</strong></span>
        <span class="flex items-center gap-1.5 text-slate-300">
          YESBANK: <strong class="text-white">₹0.00</strong>
          <span class="px-1 py-0.2 rounded bg-white/[0.06] text-[9px] text-slate-400 border border-white/[0.1]">SIM</span>
        </span>
      </div>
    </div>

    <div class="hidden md:flex items-center space-x-4 text-[11px] text-slate-500">
      <span>FEED: <strong class="text-amber-400 font-mono">SYNCHRONIZED</strong></span>
      <span>LATENCY: <strong class="text-slate-300 font-mono">11ms</strong></span>
    </div>
  </div>

  <!-- ================= TIER 2: PRIMARY NAVBAR ================= -->
  <header class="border-b border-white/[0.08] bg-[#070605] px-4 lg:px-8 h-14 flex items-center justify-between">
    <!-- Brand -->
    <div class="flex items-center space-x-3">
      <div class="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 border border-amber-300 flex items-center justify-center text-black font-extrabold text-xs tracking-wider font-mono shadow-[0_0_15px_rgba(245,158,11,0.3)]">
        AT
      </div>
      <div class="flex items-center space-x-2">
        <span class="text-base font-extrabold text-white tracking-tight">ApexTrade</span>
        <span class="px-1.5 py-0.5 rounded bg-white/[0.05] border border-white/[0.1] text-[10px] font-mono text-slate-400 font-medium">
          v6.1.1
        </span>
        <span class="px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/30 text-[10px] font-bold text-red-400">
          PAPER ONLY
        </span>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <nav class="hidden xl:flex items-center space-x-1" id="nav-container">
      <button onclick="switchTab('home')" id="tab-home" class="nav-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-white/[0.04] transition-all flex items-center gap-1.5">
        <i data-lucide="activity" class="w-3.5 h-3.5"></i><span>Home</span>
      </button>
      <button onclick="switchTab('bot')" id="tab-bot" class="nav-btn px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/40 flex items-center gap-1.5 shadow-[0_0_15px_rgba(245,158,11,0.2)]">
        <i data-lucide="cpu" class="w-3.5 h-3.5"></i><span>Bot Engine</span>
      </button>
      <button onclick="switchTab('terminal')" id="tab-terminal" class="nav-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-white/[0.04] transition-all flex items-center gap-1.5">
        <i data-lucide="line-chart" class="w-3.5 h-3.5"></i><span>Terminal</span>
      </button>
      <button onclick="switchTab('scanner')" id="tab-scanner" class="nav-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-white/[0.04] transition-all flex items-center gap-1.5">
        <i data-lucide="layers" class="w-3.5 h-3.5"></i><span>Scanner</span>
      </button>
      <button onclick="switchTab('predictions')" id="tab-predictions" class="nav-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-white/[0.04] transition-all flex items-center gap-1.5">
        <i data-lucide="trending-up" class="w-3.5 h-3.5"></i><span>Predictions</span>
      </button>
      <button onclick="switchTab('analytics')" id="tab-analytics" class="nav-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-white/[0.04] transition-all flex items-center gap-1.5">
        <i data-lucide="pie-chart" class="w-3.5 h-3.5"></i><span>Analytics</span>
      </button>
      <button onclick="switchTab('journal')" id="tab-journal" class="nav-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-white/[0.04] transition-all flex items-center gap-1.5">
        <i data-lucide="book-open" class="w-3.5 h-3.5"></i><span>Journal</span>
      </button>
      <button onclick="switchTab('security')" id="tab-security" class="nav-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-white/[0.04] transition-all flex items-center gap-1.5">
        <i data-lucide="shield-check" class="w-3.5 h-3.5"></i><span>Security</span>
      </button>
    </nav>

    <!-- Search & Profile -->
    <div class="flex items-center space-x-3">
      <div class="relative w-44 md:w-60">
        <i data-lucide="search" class="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-500"></i>
        <input type="text" placeholder="Search instruments..." readonly class="w-full glass-input rounded-lg pl-9 pr-8 py-1.5 text-xs text-slate-200 placeholder-slate-500 cursor-pointer">
        <span class="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] bg-black text-amber-400 px-1.5 py-0.5 rounded border border-amber-500/30 font-mono">⌘K</span>
      </div>

      <div class="w-8 h-8 rounded-lg bg-black border border-amber-500/30 flex items-center justify-center text-xs font-black text-amber-400 font-mono">
        OW
      </div>
    </div>
  </header>

  <!-- ================= TIER 3: PORTFOLIO & STATUS STRIP ================= -->
  <div class="h-11 border-b border-white/[0.08] bg-black px-4 lg:px-8 flex items-center justify-between text-xs overflow-x-auto whitespace-nowrap">
    <div class="flex items-center space-x-6 font-mono text-xs">
      <div class="flex items-center space-x-2">
        <span class="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">CASH:</span>
        <span class="text-white font-medium">₹0.00</span>
      </div>
      <div class="h-3 w-[1px] bg-white/[0.1]"></div>
      <div class="flex items-center space-x-2">
        <span class="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">HOLDINGS:</span>
        <span class="text-white font-medium">₹0.00</span>
      </div>
      <div class="h-3 w-[1px] bg-white/[0.1]"></div>
      <div class="flex items-center space-x-2">
        <span class="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">TODAY'S P&L:</span>
        <span class="text-amber-300 bg-amber-500/10 border border-amber-500/30 px-2.5 py-0.5 rounded-full font-bold">
          +₹0.00 (0.00%)
        </span>
      </div>
    </div>

    <div class="flex items-center space-x-5">
      <div class="flex items-center space-x-2">
        <span class="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">BOT ENGINE:</span>
        <span class="px-2.5 py-0.5 rounded-full bg-red-500/10 border border-red-500/40 text-[10px] font-mono font-bold text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.2)]">
          STOPPED
        </span>
      </div>
      <div class="hidden sm:flex items-center space-x-1.5 text-slate-400 text-xs">
        <span class="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_#f59e0b]"></span>
        <span class="font-medium text-slate-300">NSE: OPEN</span>
      </div>
    </div>
  </div>

  <!-- ================= WORKSPACE BODY ================= -->
  <main class="flex-1 w-full max-w-[1800px] mx-auto p-4 lg:p-8 space-y-6">

    <!-- BOT ENGINE HERO -->
    <div class="glass-panel rounded-2xl p-6">
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
        <div class="space-y-1.5">
          <div class="flex items-center space-x-3">
            <h2 class="text-lg font-extrabold text-white tracking-tight">Bot Engine Control Matrix</h2>
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-red-500/15 border border-red-500/40 text-red-400">
              STATUS: STOPPED
            </span>
            <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 border border-amber-500/30 text-amber-300">
              PAPER RUNTIME
            </span>
          </div>
          <p class="text-xs text-slate-400 max-w-xl">
            Autonomous signal dispatch pipeline. Simulates intraday orders on simulated NSE ticks with zero live market exposure.
          </p>
        </div>

        <!-- Controls: Gold Start, Black Pause, Crimson Stop -->
        <div class="flex items-center space-x-3">
          <button class="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-black text-xs font-black shadow-[0_0_25px_rgba(245,158,11,0.35)] transition-all transform hover:-translate-y-0.5">
            <i data-lucide="play" class="w-3.5 h-3.5 fill-current"></i>
            <span>START BOT</span>
          </button>

          <button class="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-black hover:bg-[#141210] border border-white/[0.12] text-slate-200 text-xs font-semibold transition-all">
            <i data-lucide="pause" class="w-3.5 h-3.5"></i>
            <span>PAUSE</span>
          </button>

          <button class="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 border border-red-500 text-white text-xs font-black shadow-[0_0_22px_rgba(239,68,68,0.35)] transition-all transform hover:-translate-y-0.5">
            <i data-lucide="square" class="w-3 h-3 fill-current"></i>
            <span>STOP ALL</span>
          </button>
        </div>
      </div>

      <!-- Telemetry Cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-white/[0.08]">
        <div class="p-3.5 rounded-xl bg-black border border-amber-500/20">
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Today's P&L</span>
          <div class="text-lg font-bold font-mono text-amber-300 mt-1">+₹0.00</div>
        </div>
        <div class="p-3.5 rounded-xl bg-black border border-white/[0.08]">
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Active Signals</span>
          <div class="text-lg font-bold font-mono text-slate-200 mt-1">0</div>
        </div>
        <div class="p-3.5 rounded-xl bg-black border border-red-500/20">
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Daily Stop Loss</span>
          <div class="text-lg font-bold font-mono text-red-400 mt-1">₹2,500.00</div>
        </div>
        <div class="p-3.5 rounded-xl bg-black border border-amber-500/20">
          <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Safety Circuit</span>
          <div class="text-lg font-bold font-mono text-amber-400 mt-1 flex items-center gap-1.5">
            <i data-lucide="shield-check" class="w-4 h-4 text-amber-400"></i>
            <span>ARMED</span>
          </div>
        </div>
      </div>
    </div>

    <!-- CONFIGURED STRATEGIES -->
    <div class="glass-panel rounded-2xl p-6 space-y-4">
      <div class="flex items-center justify-between pb-3 border-b border-white/[0.08]">
        <div class="flex items-center space-x-3">
          <span class="px-3 py-1 text-xs font-bold rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/30">
            Active Strategies (5)
          </span>
          <span class="px-3 py-1 text-xs font-medium text-slate-400 hover:text-white cursor-pointer transition-colors">
            Performance Attribution
          </span>
        </div>
        <span class="text-xs text-amber-500/80 font-mono">CORE: #ENG-611</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
        <!-- Strat 1 -->
        <div class="p-4 rounded-xl bg-black border border-white/[0.08] hover:border-amber-500/30 transition-all flex flex-col justify-between">
          <div class="space-y-2.5">
            <div class="flex items-start justify-between">
              <div>
                <h4 class="text-xs font-bold text-white">Intraday Momentum</h4>
                <span class="text-[11px] text-slate-500">Trend Scalper</span>
              </div>
              <span class="px-2 py-0.5 rounded-full text-[9px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30">
                Moderate
              </span>
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">
              Volume breakouts in top 20 liquid NSE contracts with dynamic ATR trailing stops.
            </p>
          </div>
          <div class="pt-3 mt-3 border-t border-white/[0.08] flex items-center justify-between">
            <span class="text-slate-400 font-mono text-xs">Win: <strong class="text-white">54.0%</strong></span>
            <span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30">ENABLED</span>
          </div>
        </div>

        <!-- Strat 2 -->
        <div class="p-4 rounded-xl bg-black border border-white/[0.08] hover:border-amber-500/30 transition-all flex flex-col justify-between">
          <div class="space-y-2.5">
            <div class="flex items-start justify-between">
              <div>
                <h4 class="text-xs font-bold text-white">Mean Reversion</h4>
                <span class="text-[11px] text-slate-500">Statistical Arb</span>
              </div>
              <span class="px-2 py-0.5 rounded-full text-[9px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30">
                Low Risk
              </span>
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">
              Fades overextended 2-SD moves at Bollinger extremes during midday consolidation.
            </p>
          </div>
          <div class="pt-3 mt-3 border-t border-white/[0.08] flex items-center justify-between">
            <span class="text-slate-400 font-mono text-xs">Win: <strong class="text-white">58.5%</strong></span>
            <span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30">ENABLED</span>
          </div>
        </div>

        <!-- Strat 3 -->
        <div class="p-4 rounded-xl bg-black border border-red-500/20 hover:border-red-500/40 transition-all flex flex-col justify-between">
          <div class="space-y-2.5">
            <div class="flex items-start justify-between">
              <div>
                <h4 class="text-xs font-bold text-white">Breakout Volume</h4>
                <span class="text-[11px] text-slate-500">Directional</span>
              </div>
              <span class="px-2 py-0.5 rounded-full text-[9px] font-bold text-red-400 bg-red-500/10 border border-red-500/30">
                High Risk
              </span>
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">
              Trades opening range breakouts (ORB 15-min) with 2.5x standard relative volume.
            </p>
          </div>
          <div class="pt-3 mt-3 border-t border-white/[0.08] flex items-center justify-between">
            <span class="text-slate-400 font-mono text-xs">Win: <strong class="text-white">49.8%</strong></span>
            <span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold text-slate-500 bg-white/[0.04] border border-white/[0.08]">DISABLED</span>
          </div>
        </div>

        <!-- Strat 4 -->
        <div class="p-4 rounded-xl bg-black border border-white/[0.08] hover:border-amber-500/30 transition-all flex flex-col justify-between">
          <div class="space-y-2.5">
            <div class="flex items-start justify-between">
              <div>
                <h4 class="text-xs font-bold text-white">RSI Scalper</h4>
                <span class="text-[11px] text-slate-500">Micro Scalp</span>
              </div>
              <span class="px-2 py-0.5 rounded-full text-[9px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30">
                Moderate
              </span>
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">
              Fast 5-min momentum exhaustion targeting 0.35% quick scalp moves with strict exit.
            </p>
          </div>
          <div class="pt-3 mt-3 border-t border-white/[0.08] flex items-center justify-between">
            <span class="text-slate-400 font-mono text-xs">Win: <strong class="text-white">52.1%</strong></span>
            <span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold text-slate-500 bg-white/[0.04] border border-white/[0.08]">DISABLED</span>
          </div>
        </div>

        <!-- Strat 5 -->
        <div class="p-4 rounded-xl bg-black border border-white/[0.08] hover:border-amber-500/30 transition-all flex flex-col justify-between">
          <div class="space-y-2.5">
            <div class="flex items-start justify-between">
              <div>
                <h4 class="text-xs font-bold text-white">Swing Follower</h4>
                <span class="text-[11px] text-slate-500">Trend Horizon</span>
              </div>
              <span class="px-2 py-0.5 rounded-full text-[9px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30">
                Low Risk
              </span>
            </div>
            <p class="text-[11px] text-slate-400 leading-relaxed">
              Filters 15m and 60m trend alignment using SuperTrend Quant dual-engine logic.
            </p>
          </div>
          <div class="pt-3 mt-3 border-t border-white/[0.08] flex items-center justify-between">
            <span class="text-slate-400 font-mono text-xs">Win: <strong class="text-white">51.2%</strong></span>
            <span class="px-2 py-0.5 rounded text-[9px] font-mono font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30">ENABLED</span>
          </div>
        </div>
      </div>
    </div>

    <!-- TRADE LOG -->
    <div class="glass-panel rounded-2xl p-6 space-y-4">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
        <div class="flex items-center space-x-2">
          <i data-lucide="clock" class="w-4 h-4 text-amber-400"></i>
          <h3 class="text-sm font-bold text-white tracking-tight">Trade Execution Log</h3>
          <span class="text-xs text-slate-500 font-mono">(Paper Journal)</span>
        </div>

        <div class="flex items-center space-x-1 bg-black p-1 rounded-xl border border-white/[0.08]">
          <button class="px-3 py-1 text-xs font-bold rounded-lg bg-amber-500 text-black shadow-sm">ALL</button>
          <button class="px-3 py-1 text-xs font-medium text-slate-400 hover:text-white">BUY</button>
          <button class="px-3 py-1 text-xs font-medium text-slate-400 hover:text-white">SELL</button>
          <button class="px-3 py-1 text-xs font-medium text-slate-400 hover:text-white">OPEN</button>
          <button class="px-3 py-1 text-xs font-medium text-slate-400 hover:text-white">ENDED</button>
        </div>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-left text-xs border-collapse">
          <thead>
            <tr class="border-b border-white/[0.08] text-[10px] uppercase tracking-wider text-slate-400 bg-black">
              <th class="py-3 px-4 font-semibold">Time</th>
              <th class="py-3 px-4 font-semibold">Symbol</th>
              <th class="py-3 px-4 font-semibold">Strategy</th>
              <th class="py-3 px-4 font-semibold">Side</th>
              <th class="py-3 px-4 font-semibold text-right">Qty</th>
              <th class="py-3 px-4 font-semibold text-right">Entry (₹)</th>
              <th class="py-3 px-4 font-semibold text-right">Exit (₹)</th>
              <th class="py-3 px-4 font-semibold text-right">Realized P&L</th>
              <th class="py-3 px-4 font-semibold text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colspan="9" class="py-16 text-center">
                <div class="flex flex-col items-center justify-center space-y-2.5">
                  <div class="w-11 h-11 rounded-2xl bg-black border border-white/[0.1] flex items-center justify-center text-slate-400">
                    <i data-lucide="inbox" class="w-5 h-5 text-amber-500/80"></i>
                  </div>
                  <span class="text-sm font-bold text-slate-200">No trades yet</span>
                  <p class="text-xs text-slate-500 max-w-sm">
                    The bot engine is currently stopped. Start the bot or trigger a simulation run to capture intraday paper executions.
                  </p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- BACKTEST ENGINE & TOURNAMENT -->
    <div class="glass-panel rounded-2xl p-6 space-y-5">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-white/[0.08]">
        <div>
          <h3 class="text-sm font-bold text-white tracking-tight flex items-center gap-2">
            <i data-lucide="bar-chart-3" class="w-4 h-4 text-amber-400"></i>
            Quantitative Backtest Engine
          </h3>
          <p class="text-xs text-slate-400 mt-0.5">
            Historical execution simulator with realistic NSE slippage and transaction fee modeling.
          </p>
        </div>
        <span class="px-2.5 py-1 rounded-full text-[10px] font-mono text-amber-400 bg-amber-500/10 border border-amber-500/30">
          ENGINE: v6.1-CORE
        </span>
      </div>

      <!-- Inputs -->
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3.5">
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">Symbol</label>
          <input type="text" value="NIFTY 50" class="w-full glass-input rounded-xl px-3 py-2 text-xs font-mono">
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">Strategy</label>
          <select class="w-full glass-input rounded-xl px-3 py-2 text-xs font-mono">
            <option>SuperTrend Quant (10, 3.0)</option>
            <option>Mean Reversion (2.0 StdDev)</option>
            <option>Breakout Volume (15m ORB)</option>
          </select>
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">Start Date</label>
          <input type="date" value="2024-01-01" class="w-full glass-input rounded-xl px-3 py-2 text-xs font-mono">
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">End Date</label>
          <input type="date" value="2024-11-05" class="w-full glass-input rounded-xl px-3 py-2 text-xs font-mono">
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">Capital (₹)</label>
          <input type="text" value="100000" class="w-full glass-input rounded-xl px-3 py-2 text-xs font-mono">
        </div>
        <div class="space-y-1.5">
          <label class="text-[10px] font-bold text-amber-400/90 uppercase tracking-wider">Stop ATR Mult</label>
          <input type="text" value="3.0" class="w-full glass-input rounded-xl px-3 py-2 text-xs font-mono">
        </div>
      </div>

      <!-- Triggers -->
      <div class="flex flex-wrap items-center gap-3 pt-1">
        <button class="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-black text-xs font-black shadow-[0_0_22px_rgba(245,158,11,0.35)] transition-all transform hover:-translate-y-0.5">
          <i data-lucide="play" class="w-3.5 h-3.5 fill-current"></i>
          <span>RUN BACKTEST</span>
        </button>

        <button class="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-black hover:bg-[#141210] border border-amber-500/30 text-amber-300 text-xs font-bold transition-all">
          <i data-lucide="sparkles" class="w-3.5 h-3.5 text-amber-400"></i>
          <span>RUN 30-STRATEGY TOURNAMENT</span>
        </button>
      </div>

      <!-- 30-Strategy Leaderboard -->
      <div class="pt-3">
        <div class="flex items-center justify-between pb-3">
          <h4 class="text-xs font-bold text-white tracking-tight uppercase flex items-center gap-2">
            <i data-lucide="trophy" class="w-4 h-4 text-amber-400"></i>
            30-Strategy Leaderboard
          </h4>
          <span class="text-[11px] text-amber-500/80 font-mono">BENCHMARK: NIFTY 50 TRI</span>
        </div>

        <div class="overflow-x-auto rounded-xl border border-white/[0.08]">
          <table class="w-full text-left text-xs border-collapse">
            <thead>
              <tr class="border-b border-white/[0.08] text-[10px] uppercase tracking-wider text-slate-400 bg-black">
                <th class="py-3 px-4 font-semibold">Rank</th>
                <th class="py-3 px-4 font-semibold">Strategy Name</th>
                <th class="py-3 px-4 font-semibold text-right">Win Rate</th>
                <th class="py-3 px-4 font-semibold text-right">Sharpe</th>
                <th class="py-3 px-4 font-semibold text-right">Trades</th>
                <th class="py-3 px-4 font-semibold text-right">Avg Return (₹)</th>
                <th class="py-3 px-4 font-semibold text-right">Score</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-white/[0.04] font-mono tabular-nums text-slate-300">
              <!-- Leader Row #1 -->
              <tr class="bg-amber-500/[0.08] border-l-2 border-amber-400 transition-colors">
                <td class="py-3 px-4">
                  <span class="px-2 py-0.5 rounded-full text-[10px] font-black bg-amber-400 text-black shadow-[0_0_8px_#f59e0b]">#1</span>
                </td>
                <td class="py-3 px-4 font-sans font-bold text-white flex items-center gap-2">
                  SuperTrend Quant (10, 3.0)
                  <span class="px-1.5 py-0.2 rounded-full bg-red-500/20 text-red-400 border border-red-500/30 text-[9px] font-mono font-bold">LEADER</span>
                </td>
                <td class="py-3 px-4 text-right text-amber-400 font-bold">51.2%</td>
                <td class="py-3 px-4 text-right">0.63</td>
                <td class="py-3 px-4 text-right text-slate-400">184</td>
                <td class="py-3 px-4 text-right text-amber-400 font-bold">800.38</td>
                <td class="py-3 px-4 text-right font-black text-amber-300">170.94</td>
              </tr>

              <!-- Row 2 -->
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-3 px-4"><span class="px-2 py-0.5 rounded-full text-[10px] bg-white/[0.05] text-slate-400 border border-white/[0.08]">#2</span></td>
                <td class="py-3 px-4 font-sans text-slate-200">VWAP Institutional Pullback</td>
                <td class="py-3 px-4 text-right text-amber-400/90">56.4%</td>
                <td class="py-3 px-4 text-right">0.61</td>
                <td class="py-3 px-4 text-right text-slate-400">212</td>
                <td class="py-3 px-4 text-right text-amber-400/90">742.10</td>
                <td class="py-3 px-4 text-right font-bold text-white">164.20</td>
              </tr>

              <!-- Row 3 -->
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-3 px-4"><span class="px-2 py-0.5 rounded-full text-[10px] bg-white/[0.05] text-slate-400 border border-white/[0.08]">#3</span></td>
                <td class="py-3 px-4 font-sans text-slate-200">EMA Ribbon Scalper 5m</td>
                <td class="py-3 px-4 text-right text-amber-400/90">48.9%</td>
                <td class="py-3 px-4 text-right">0.58</td>
                <td class="py-3 px-4 text-right text-slate-400">310</td>
                <td class="py-3 px-4 text-right text-amber-400/90">680.50</td>
                <td class="py-3 px-4 text-right font-bold text-white">158.45</td>
              </tr>

              <!-- Row 4 -->
              <tr class="hover:bg-white/[0.02] transition-colors">
                <td class="py-3 px-4"><span class="px-2 py-0.5 rounded-full text-[10px] bg-white/[0.05] text-slate-400 border border-white/[0.08]">#4</span></td>
                <td class="py-3 px-4 font-sans text-slate-200">Opening Range Breakout 15m</td>
                <td class="py-3 px-4 text-right text-amber-400/90">53.0%</td>
                <td class="py-3 px-4 text-right">0.54</td>
                <td class="py-3 px-4 text-right text-slate-400">142</td>
                <td class="py-3 px-4 text-right text-amber-400/90">610.25</td>
                <td class="py-3 px-4 text-right font-bold text-white">151.10</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

  </main>

  <footer class="border-t border-white/[0.08] bg-black px-6 py-4 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500">
    <div>ApexTrade v6.1.1 — Owner-Only NSE Intraday Paper Signal System</div>
    <div class="font-mono text-[11px] text-amber-500/70">Simulated Environment • Zero Real Funds at Risk</div>
  </footer>

  <script>
    lucide.createIcons();

    function switchTab(tabId) {
      document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.className = 'nav-btn px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white hover:bg-white/[0.04] transition-all flex items-center gap-1.5';
      });

      const activeBtn = document.getElementById('tab-' + tabId);
      if (activeBtn) {
        activeBtn.className = 'nav-btn px-3 py-1.5 rounded-lg text-xs font-bold bg-amber-500/15 text-amber-300 border border-amber-500/40 flex items-center gap-1.5 shadow-[0_0_15px_rgba(245,158,11,0.2)]';
      }
    }
  </script>
</body>
</html>
```

---

## 3. Updated Code for Your Local App Files

Apply these changes to `C:\Users\aryan\OneDrive\Desktop\app\projects\trade.ai`:

### File 1: `src/index.css`
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  /* Black, Red & Gold Only */
  --bg-canvas: #050506;
  --bg-surface: #0c0a09;
  --border-gold: rgba(245, 158, 11, 0.2);
  --gold: #f59e0b;
  --gold-light: #fbbf24;
  --red: #ef4444;
  --red-dark: #dc2626;
}

body {
  background-color: var(--bg-canvas);
  color: #f8fafc;
  font-family: -apple-system, BlinkMacSystemFont, "Plus Jakarta Sans", sans-serif;
  overflow-x: hidden;
}

.font-mono {
  font-variant-numeric: tabular-nums;
}

.glass-panel {
  background-color: var(--bg-surface);
  border: 1px solid var(--border-gold);
  box-shadow: 0 16px 36px -12px rgba(0, 0, 0, 0.9);
}

.glass-input {
  background: #000000;
  border: 1px solid rgba(245, 158, 11, 0.25);
  color: #ffffff;
}
.glass-input:focus {
  outline: none;
  border-color: var(--gold);
  box-shadow: 0 0 0 2px rgba(245, 158, 11, 0.25);
}

.btn-gold {
  background: linear-gradient(135deg, #fbbf24, #f59e0b);
  color: #000000;
  font-weight: 800;
  box-shadow: 0 0 22px rgba(245, 158, 11, 0.35);
}
.btn-gold:hover {
  background: linear-gradient(135deg, #fde68a, #fbbf24);
}

.btn-crimson {
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: #ffffff;
  font-weight: 800;
  box-shadow: 0 0 22px rgba(239, 68, 68, 0.35);
}
.btn-crimson:hover {
  background: linear-gradient(135deg, #f87171, #ef4444);
}
```

### File 2: `src/components/Header.jsx`
Update your Header to use Gold badges and the Crimson Red PAPER ONLY tag:

```jsx
import React from 'react';
import { 
  Activity, 
  Search, 
  ShieldCheck, 
  Cpu, 
  Layers, 
  LineChart, 
  TrendingUp, 
  PieChart, 
  BookOpen 
} from 'lucide-react';

export default function Header({ activeTab, setActiveTab }) {
  const navItems = [
    { id: 'home', label: 'Home', icon: Activity },
    { id: 'bot', label: 'Bot Engine', icon: Cpu },
    { id: 'terminal', label: 'Terminal', icon: LineChart },
    { id: 'scanner', label: 'Scanner', icon: Layers },
    { id: 'predictions', label: 'Predictions', icon: TrendingUp },
    { id: 'analytics', label: 'Analytics', icon: PieChart },
    { id: 'journal', label: 'Journal', icon: BookOpen },
    { id: 'security', label: 'Security', icon: ShieldCheck },
  ];

  return (
    <header className="sticky top-0 z-50 w-full bg-[#050506]">
      {/* TIER 1: Ticker Strip */}
      <div className="h-8 border-b border-white/[0.08] bg-black px-4 lg:px-8 flex items-center justify-between text-xs text-slate-400 overflow-x-auto whitespace-nowrap">
        <div className="flex items-center space-x-5">
          <div className="flex items-center space-x-2">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500" />
            </span>
            <span className="text-[10px] font-bold tracking-wider text-amber-400 uppercase">NSE TICK FEED</span>
            <span className="px-1.5 py-0.2 rounded bg-amber-500/10 border border-amber-500/30 text-[9px] font-semibold text-amber-300 font-mono">
              SIMULATED
            </span>
          </div>

          <div className="h-3 w-[1px] bg-white/[0.1]" />

          <div className="flex items-center space-x-6 font-mono text-[11px]">
            <span>NIFTY 50: <strong className="text-amber-400 font-medium">24,180.20 (+0.32%)</strong></span>
            <span>BANKNIFTY: <strong className="text-red-400 font-medium">51,240.10 (-0.14%)</strong></span>
            <span className="flex items-center gap-1.5 text-slate-300">
              YESBANK: <strong className="text-white">₹0.00</strong>
              <span className="px-1 py-0.2 rounded bg-white/[0.06] text-[9px] text-slate-400 border border-white/[0.1]">SIM</span>
            </span>
          </div>
        </div>

        <div className="hidden md:flex items-center space-x-4 text-[11px] text-slate-500">
          <span>FEED: <strong className="text-amber-400 font-mono">SYNCHRONIZED</strong></span>
          <span>LATENCY: <strong className="text-slate-300 font-mono">11ms</strong></span>
        </div>
      </div>

      {/* TIER 2: Main Brand & Navigation Strip */}
      <div className="border-b border-white/[0.08] bg-[#070605] px-4 lg:px-8 h-14 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-amber-400 to-amber-600 border border-amber-300 flex items-center justify-center text-black font-extrabold text-xs tracking-wider font-mono shadow-[0_0_15px_rgba(245,158,11,0.3)]">
            AT
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-base font-extrabold text-white tracking-tight">ApexTrade</span>
            <span className="px-1.5 py-0.5 rounded bg-white/[0.05] border border-white/[0.1] text-[10px] font-mono text-slate-400 font-medium">
              v6.1.1
            </span>
            <span className="px-2 py-0.5 rounded-full bg-red-500/10 border border-red-500/30 text-[10px] font-bold text-red-400">
              PAPER ONLY
            </span>
          </div>
        </div>

        {/* Navigation Tabs */}
        <nav className="hidden xl:flex items-center space-x-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`px-3 py-1.5 rounded-lg text-xs transition-all flex items-center gap-1.5 ${
                  isActive
                    ? 'font-bold bg-amber-500/15 text-amber-300 border border-amber-500/40 shadow-[0_0_15px_rgba(245,158,11,0.2)]'
                    : 'font-medium text-slate-400 hover:text-white hover:bg-white/[0.04]'
                }`}
              >
                <Icon size={14} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {/* Search & Profile */}
        <div className="flex items-center space-x-3">
          <div className="relative w-44 md:w-60">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
            <input
              type="text"
              placeholder="Search instruments..."
              readOnly
              className="w-full glass-input rounded-lg pl-9 pr-8 py-1.5 text-xs text-slate-200 placeholder-slate-500 cursor-pointer"
            />
            <span className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] bg-black text-amber-400 px-1.5 py-0.5 rounded border border-amber-500/30 font-mono">
              ⌘K
            </span>
          </div>

          <div className="w-8 h-8 rounded-lg bg-black border border-amber-500/30 flex items-center justify-center text-xs font-black text-amber-400 font-mono">
            OW
          </div>
        </div>
      </div>

      {/* TIER 3: Portfolio & Status Strip */}
      <div className="h-11 border-b border-white/[0.08] bg-black px-4 lg:px-8 flex items-center justify-between text-xs overflow-x-auto whitespace-nowrap">
        <div className="flex items-center space-x-6 font-mono text-xs">
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">CASH:</span>
            <span className="text-white font-medium">₹0.00</span>
          </div>
          <div className="h-3 w-[1px] bg-white/[0.1]" />
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">HOLDINGS:</span>
            <span className="text-white font-medium">₹0.00</span>
          </div>
          <div className="h-3 w-[1px] bg-white/[0.1]" />
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">TODAY'S P&L:</span>
            <span className="text-amber-300 bg-amber-500/10 border border-amber-500/30 px-2.5 py-0.5 rounded-full font-bold">
              +₹0.00 (0.00%)
            </span>
          </div>
        </div>

        <div className="flex items-center space-x-5">
          <div className="flex items-center space-x-2">
            <span className="text-[11px] font-sans font-semibold text-slate-400 uppercase tracking-wider">BOT ENGINE:</span>
            <span className="px-2.5 py-0.5 rounded-full bg-red-500/10 border border-red-500/40 text-[10px] font-mono font-bold text-red-400 shadow-[0_0_10px_rgba(239,68,68,0.2)]">
              STOPPED
            </span>
          </div>
          <div className="hidden sm:flex items-center space-x-1.5 text-slate-400 text-xs">
            <span className="w-2 h-2 rounded-full bg-amber-400 shadow-[0_0_8px_#f59e0b]" />
            <span className="font-medium text-slate-300">NSE: OPEN</span>
          </div>
        </div>
      </div>
    </header>
  );
}
```

### File 3: `src/components/BotEngine.jsx`
Updated with Gold Start, Black Pause, and Crimson Red Stop triggers:

```jsx
import React from 'react';
import { Play, Pause, Square, ShieldCheck } from 'lucide-react';

export default function BotEngine() {
  const strategies = [
    { id: 1, name: 'Intraday Momentum', type: 'Trend Scalper', risk: 'Moderate', winRate: '54.0%', enabled: true },
    { id: 2, name: 'Mean Reversion', type: 'Statistical Arb', risk: 'Low Risk', winRate: '58.5%', enabled: true },
    { id: 3, name: 'Breakout Volume', type: 'Directional', risk: 'High Risk', winRate: '49.8%', enabled: false },
    { id: 4, name: 'RSI Scalper', type: 'Micro Scalp', risk: 'Moderate', winRate: '52.1%', enabled: false },
    { id: 5, name: 'Swing Follower', type: 'Trend Horizon', risk: 'Low Risk', winRate: '51.2%', enabled: true },
  ];

  return (
    <div className="space-y-6">
      {/* Bot Hero Matrix */}
      <div className="glass-panel rounded-2xl p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-5">
          <div className="space-y-1.5">
            <div className="flex items-center space-x-3">
              <h2 className="text-lg font-extrabold text-white tracking-tight">Bot Engine Control Matrix</h2>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-red-500/15 border border-red-500/40 text-red-400">
                STATUS: STOPPED
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/15 border border-amber-500/30 text-amber-300">
                PAPER RUNTIME
              </span>
            </div>
            <p className="text-xs text-slate-400 max-w-xl">
              Autonomous signal dispatch pipeline. Simulates intraday orders on simulated NSE ticks with zero live market exposure.
            </p>
          </div>

          {/* Action Triggers: 24K Gold Start, Dark Pause, Crimson Stop */}
          <div className="flex items-center space-x-3">
            <button className="flex items-center space-x-2 px-6 py-2.5 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-black text-xs font-black shadow-[0_0_25px_rgba(245,158,11,0.35)] transition-all transform hover:-translate-y-0.5">
              <Play size={14} fill="currentColor" />
              <span>START BOT</span>
            </button>
            <button className="flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-black hover:bg-[#141210] border border-white/[0.12] text-slate-200 text-xs font-semibold transition-all">
              <Pause size={14} />
              <span>PAUSE</span>
            </button>
            <button className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 border border-red-500 text-white text-xs font-black shadow-[0_0_22px_rgba(239,68,68,0.35)] transition-all transform hover:-translate-y-0.5">
              <Square size={12} fill="currentColor" />
              <span>STOP ALL</span>
            </button>
          </div>
        </div>

        {/* Telemetry */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6 pt-6 border-t border-white/[0.08]">
          <div className="p-3.5 rounded-xl bg-black border border-amber-500/20">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Today's P&L</span>
            <div className="text-lg font-bold font-mono text-amber-300 mt-1">+₹0.00</div>
          </div>
          <div className="p-3.5 rounded-xl bg-black border border-white/[0.08]">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Active Signals</span>
            <div className="text-lg font-bold font-mono text-slate-200 mt-1">0</div>
          </div>
          <div className="p-3.5 rounded-xl bg-black border border-red-500/20">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Daily Stop Loss</span>
            <div className="text-lg font-bold font-mono text-red-400 mt-1">₹2,500.00</div>
          </div>
          <div className="p-3.5 rounded-xl bg-black border border-amber-500/20">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Safety Circuit</span>
            <div className="text-lg font-bold font-mono text-amber-400 mt-1 flex items-center gap-1.5">
              <ShieldCheck size={16} className="text-amber-400" />
              <span>ARMED</span>
            </div>
          </div>
        </div>
      </div>

      {/* Strategies List */}
      <div className="glass-panel rounded-2xl p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-white/[0.08]">
          <div className="flex items-center space-x-3">
            <span className="px-3 py-1 text-xs font-bold rounded-lg bg-amber-500/15 text-amber-300 border border-amber-500/30">
              Active Strategies (5)
            </span>
            <span className="px-3 py-1 text-xs font-medium text-slate-400 hover:text-white cursor-pointer transition-colors">
              Performance Attribution
            </span>
          </div>
          <span className="text-xs text-amber-500/80 font-mono">CORE: #ENG-611</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
          {strategies.map((strat) => (
            <div
              key={strat.id}
              className={`p-4 rounded-xl bg-black border ${
                strat.risk === 'High Risk' ? 'border-red-500/25 hover:border-red-500/40' : 'border-white/[0.08] hover:border-amber-500/30'
              } transition-all flex flex-col justify-between`}
            >
              <div className="space-y-2.5">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="text-xs font-bold text-white">{strat.name}</h4>
                    <span className="text-[11px] text-slate-500">{strat.type}</span>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[9px] font-bold ${
                      strat.risk === 'High Risk'
                        ? 'text-red-400 bg-red-500/10 border border-red-500/30'
                        : 'text-amber-400 bg-amber-500/10 border border-amber-500/30'
                    }`}
                  >
                    {strat.risk}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  Intraday quant signals executed on simulated ticks.
                </p>
              </div>
              <div className="pt-3 mt-3 border-t border-white/[0.08] flex items-center justify-between">
                <span className="text-slate-400 font-mono text-xs">Win: <strong className="text-white">{strat.winRate}</strong></span>
                <span
                  className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold ${
                    strat.enabled
                      ? 'text-amber-400 bg-amber-500/10 border border-amber-500/30'
                      : 'text-slate-500 bg-white/[0.04] border border-white/[0.08]'
                  }`}
                >
                  {strat.enabled ? 'ENABLED' : 'DISABLED'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

---

## 4. Verification Check
- **Zero purple/blue/green:** Every highlight is either 24K Gold or Crimson Red on pure Obsidian Black.
- **Zero text collisions:** Tier 1 ticker strip, Tier 2 brand/search, and Tier 3 portfolio balances are completely separated.
- **Original data preserved:** Bot is `STOPPED`, Today's P&L is `+₹0.00`, Trade Log is `"No trades yet"`, and Leaderboard #1 is `SuperTrend Quant (10, 3.0)` with Score `170.94`.
