---
description: "Recurring patterns and conventions discovered across work — architecture, naming, tooling, and implementation patterns"
date: 2026-07-19
tags:
  - brain
---

# Patterns

- **Immutable updates** — never modify objects in place; always return new copies (see [[Key Decisions]]).
- **Single responsibility** — split large files >500 lines by concept.
- **Explicit state flow** — make state transitions clear in code comments.
- **Domain‑driven naming** — use finance terms (`signal`, `instrument`, `position`) for variables and functions.
- **Versioned APIs** — keep public interfaces stable; deprecate with prefix `v1_`.
- **Reusable components** — extract common logic into pure utility functions; reference via import.
- **Verification‑first** — write tests before implementing core logic.

## Related

- [[Key Decisions]] — decisions that enforce these patterns
- [[Gotchas]] — pitfalls when patterns are broken
- [[North Star]] — strategic direction
