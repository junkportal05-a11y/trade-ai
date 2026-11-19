# ApexTrade — Full Rebuild Prompt

Copy this whole file into a `.md` file and tell OpenCode to read it and do everything in it, in order. This is a rebuild, not a patch: the app's purpose changes, the navigation changes, and everything that is not prediction is removed.

## 0. Context — read this first

- **App:** ApexTrade — NSE Intraday Signals. Live at https://trade-ai-beta.vercel.app/ (v6.1.1). Backend: https://apextrade-core-trade-ai-backend.hf.space (Vercel rewrites `/api/*` to it).
- **Repo:** https://github.com/junkportal05-a11y/trade-ai, branch `main`. Rebuild inside this same repo and the same Vercel + Hugging Face deployment. Do not start a second app.
- **Local project path:** `C:\Users\aryan\OneDrive\Desktop\app\projects\trade ai`
- **Rules for this whole job:**
  - Read the **actual local source files**. Code wins over docs. `codebase.md` is historical only — do not trust it, and **update it at the end** to match what you actually changed and verified.
  - **The app never places an order — in any phase.** Remove all order-placement code entirely (see §4). There is no trading capability left to gate; the app is incapable of trading by construction. `live_trading_armed` stays `False` and `trading_mode` stays `paper` wherever those flags still exist.
  - Single user only: `apex_head_quant`, `LEVEL_4_ROOT`. Do not add any multi-user login, signup, roles, or new auth system. The existing single-code gate (`POST /api/login`, `GET /api/auth/verify`, `apt_token`) stays as it is.
  - No secrets in code. API keys and passwords go in environment variables only. Never commit a `.env` file. (Note: the old Gemini key leaked into a report file — it must be rotated; use a fresh key from env only.)
  - Test every change before claiming it works. A feature is done only when the **live site** shows it working, not when the code merely looks right.
  - Work in order. Do not skip ahead to UI polish while the deployment is still unpinned (§1).

## 1. Step 0 — Pin the deployment to ONE commit (do this first)

**Problem (verified live 19 Nov 2026):** the live site does not run the repo HEAD. Proof:
- The Scanner's "Market is closed. No active intraday setups detected on live feed." string does **not exist anywhere** in the repo at HEAD `998bb76` (18 Nov 2026) — but it **does** exist in the live JS bundle (`/assets/index-BtXlUtu2.js`, 292,045 bytes).
- The live site serves **different layouts between loads**: Predictions flips between "AI Prediction Engine" and "PREDICTION TRACKING CENTER"; the Journal layout changes; the Security page profile flips between "Vishal Agnihotri — vishalagnihotri12@gmail.com — Trader — PRO ACCESS" and "Lead Quant — Master Quant / Administrator, LEVEL_4_ROOT"; strategy win rates change run to run (Mean Reversion 58.5% vs 52.3%).
- The repo has **two backend entry points**: `backend/Procfile` starts `uvicorn main:app`, `backend/Dockerfile` starts `uvicorn app.main:app`. It is unverified which one the live Hugging Face backend actually runs.

**Fix:**
1. Find out exactly which commit/branch Vercel builds the frontend from and which entry point the Hugging Face Space runs. Check the Vercel project settings, the Hugging Face Space settings, and the GitHub repo — do not guess.
2. Make the live deployment build from **one** commit of `main`. Remove or reconcile the second entry point so there is exactly one way the backend starts.
3. Redeploy, then prove parity: fetch the live JS bundle and confirm the strings and components in it match the repo source you just built from. Confirm the same layout, same profile, same win rates across three separate loads.

**Verification:** three separate loads of the live site show identical layouts and identical strategy win rates. If they still differ, Step 0 is not done — stop and report why before touching anything else.

## 2. The new purpose — the whole rebuild follows from this

**ApexTrade is built only to analyse stocks and predict them.** It predicts future stocks/charts by analysing them. That is the entire job.

- **How predictions are made:** the 5 Strategies are the prediction engines — Trend Scalper, Mean Reversion, Breakout Volume, RSI Scalper, Swing Trend Follower. Each one analyses the chart its own way and produces predictions.
- **How predictions are proven:** every prediction gets a recorded outcome (entry, target, stop, right/wrong). The app's one number that matters is **prediction accuracy per strategy** — which strategy actually predicts best.
- **What the app is NOT:** not a trading bot, not a portfolio tracker, not a broker terminal. It never places an order, never holds a real position, never shows P&L as real money (paper P&L only, always labelled PAPER).

This rebuild IS Phase 1 (see `apextrade-phases-1-2-3.md`): autonomous analysis + prediction, with outcomes tracked.

### The original vision (TradeAI / RetailOS)
The app was intended as a personal AI-powered stock market analysis and intraday trading command center — to help make data-driven trading decisions instead of guesses, emotions, or random tips:
- **AI Stock Scanner** — scan NSE/BSE, find intraday and BTST opportunities that fit available capital, generate entry, stop-loss and target prices, with technical reasons and confidence scores.
- **Smart Risk Management** — example capital ₹1,840; max risk per trade 2%; affordable share quantities; stop-loss and target levels; prevent oversized positions.
- **Live Market Data** — live/latest quotes, price movements, historical OHLCV, WebSocket streaming; broker data later (AngelOne is the broker here).
- **AI Trading Engine** — RSI, MACD, EMA, VWAP; breakout, momentum, reversal strategies; AI-assisted signals; market-condition analysis; strategy performance evaluation.
- **Trading Vault & Journal** — track capital, record trades, track profits and losses, analyse wins and losses, maintain discipline.
- **Roadmap:** 1 Backend + market data → 2 TradingView candlestick charts → 3 Indicators + strategy engine → 4 Paper trading → 5 Real-time broker data → 6 AI signal validation + backtesting → 7 Advanced AI assistant.
- **The point:** an AI that justifies its decisions with data and knows when NOT to trade. AI confidence scores are not proof — rigorous backtesting and paper trading come before any real-money execution.
- **This rebuild covers roadmap phases 1–3 and 6** (backend/data, charts, indicators/strategy engine, validation/backtesting). Paper trading (4) is the prediction-outcome record in §5c. Broker data (5) is data only, never orders. Phase 7 is later.

## 3. New navigation — 5 sections, one job each

Replace the current 8-section navigation (Home, Bot Engine, Terminal, Scanner, Predictions, Analytics, Journal, Security, MORE) with exactly this:

| Section | Job |
|---|---|
| **Home** | Today's prediction dashboard: market briefing, top predictions, strategy leaderboard, engine status |
| **Charts** | Analyse one stock: candles, indicators (EMA9, EMA21, VWAP, RSI(14)), and the AI Analyst note explaining the read |
| **Scanner** | Find setups: scan the watchlist, show qualifying setups with entry, stop-loss, target, confidence and technical reasons — plus position size from the risk calculator |
| **Predictions** | Predict + track: the AI Prediction Engine form, the prediction log (paper record with paper P&L as the outcome measure), accuracy per strategy |
| **Strategies** | The 5 prediction engines + backtest + accuracy comparison (which strategy predicts best) |

- **Analytics folds into Strategies** (accuracy comparison is strategy comparison — it does not need its own section).
- **Journal folds into Predictions** (the journal IS the prediction log).
- **Bot Engine is deleted** (see §4). Its only surviving piece is engine status, shown small on Home.
- **Security page is deleted** (see §4). The login gate itself stays — it is the entry screen, not a page.
- **MORE menu is deleted.** Whatever it held is either a section above or deleted in §4.

## 4. REMOVE — everything in this list goes, code included

Delete the feature and its code, routes, components, and database tables if nothing kept uses them. Do not hide them behind a flag — remove them.

1. **Bot Engine (the trading bot):** START BOT / PAUSE / STOP ALL, P&L, Active Signals, daily stop loss ₹2,500, safety circuit, Emergency Stop Bot. The "bot" as a trader ceases to exist.
2. **Real-money / holdings UI:** Portfolio Balances, Holdings Allocation, Net Worth, Cash, Holdings, Positions tab (real positions). The app holds no real money and no real positions.
   - KEPT as decision support (not execution): the Scanner's entry, stop-loss and target per setup, confidence scores, technical reasons, and the risk calculator (capital input, default ₹1,840, max risk 2% per trade, affordable quantity). These help decide; they never place an order.
   - KEPT as the outcome record: the prediction log (paper record) with paper P&L, labelled PAPER everywhere — it measures whether predictions were right, in rupees, on paper only. This is the Trading Vault & Journal: it analyses wins and losses so mistakes are visible.
3. **All order-placement code:** `place_order` and its live branch, any broker order call, any `order_mode="live"` path, the `POST /api/bot/start` trading endpoint. The app must contain no code path that can send an order to a broker.
4. **AngelOne broker connection:** the Security-page AngelOne connect form, stored broker credentials flow, "NOT CONNECTED" broker status. (AngelOne stays only as a *price data feed* option — see §5. If the data-feed wiring shares code with the order wiring, split them and delete the order half.)
5. **Chat:** the `/api/chat` route and any chat UI. There is no chat panel in the app today; do not build one. The Terminal's AI Analyst panel stays as a read-only explanation of the chart read (see §5), not a conversation.
6. **AI Quant Mentor recommendation** ("Do not deploy" and similar trading advice) and **Active Price Alerts**. Neither is prediction.
7. **SYSTEM HEALTH diagnostics panel** (the NSE OPEN button panel). Replace with one small engine-status line on Home (see §5). Delete the detailed panel and its rows.
8. **Settings page and Help page.** Both are dead today (clicking them does nothing). Do not rebuild them. Anything genuinely needed becomes a small control on the page that uses it (e.g. timeframe selector on Charts).
9. **Command-palette trading actions:** Emergency Stop Bot, Clear Order Logs. Keep navigation + symbol search in the palette; fix the "undefined ·" label bug on symbols.
10. **Governance worker** (`governance_loop`) and the **trade-placing worker** (`trading_agent_loop` as a trader). The backend needs exactly two background jobs (see §5), not three.

## 5. KEEP — and fix while rebuilding

Each kept feature must work live after the rebuild. The bugs below were all verified live 19 Nov 2026 — fix them as part of the rebuild, not after it.

### 5a. Charts (was Terminal)
- Candles must load for RELIANCE 1m without pressing RETRY. (Verified failure: "Failed to load chart data. Tap RETRY to try again.", RETRY also fails. Note: the old yfinance MultiIndex bug is already fixed in code — `backend/signals.py:70-74` `_flatten_columns()` at every tier — so find the real cause live and fix that.)
- Indicators show: EMA9, EMA21, VWAP, RSI(14).
- The right-hand panel must have content in every tab — never a blank black area.
- AI Analyst panel stays as a read-only explanation note. Fix its Refresh: today it spins 20 seconds ("Running technical scan and generating insights...") then reverts to the same "no priced context available" note with no recommendation produced. It must either produce a read or say honestly why it cannot.
- Remove the POSITIONS tab, the TRADE LOG tab, and the BOT ENGINE tab from this panel. Tabs are: Chart, Strategies, Backtest, AI Analyst.

### 5b. Scanner
- **Fix the crash first:** opening Scanner starts its auto-scan, then the whole app crashes to "Something crashed inside ApexTrade. Attempting recovery..." (reproduced twice, 19 Nov 2026). Find the exception, fix the cause, and make the Scanner survive an empty, failed, or slow `POST /api/allocate` response without taking down the app.
- **Fix the false label:** the deployed Scanner prints "Market is closed. No active intraday setups detected on live feed." whenever `POST /api/allocate` returns zero signals — with no market-hours check at all (the string is not in repo HEAD; the header's "NSE OPEN" comes from a real IST check in `Header.jsx:13-28`). Gate the message on real market state (reuse `isNSEMarketOpen`, `frontend/src/hooks/useMarketData.js:305`): market genuinely closed → keep the label; market open + zero signals → honest empty state ("No qualifying setups — the scan ran but no signal passed the gates") with the per-gate rejection breakdown the repo's Scanner already renders (`ScannerPanel.jsx:820-860`).
- The SCAN & SIZE action must be reachable.
- Each qualifying setup shows entry, stop-loss, target, confidence score and technical reasons — plus position size from the risk calculator (capital default ₹1,840, max risk 2% per trade). These are predictions to decide on, not orders.

### 5c. Predictions (was Predictions + Journal)
- Restore the **AI Prediction Engine** as the Predictions page (symbol, timeframe, ANALYZE & PREDICT). It vanished after the crashes and was replaced by the Tracking Center alone — the rebuilt page has both, in one place.
- The **Prediction Tracking Center** stays: RECORD NEW SYSTEM PREDICTION form (symbol, BULLISH/BEARISH, entry/target/stop, confidence, RSI/MACD/ADX, thesis) and the prediction log below it. Nothing is auto-saved; the form only records when the user saves.
- **The prediction resolver must run:** today the Predictions Accuracy is 0.0% (0 of 0, "NO RESOLVED PREDICTIONS") and the log is empty, because no prediction ever gets an outcome. The resolver worker must record right/wrong for every prediction and update accuracy per strategy. This is the single most important behaviour in the rebuild: without it, the app cannot say which strategy predicts best.
- The prediction log records the paper outcome of each prediction, including paper P&L, always labelled PAPER — this is the Trading Vault & Journal: it analyses wins and losses so mistakes are visible.
- The Journal's ADD TRADE LOG modal is deleted. Its replacement is the prediction record form above. Fix the layout defect found in the old modal (Exit Price / Total PnL fields stuck out past the modal's right edge) — all fields must fit inside the modal.

### 5d. Strategies (was Strategies tab + Analytics + Backtest)
- The 5 strategy cards render with legible text and win rates. Fix the Trend Scalper card contrast (verified: white background, washed-out text, win rate illegible).
- **Backtest must run:** pressing RUN BACKTEST (RELIANCE, Intraday Momentum, 2024, ₹100,000, Stop ATR 1.5) today returns "'Repository' object has no attribute 'market_data'". Fix the missing attribute/wiring so the run completes and shows results.
- **Backtest leaderboard rows must do something:** clicking #1 (MFI 14 Reversals, Score 16) and #2 (Bollinger Bands Bounce) today changes nothing. Each row must open that strategy's backtest details.
- Analytics content moves here: accuracy per strategy, resolved-prediction counts, and the comparison of the 5 strategies. No blank black area — charts or a proper empty state, never empty space.
- The old "Strategies" MORE-menu behaviour (switching Terminal's right panel to a tab that first renders blank) is deleted with the MORE menu.

### 5e. Home (prediction dashboard)
- Keep: AI Daily Market Briefing (NIFTY bias, top picks), Top Screening Trigger (e.g. YESBANK BUY, RSI 67, Volume 1.3x Avg), Predictions Accuracy, strategy leaderboard, engine status line (prediction loop running/stopped, last scan time, feed status).
- Remove: Portfolio Balances, Holdings Allocation donut, AI Quant Mentor recommendation, Active Price Alerts.
- Links work: PREDICTIONS CENTRE, OPEN SIGNAL SCANNER, OPEN INTERACTIVE CHARTS — all three must navigate (Scanner link was untested because Scanner crashed; test it after §5b).

### 5f. Backend — two background jobs, honest data
- Exactly two background jobs: **(1) prediction loop** — runs the strategies on schedule during market hours and records predictions; **(2) prediction resolver** — records the outcome of each prediction and updates accuracy. Nothing else runs in the background.
- Data feeds stay (yfinance, AngelOne price feed, last-good snapshot) so Charts and Scanner have real prices. Simulated/synthetic data is always labelled where shown (SIMULATED / synthetic) — never presented as real market data. Note: `backend/signals.py` Tier 4 is a synthetic candle generator, labelled `"synthetic"` in `_SOURCE_CACHE` — surface that label in the UI.
- Restore `knowledge_dir` and `historical_data_dir` on the backend host (live `/api/health` says both do not exist), or confirm in the final report that they are intentionally absent.
- AI (Gemini) is configured from env only, with a rotated key — or the local fallback is accepted in writing. Fix the latent crash either way: `backend/app/services/chat.py:272` sets `parsed['source'] = 'litellm'`, but `ChatResponse` (`backend/app/models/schemas.py:119-123`) only allows `Literal["gemini", "heuristic"]` — add `"litellm"` or map it, so a configured local LLM cannot 500 the response.
- Remove the stale `http://127.0.0.1` / `http://localhost` / `https://my-backend.hf.space` URLs from the frontend bundle.

## 6. UI/UX rules for the rebuild

- **Dark only.** Clean dark, flat, near-black (`#080808` family), one restrained accent (`#D41514`), light text (`#CDCBCA`). No glassmorphism, no gradients, no coloured cards. (Auth gate stays flat `#0b0e13` / `#12161d` as before.)
- **One screen, one job.** Each of the 5 sections does exactly what §3 says and nothing else. No section grows a second job.
- **Big type, short lines, charts first.** The user reads predictions off charts — candles and accuracy numbers are the largest thing on the page; paragraphs stay short.
- **Honest empty states everywhere.** No blank black areas, no spinners that never resolve, no invented numbers. Empty means a sentence saying what is empty and why (e.g. "No qualifying setups — the scan ran but no signal passed the gates").
- **Every number is traceable.** A win rate, an accuracy, a backtest score must come from recorded predictions. If there are 0 resolved predictions, accuracy shows 0 of 0 — never a made-up percentage.
- **Decisions, not orders:** setups show entry, stop-loss, target, confidence and reasons; the log shows paper P&L labelled PAPER. There are no BUY/SELL buttons that place orders, no real positions, no "deploy". And the app must know when NOT to trade — when there is no setup, it says so plainly instead of inventing one.

## 7. Final verification checklist (all on the LIVE site, after deploy)

Tick each one off live. Nothing is "done" until its line is ticked.

- [ ] Three separate loads show identical layouts and identical strategy win rates (Step 0).
- [ ] Navigation has exactly 5 sections (Home, Charts, Scanner, Predictions, Strategies). No Bot Engine, no Journal, no Security, no Analytics, no MORE menu. No order buttons, no real positions, no real-money P&L anywhere.
- [ ] Charts: candles load for RELIANCE 1m without RETRY; indicators show; AI Analyst Refresh produces a read or an honest reason why not.
- [ ] Scanner opens three times without crashing; at market-open hours it never says "Market is closed"; an empty scan explains why; each qualifying setup shows entry, stop-loss, target, confidence, reasons and position size (₹1,840 capital, 2% risk).
- [ ] Predictions: AI Prediction Engine form is present every time; ANALYZE & PREDICT produces a result; the Tracking Center form records a prediction when saved.
- [ ] Prediction resolution works: a recorded prediction gets an outcome, and accuracy per strategy updates from 0 of 0. The prediction log shows the paper outcome with paper P&L labelled PAPER. (Verify with a real prediction, not a hardcoded number.)
- [ ] Risk calculator: changing capital and risk % updates the affordable quantity; defaults are ₹1,840 and 2%.
- [ ] Strategies: all 5 cards legible; backtest run completes with the stated form values; leaderboard rows open details; accuracy comparison renders.
- [ ] Home: briefing, top trigger, accuracy, leaderboard, engine status all render; all three links navigate.
- [ ] Command palette: navigation + symbols work, no trading actions, no "undefined ·" labels.
- [ ] No order-placement code remains in the repo (grep for `place_order` and broker order calls returns nothing live). No localhost URLs in the built bundle.
- [ ] `/api/health` has no storage warning; AI status matches reality (configured only if a real rotated key is wired).
- [ ] Bot left with no trading state: there is no bot to leave running. Prediction loop state is shown on Home.

## 8. Final report (required)

When everything is done, write a short report: for each section, what you removed, what you kept, what you changed (file + what), what the live verification showed, and what is still not done (if anything). Then update `codebase.md` to match the final code. Then commit, push, and deploy to live — and verify the live site once more after the deploy, because the deploy itself is part of the job.
