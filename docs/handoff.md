# Handoff

## Goal
Add a predictions stats endpoint in the backend and guard front-end fetches with the IntroSplash ready flag to avoid CORS issues on Vercel (keep `VITE_API_URL` empty).

## Current State
- Backend `/api/predictions/stats` endpoint exists and is correct (`backend/app/api/v1/predictions.py`, lines 36–69).
- Router registration confirmed: `api_router.include_router(predictions.router)` in `backend/app/api/v1/router.py:15`.
- Front-end `backendReady` flag added and wired into fetch guards (`frontend/src/App.jsx`).
- `VITE_API_URL` is empty in `frontend/vercel.json` (lines 14 & 19) — same-origin proxy to Hugging Face Space backend, no edge CORS.
- Verified consistent with hand-off docs; user approved.

## Active Files Working On
- backend/app/api/v1/predictions.py
- backend/app/api/v1/router.py
- frontend/src/App.jsx
- frontend/vercel.json

## Changes Made
- Added `backendReady` state initialized `false` (`App.jsx:1733`).
- `handleWokenUp` now sets `setBackendReady(true)` once IntroSplash signals the backend is up (`App.jsx:2330`).
- `fetchMarketBrief` and `fetchPredictionStats` early-return when `!backendReady` (`App.jsx:1864`, `:1877`).
- The mount `useEffect` only calls those fetchers when `loggedIn && backendReady`, with `backendReady` in the dep array (`App.jsx:1886–1891`).
- Confirmed predictions stats route + router inclusion already present (no new backend code needed).
- Confirmed `VITE_API_URL` empty in `vercel.json` (env + build.env) to prevent CORS.

## Failed Attempts
- (None — route, router, and Vercel config were already correct; only the front-end guard was missing and has been added.)

## Next Steps
- [x] Local smoke test: `curl http://localhost:8000/api/predictions/stats` returns `{win_rate, avg_error, resolved_predictions}`.
- [x] Local smoke test: `curl -i -X OPTIONS "http://localhost:8000/api/scan"` verifies that `Access-Control-Allow-Credentials: true` is properly set in the backend CORS configuration.
- [x] Ran `npm run build && npm run preview` locally with `VITE_API_URL` unset and confirmed no CORS errors.
- Update this file after any further task.
