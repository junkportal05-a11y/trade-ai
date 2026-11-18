# Roadmap Implementation Plan

## Phase 1: Polish Features (High Value, Lower Effort)

### 1.1 Trade Journal UI (Backend exists, needs Frontend)
- [x] Create JournalPanel component
- [x] Add journal CRUD API calls to api.js
- [x] Integrate into App.jsx routing/tabs
- [x] Add journal list, create, delete UI

### 1.2 Daily Morning Brief (9:15 AM)
- [x] Add cron/scheduler in frontend (runs check every minute)
- [x] Toast/modal notification system in frontend
- [x] Store brief results with localStorage (once per day)
- [ ] Add user preference for enable/disable (optional enhancement)

### 1.3 Keyboard Shortcuts
- [x] Create useKeyboardShortcuts hook
- [x] Map B/S for buy/sell, 1-6 for timeframes, Tab for symbol cycling
- [x] Integrate into trading panels

### 1.4 Screener Filters on Signals Panel
- [x] Add filter state (sector, confidence%, R:R, volume)
- [x] Add filter UI to SignalsPanel (FilterBar component)
- [x] Apply filters to signals list

### 1.5 Price Alerts with Push Notifications
- [x] Frontend: Alert creation UI (OrderPanel)
- [x] Price checking engine with toast notifications
- [x] localStorage persistence
- [x] Display in HomePanel & BottomConsole
- [ ] Browser Push API integration (for background alerts when tab closed)
- [ ] Service worker for background alerts

### 1.6 Telegram Bot Alerts
- [x] Backend: Telegram bot service (telegram_bot.py)
- [x] Config for bot token/chat ID (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
- [x] Trigger on high-confidence signals (>75%) in signals.py
- [x] Added to .env.example
- [ ] Morning brief via Telegram (optional enhancement)

### 1.7 Drawing Tools on Chart
- [x] Integrate lightweight-charts drawing tools
- [x] Trend lines, Fibonacci, support/resistance
- [x] Persist drawings per symbol (localStorage)

---

## Phase 2: Advanced Features (Higher Effort)

### 2.1 Strategy Builder (IF/THEN Rules)
- [ ] Rule engine schema (conditions + actions)
- [ ] Visual rule builder UI
- [ ] Backend execution engine

### 2.2 Custom Date Range Backtesting
- [ ] Extend backtest API with date range params
- [ ] Frontend date picker for backtest config

### 2.3 Options Chain Viewer
- [ ] NSE option chain API integration
- [ ] CE/PE premiums, OI, IV display

### 2.4 News Sentiment
- [ ] News API integration
- [ ] Sentiment scoring per symbol
- [ ] Add to signal context

### 2.5 Multi-Portfolio Comparison
- [ ] Portfolio schema
- [ ] Comparison dashboard

### 2.6 Real Broker Execution (Live Trading)
- [ ] AngelOne order API integration
- [ ] Live trading mode safeguards
- [ ] Order management UI

### 2.7 Android App via Capacitor
- [ ] Capacitor setup
- [ ] Native build config
- [ ] App store preparation

---

## Implementation Order (Dependencies Considered)

1. **Journal UI** - Backend ready, pure frontend work
2. **Keyboard Shortcuts** - Pure frontend, high UX impact
3. **Screener Filters** - Frontend only, improves Signals panel
4. **Morning Brief** - Needs backend scheduler + frontend toast
5. **Price Alerts** - Full stack (backend checker + frontend + push)
6. **Telegram Bot** - Backend service + config
7. **Drawing Tools** - Chart library integration
8. **Custom Date Backtest** - API extension
9. **Strategy Builder** - Complex, new rule engine
10. **Options Chain** - New data source
11. **News Sentiment** - External API
12. **Multi-Portfolio** - New data model
13. **Real Broker Execution** - High risk, needs careful safeguards
14. **Android/Capacitor** - Platform expansion

---

## Quick Wins (Can do in parallel)
- Move LICENSE, CONTRIBUTING.md, SECURITY.md to root
- Add CHANGELOG.md
- Add .github/CODEOWNERS