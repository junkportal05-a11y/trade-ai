---
date: 2026-07-19
description: ApexTrade vault entry point — embedded Base views, quick links to active work, brain, and org context.
tags:
  - index
  - moc
type: home
---

# ApexTrade — Home

Vault entry point for the ApexTrade trading-AI project. Use the embedded Bases views below for navigation; everything else links out from there.

+ [[North Star]] — current goals and focus areas

## Changelog

**2026-10-30 — Learn/Verify/Deploy run (TAR-21 deploy, v6.1.1, HEAD lineage `2d22822`):** Full codebase re-read from local code (code wins over docs). Architecture: single-code gate (`POST /api/login` username="code" → JWT `apt_token` → `GET /api/auth/verify`; only `/api/health`, `/api/prices`, `/ws/prices` public; everything else `SessionDep`/`TraderDep`/`AdminDep` + unconditional CSRF on mutations). Verified: pytest **296/0** (after test-harness alignment for `fc8f26a`'s unconditional CSRF — 41 tests predated it), vitest **46/46**, build 0 errors, verify **401/401/200 never 422** (note: verify is rate-limited 5/min → 429 → honest code-screen fallback), prod-build browser checks 3/3 reloads clean, Try Again recovers without loop/bypass both auth states, `T.gold/yellow/blueDim/blueGlow` 0 refs, broker Fernet confirmed on submit path. Deployed: **HF Space live** (`adbcf9c`; had to untrack binary `palace/` for xet, and set Space var `ENVIRONMENT=production` after the 7a391e3 boot guard correctly refused `DATABASE_URL`+unset-ENVIRONMENT — Space had silently run in default-dev mode before). **Vercel frontend already current** (live bundle byte-identical to fresh build of source; frontend untouched). Live incognito probes: code screen only, no terminal/admin leak, 3/3 reloads, `errors: []`. Discrepancies: legal pages (Landing/Terms/Privacy/Disclaimer) exist but are imported nowhere — not reachable from the live site; CORS is allow-list-only since `fc8f26a` (no `localhost:*` regex). Correct-code→terminal step is owner-tested. No secrets in any commit or doc (`backend/.env*` gitignored, checked).

## Dashboards

![[Work Dashboard.base]]
![[Recently Touched.base]]

## Context

- [[brain/North Star|North Star]] — current goals and focus areas
- [[work/Index|Work Index]] — active projects and archive
- [[org/People & Context|People & Context]] — team and org knowledge
- [[perf/Brag Doc|Brag Doc]] — wins and evidence

## More Views

![[Incidents.base]]
![[People Directory.base]]
![[1-1 History.base]]
![[Review Evidence.base]]
![[Competency Map.base]]
![[Templates.base]]
