---
description: "Index of memory topics — key decisions, patterns, gotchas, people context"
date: 2025-09-26
tags:
  - brain
  - index
---

# Memories

Persistent context and knowledge retained across sessions. Each topic lives in its own note — follow the links.

- [[Key Decisions]] — architectural and workflow decisions worth recalling
- [[Patterns]] — recurring patterns and conventions discovered across work
- [[Gotchas]] — things that have bitten before and will bite again
- [[People & Context]] — org structure, teams, review history, dynamics
- [[North Star]] — living goals document, read at session start
- [[Skills]] — custom slash commands and workflows

## Recent Context

-

## Tool Memory Pointers

- Claude Code project memory (`~/.claude/projects/.../memory/MEMORY.md`) is a pointer index that redirects here
- All durable knowledge lives in `brain/` topic notes, never in `~/.claude/`

## Recent Context

- 2026-07-23: Full automated backlog run (tasks 9-32). Part A: Toolchain (Ralph, Caveman, GSD+Ponytail, Obsidian memory). Part B: Engineering (WAL, health checks, integration tests, error boundaries, runbook). Part C: AngelOne session hardening. Part D: Infrastructure audit — verified executors, key separation, validation, JSON logging, rate limiting, circuit breaker already done. Migrated to Alembic. Deleted orphaned quant/ stubs.
- 2026-07-25: Completed remaining backlog tasks 13, 20, 22, 23, 24. Session freshness check fixed with `is_session_valid(session_data)` parameter. Token persistence enhanced with full encryption of all token fields. CLI backtest script upgraded with argparse, validation, JSON output. Daily scheduled refresh implemented with adaptive timing based on token age.