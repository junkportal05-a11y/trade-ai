# Test Baseline - ApexTrade

Canonical test-count baseline. Code wins over docs: re-run before citing a
number in any other document. Only the "Current verified run" below may be
quoted as current; everything under History is superseded.

## Current verified run

- Date: 2026-11-02 (UTC)
- HEAD: `a599798` - `fix(frontend): consolidate UI theme tokens and fix JSX structure`
- State: clean detached git worktree at HEAD (no other agents' working-tree edits)
- Backend environment: Python 3.12.10 (`C:\Users\aryan\OneDrive\Desktop\app\projects\trade ai\.venv`), `DATABASE_URL=""`, temp `DB_PATH`, `JWT_SECRET`/`ADMIN_KEY` test values, `PYTHONPATH=backend`
- Backend command: `python -m pytest -q --disable-warnings -o asyncio_mode=auto`
- **Backend result: 296 passed, 0 failed, 0 skipped** across **50 `test_*.py` files** (44.80s)
- Frontend environment: Node/npm with vitest 5.0.5, same clean worktree
- Frontend command: `npm test` (`vitest run`)
- **Frontend result: 46 passed across 9 test files** (1.75s)
- CSRF fixtures (Item 3): `backend/tests/test_csrf.py` **6 passed**; `conftest.auth_client`
  sends the same `X-Requested-With: XMLHttpRequest` header the real `apiFetch`
  sends, and the test file keeps bare clients for its 403 assertions. The
  production `TESTING=1` bypass is gone; no bypass env var is required.
- CI note: `.github/workflows/ci.yml` backend job runs a **24-file subset** of the
  50 backend test files, and the frontend job runs only a production build (no
  vitest). The counts above come from a full local run, not from CI.

## History (superseded - do not cite as current)

| Date | HEAD / commit | Backend | Frontend | Note |
| --- | --- | --- | --- | --- |
| pre-2026-10-26 | - | 233 | 12 | older doc baseline |
| 2026-10-26 | `5256014` | 250 | 32 (7 files) | TAR-15/16 integration |
| 2026-10-27 | `8c74339` | 262 passed / 0 failed | 36 (7 files) | TAR-19 gate |
| 2026-10-27 | `34fa14e` | 296 passed / 48 files | 46 (9 files) | TAR-20 god gate |
| 2026-10-28 | `80e9af2` + `ad56605` | 278 | 46 | Oscar square-off fix |
| 2026-10-28 | `782fc52` | 285 | 46 | Jim SignalResponse |
| 2026-10-28 | `0efee21` | 292 | 46 | Jim paper-loop honesty |
| 2026-10-30 | `69dca49` | 296 | 46 | CSRF fixtures after TAR-21 |

Other historical counts mentioned in older docs (251, 253, 258, 285, 296;
36/46 frontend; 41/48/50 test files; CI 13/15/24 files) are superseded. If a
number is not in the table above and not in "Current verified run", do not
treat it as a verified baseline.

## Re-verification checklist

1. Create a clean worktree at the commit you intend to quote:
   `git worktree add --detach <tmp> HEAD`
2. Backend: `python -m pytest -q --disable-warnings -o asyncio_mode=auto`
   (set `DATABASE_URL=""`, a throwaway `DB_PATH`, and test `JWT_SECRET`/`ADMIN_KEY`;
   never run the suite against a real database).
3. Frontend: `cd frontend && npm test`
4. Record date, HEAD sha, exact passed/failed/skipped counts, and file counts here.
