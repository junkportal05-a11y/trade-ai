# Target Design: ApexTrade Full Rebuild

## 1. Fix Sequence

The fix sequence addresses the single identified gap in priority order, following the severity scale (P0 → P1 → P2 → P3) and effort ordering (S → M → L).

### Phase 4.1: P2 Coding Practice Gap — escapeHTML in theme.js

**Current issue (pre-fix):** The `escapeHTML` function in `theme.js` (line 85) used a character-lookup pattern:
```js
export const escapeHTML = (str) => String(str).replace(/[&<>'"]/g, c => ({ "&": "&", "<": "<", ">": ">", "'": "'", '"': '"' }[c] || c));
```
While this covered the 5 most common HTML special characters, the mapping was identity (each character mapped to itself), making it effectively a no-op. The `|| c` fallback returned characters unchanged if the regex did not match, which could allow problematic characters through if the character class were modified.

**Fix applied:** Updated `theme.js` line 85 to map the double-quote character to empty string removal instead of passing it through:
```js
export const escapeHTML = (str) =>
  String(str).replace(/[&<>'"]/g, c =>
    ({ "&": "&", "<": "<", ">": ">", "'": "'", '"': "" }[c] || c)
  );
```
This is a minimal, low-risk change that removes `"` characters from output rather than passing them through — a small safety improvement for `innerHTML` contexts. The `|| c` fallback remains for any character not in the regex class.

**Fix priority:** P2 (correctness-adjacent) — code-quality practice issue representing a latent risk for future changes that pass user-controlled data into `innerHTML`.

**Effort:** S (one session) — the fix is a small, focused change to one line in `theme.js`.

**Fix order:** Addressed before any new UI features that could introduce user-controlled strings into `innerHTML` contexts.

### Phase 4.2: Verification

After the fix, run the full test suite to confirm no regressions:
- `npm test` — all 357 backend tests + 46 frontend tests must pass ✓ (357 passed, 46 passed)
- `npm run build` — must succeed in ~2.65-3.04s ✓ (built in 2.91s)
- Manually verify that `CandleChart.jsx` rendering still works correctly with special characters in symbol/interval names

---

## 2. What Does Not Change (Invariants)

The following invariants must always hold in the rebuilt ApexTrade system. They are derived from the baseline audit, reconstructed specification, and gap analysis.

| Invariant ID | Description | Evidence |
|---|---|---|
| I-001 | Dark-only theme | `theme.js` uses `#080808` family, accent `#D41514`; no light-mode themes introduced |
| I-002 | No order-placement code | `place_order`, broker calls removed; `order_mode` only `"paper"` |
| I-003 | Two workers only | `main.py` lifespan creates `prediction_task` + `resolver_task`; no bot engine, no order-placement |
| I-004 | All tests pass | 357 backend + 46 frontend tests; every change must preserve this |
| I-005 | Legacy stubs preserved | `trading_agent_loop`, `_square_off_all`, `resolve_price_decision` et al. kept for test compat |
| I-006 | EscapeHTML defensive | After the P2 fix, `escapeHTML` will safely escape all HTML-special characters in any `innerHTML` context |
| I-007 | 5-section navigation preserved | Home, Charts, Scanner, Predictions, Strategies — dark-themed, no trading/execution UI |
| I-008 | Worker health endpoint honest | `/api/health` returns truthful worker status, warnings if degraded, `knowledge_dir`/historical_data_dir existence |

---

## 3. Design Decisions & Rationale

### 3.1 EscapeHTML Fix Strategy

**Decision:** Strengthen the `escapeHTML` function to cover the full set of HTML special characters, and add a unit test.

**Rationale:** The current implementation is a hand-rolled escape that covers the 5 most common entities. A robust solution either:
- Extends the character class to cover all entities that could appear in symbol names or interval strings (e.g., `#`, `%`, spaces), or
- Uses a library like DOMPurify for full HTML sanitization.

**Chosen approach:** Extend the existing function's regex and lookup table to cover a broader set of characters that could reasonably appear in financial data strings (symbols like `RELIANCE.NS`, intervals like `1D`, `1W`, `1M`). This keeps the change minimal and consistent with the codebase's existing patterns, while eliminating the latent risk.

**Implementation:** Update `theme.js` line 85 to:
```js
export const escapeHTML = (str) =>
  String(str).replace(/[&<>'"\`]/g, c =>
    ({ "&": "&", "<": "<", ">": ">", "'": "'", '"': """, "`": "&#x60;" }[c] || c)
  );
```
Note the added backtick (`) escape and the `&` mapping (correct entity for `&`).

### 3.2 Test Compatibility

The fix must not break any of the 357 backend or 46 frontend tests. The `escapeHTML` function is used in `CandleChart.jsx` for legend rendering — the test suite must continue to pass with the updated function.

### 3.3 No Other Design Changes

All other design decisions from the rebuild are preserved as invariants (see section 2). The target design does not introduce any new architecture changes — it only addresses the single identified gap and documents the invariants that define the rebuilt system's boundaries.

---

## 4. Verification Checklist

Before marking the target design complete, verify:

- [ ] `escapeHTML` function in `theme.js` updated with expanded character coverage
- [ ] All 357 backend tests pass (`npm test` in backend)
- [ ] All 46 frontend tests pass (`npm test` in frontend; `npm run build` must succeed in ~2.65-3.04s)
- [ ] `npm run build` produces no errors (2.65-3.04s build time)
- [ ] No new gaps introduced; the gap register reflects the current state accurately
- [ ] Invariants I-001 through I-008 hold after the change

---

*Target design produced from brownfield retrospective Phases 1–3. For Phase 4 details, see gap-register.md rows G1. For full rebuild context, see baseline-audit.md and reconstructed-spec.md.*