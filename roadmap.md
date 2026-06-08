# Feature Roadmap

All planned features organized by priority. Checkboxes are updated as items are completed.

---

## 🔴 Critical — Do Before Sharing With Anyone

- [x] Fix `pass1/pass2/pass3` weak passwords → moved to Render env vars (`PASS_ADMIN` / `PASS_USER1` / `PASS_USER2` / `PASS_USER3`)
- [x] Fix page `<title>frontend</title>` → `ApexTrade — NSE Intraday Signals`
- [ ] Complete Upstox KYC + connect API keys to Render
- [x] Replaced Auth0 SSO with secure local session system (using bcrypt-hashed passwords)

---

## 🟡 High Value — This Week

- [x] Migrate SQLite → Supabase PostgreSQL (Completed)
- [x] Add 30 more high-volatility NSE stocks to watchlist (Completed)
- [ ] PWA install support (`manifest.json` + service worker)
- [x] Fix mobile layout — 3-column breaks on screens < 768px (Completed)
- [ ] Cache AI chat recommendations per symbol (currently re-fetches every symbol switch)
- [ ] Add signal scan warm-up message (users see blank panel on cold start)

---

## 🟢 Polish — When App Is Stable

- [ ] Daily 9:15 AM morning brief — auto-run scan, push top 3 signals as toast
- [ ] Trade journal UI — backend `/api/journal` already built, just needs frontend
- [ ] Telegram bot alerts — notify on high-confidence signals (>75%)
- [ ] Keyboard shortcuts — `B` buy, `S` sell, `1-6` timeframes, `Tab` cycle symbols
- [ ] Price alerts with browser push notifications
- [ ] Screener filters on signals panel (sector, confidence %, R:R, volume)
- [ ] Drawing tools on chart (trend lines, Fibonacci, support/resistance)

---

## 🔵 Advanced — Future

- [ ] Strategy builder — custom IF/THEN rules (IF RSI < 35 AND VWAP AND vol surge > 1.5x → BUY)
- [ ] Multi-portfolio comparison — run 2-3 strategies simultaneously
- [ ] Options chain viewer — CE/PE premiums, OI, IV via nsepython
- [ ] News sentiment per signal stock — fetch headlines, score sentiment, add to signal
- [ ] Backtesting with custom date ranges — not just live auto-scan
- [ ] Android app via Capacitor (wrap existing React as APK)
- [ ] Real broker execution via Upstox order API (live trading, not paper)

---

## 💡 Ideas Backlog | Idea | Notes |
| --- | --- |
| WhatsApp alerts | Use Twilio API for signal notifications |
| Dark/light theme toggle | Low priority — dark theme is the brand |
| Multi-language (Hindi) | Could help with Indian user base |
| Signal confidence history chart | Show how win rate changes over time |
| Sector rotation dashboard | Which sectors are hot today |
| Pre-market scanner | 9:00-9:15 AM gap analysis |
| Expiry day special mode | F&O expiry Thursdays have different patterns |
