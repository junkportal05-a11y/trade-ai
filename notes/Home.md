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

**2026-10-27 — Docs sync (TAR-19, v6.1.0, HEAD 8c74339):** Security & honesty pass folded into the merged tree — CSRF now guards session-authenticated mutating routes only (`GET /api/bot/status` / `/api/bot/trades` CSRF-free; deliberate exemptions `/api/login` + `/api/logout` for session lifecycle and `/api/admin/*` via X-Admin-Key header), `GET /api/strategies` reads the real DB store with `data_source` 'db'/'presets' (presets-only fallback) honouring `active_only`, `DELETE /api/predictions/{id}` is session-user-scoped (404 for other users' records, no leak), scanner `/api/signals` + `/api/scan` return a `gates` rejection breakdown, `/api/chat` falls back to a deterministic heuristic labelled `source: 'heuristic'` when Gemini is unconfigured, analytics `avg_error` is a real MAE in Rs over resolved predictions, auth failures are always 401 never 422 — tests: 262 pytest (CI gate runs 15 files), 36 vitest; version stays 6.1.0.

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
