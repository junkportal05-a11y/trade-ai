# ApexTrade V3 Day-by-Day Task Sequence

Source: `[Certain] The phases are well-struc.txt`

Rule: do not skip ahead. Each day starts only after the previous day is verified.

## Current Gate Before Phase 0

- [ ] Supabase PostgreSQL connected and `DATABASE_URL` set
- [x] AngelOne SmartAPI integrated as the only market-data broker path
- [x] `backend/trading_agent.py` exists
- [x] `backend/trading_agent.py` verified running autonomously in a real app session

Verification note, 2026-06-17 IST: local backend started on `127.0.0.1:8765`, returned HTTP 200, and logged `[trading_agent] Autonomous agent loop started.` It correctly stayed idle because the market was closed.

## Week 1 - Phase 0 Infrastructure

### Day 1 - Data Integrity Engine

- [x] Replace candle-only `backend/data_validator.py` with resolved-trade validation
- [x] Add `data_quality` table creation to database startup
- [x] Add database-wide `/api/data/confidence` response
- [ ] Verify with real resolved trades after Supabase is connected

### Day 2 - Data Quality UI Lock

- [ ] Update performance/analytics UI to call `/api/data/confidence` first
- [ ] If confidence is below 90, show a red warning banner
- [ ] Blur win rate, profit factor, EV, and other analytics
- [ ] Show only the failures list until data quality is fixed

### Day 3 - VWAP Veto

- [ ] Confirm VWAP gives no bull/bear scoring points
- [ ] Add a single reusable `vwap_veto(price, vwap, direction)` helper
- [ ] Apply the 0.998/1.002 tolerance from the directive
- [ ] Log clear cancellation reasons for blocked BUY/SELL signals

### Day 4 - Pessimistic Resolver

- [ ] Add `resolve_candle_pessimistic()` to `backend/backtest_engine.py`
- [ ] If target and stop are both hit in one candle, resolve as LOSS
- [ ] Wire the helper into historical backtest exits
- [ ] Add tests for BUY and SELL same-candle stop/target conflicts

### Day 5 - Phase 0 Verification

- [ ] Run backend tests
- [ ] Run one local data-confidence check
- [ ] Confirm Week 1 Day 1-4 items work together
- [ ] Update this file with completed verification notes

## Week 2 - Phase 1 Engines

### Day 6 - Market Regime Engine

- [ ] Build `backend/market_regime.py`
- [ ] Use only TRENDING, RANGING, VOLATILE, UNCLEAR
- [ ] Return no trades when regime is UNCLEAR

### Day 7 - Trade Quality Score

- [ ] Align `backend/trade_quality.py` with the directive formula
- [ ] Reject trades below 70
- [ ] Add ELITE, STRONG, WATCHLIST, REJECT tiers

### Day 8 - ATR Calibrator

- [ ] Build `backend/atr_calibrator.py`
- [ ] Test 1.0, 1.25, 1.5, and 2.0 ATR stop multiples
- [ ] Store selected multiple in the database
- [ ] Make `signals.py` read the calibrated multiple at startup

### Day 9 - Capital Manager

- [ ] Align `backend/capital_manager.py` with quality-score sizing rules
- [ ] Add 5 percent drawdown size reduction
- [ ] Add 10 percent drawdown no-trade kill switch

### Day 10 - AngelOne Verification

- [ ] Verify login, historical candles, quote fetch, and broker session restore
- [ ] Confirm Upstox is not used anywhere in live paths

## Week 3 - Autonomous Agent

### Day 11 - Trading Agent Runtime

- [ ] Verify `trading_agent.py` runs 9:15 AM to 3:20 PM IST
- [ ] Ensure it respects quality, confidence, drawdown, and regime gates

### Day 12 - Weekly Review Generator

- [ ] Generate Sunday 6:00 PM IST weekly review data
- [ ] Save output to database
- [ ] Expose `/api/reviews/latest`

### Day 13 - Monthly Report Endpoint

- [ ] Build `POST /api/reports/monthly`
- [ ] Return PDF or JSON with the directive metrics

## Week 4 - Validation

### Day 14 - Paper Trade Run

- [ ] Run 500 paper trades
- [ ] Keep all resolved trades in persistent storage

### Day 15 - Validation Criteria

- [ ] Data Confidence Score at least 90 for 30 consecutive days
- [ ] Profit Factor at least 1.5
- [ ] Expected Value greater than 0
- [ ] Max Drawdown below 10 percent
- [ ] At least 100 TRENDING trades
- [ ] At least 50 RANGING trades
- [ ] Calibration Error below 10 percent

### Day 16 - Phase 2 Decision

- [ ] If all validation criteria pass, begin micro-capital phase
- [ ] If any one criterion fails, stay in Phase 1
