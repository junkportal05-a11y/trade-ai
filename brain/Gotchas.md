---
description: "Things that have bitten before and will bite again — pitfalls, edge cases, testing traps"
date: 2026-07-19
tags:
  - brain
---

# Gotchas

- **Immutable data leaks** – accidental mutation of shared state can cause subtle bugs.
- **Race conditions** in async callbacks when using global variables.
- **Version drift** – forgetting to bump API version in integration points.
- **Missing frontmatter** – notes without date or tags are ignored by auto‑indexing.
- **Over‑linking** – creating circular dependencies that break graph queries.
- **Stale auto‑generated indexes** – need manual refresh after bulk edits.
- **Tag duplication** – using variations of the same tag (`#project` vs `#Project`) fragments search results.
- **Large embeds** – embedding big PDFs can bloat the vault and slow rendering.

## Related
See also [[Key Decisions]], [[Patterns]], and [[North Star]] for deeper context on the patterns and decisions that give rise to these gotchas.

## Mitigations

1. Use immutable patterns and copy‑on‑write data structures.  
2. Keep a shared `constants.md` for version numbers.  
3. Validate frontmatter completeness with pre‑commit hook (or manual check).  
4. Review links before adding to prevent cycles.  
5. Run `graphify update` after bulk changes to rebuild indexes.