# Brownfield Retrospective: ApexTrade Full Rebuild

**Slice:** `projects/trade.ai` (entire ApexTrade codebase — frontend + backend)
**Entry Point:** User's rebuild prompt (`apextrade-rebuild-prompt-2026-11-19.md`)
**Perimeter:** All frontend (`frontend/src/`) and backend (`backend/`) code modified during the rebuild
**Blast Radius:** 20+ files, ~5,000 lines changed
**Current Phase:** 0 - Entry point selected, starting Phase 1

---

## Gap Register

| ID | Axis | Gap | Evidence | Forward Fix | Severity | Effort | Status |
|----|------|-----|----------|-------------|----------|--------|--------|
| G1 | Coding practice | escapeHTML escaping in theme.js | The `escapeHTML` function in `theme.js` (line 85) uses a character lookup pattern that could allow unescaped characters through if the regex character class is incomplete or modified. Used in `CandleChart.jsx` to escape symbol/interval before `innerHTML` insertion. | Fix applied: updated `escapeHTML` to properly map HTML special characters to entities (P2, S effort). Verified: all 357 backend + 46 frontend tests pass; `npm run build` succeeds in 2.91s. | P2 | S (one session) | Done |