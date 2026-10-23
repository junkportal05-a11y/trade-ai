# Project Brain – Trade AI App

## Core Vision
- Build an automated trading platform that learns market dynamics and executes strategies with minimal latency.
- Emphasize **immutable data flow**, **composable modules**, and **clear separation of concerns**.

## Backend Modules (caveman package)
| Module | Purpose | Key APIs |
|--------|---------|----------|
| **weight_prediction** | Predicts asset weight / allocation based on statistical models. | `predict_weights()` |
| **crossover_points** | Detects price crossover events that trigger strategy switches. | `find_crossovers()` |
| **signal_generator** | Converts raw data signals into actionable trade signals. | `generate_signal()` |
| **bot_forwarder** | Routes generated signals to execution broker APIs. | `forward_signal()` |
| **instruction_user** | Provides user-facing UI for strategy configuration and monitoring. | `update_ui_state()` |

### Backend Public API Surface
- **centroids** – Clustering functions that group assets for downstream analysis.
- **query_groups** – Retrieves pre‑defined signal‑group mappings.
- **query_corrections** – Adjusts signals based on rule‑base corrections.

## Navigation Map
- **data records**: CSV descriptors for:
  - `W_merge_timeliness.csv`
  - `strategy_invocation_timeliness_apex_tables.csv`
  - `bot-trade.csv`
  - `trade_connection_status.csv`
- **Database**: Core schema definitions stored in `database-map.md` and supporting DB scripts (`db.py`, `journal.py`).

## Data & Config Files
- **CSV‑based records** for auditability:
  - `W_merge_timeliness.csv` – merges weights with timestamps.
  - `strategy_invocation_timeliness_apex_tables.csv` – logs per‑strategy latency.
  - `bot-trade.csv` – raw bot execution log.
  - `trade_connection_status.csv` – connection health of broker APIs.
- **JSON/Tokens**: Design‑token files for consistent UI theming.
- **CSV token generations**: `token-architecture.md`, `semantic-tokens.md`.

## Architectural References
- **Architecture Review Process** – documented in `.claude/agents/architect.md`.
- **Architectural Principles** – outlined in `.claude/agents/architect.md`.
- **ADRs (Architecture Decision Records)** – stored under `ADRs/` within the vault.

## Frontend Overview (React)
- **Core Layout**: `App.jsx` (root), `HomePanel.jsx`, `PredictionsPanel.jsx`, `PerformancePanel.jsx`, `SignalsPanel.jsx`, `TradeLogPanel.jsx`.
- **Key Components**:
  - **AccountPanel.jsx** – user auth & settings.
  - **BotControlPanel.jsx** – start/stop, status, logging.
  - **StrategySelector.jsx** – select active strategies.
  - **BacktestRunner.jsx** – historic simulation harness.
  - **ScannerPanel.jsx** – live market scanner.
- **Hooks**:
  - `useMarketData.js` – market status, live price feeds.
  - `useHistory()` – fetches historical orders.
- **Styling**: Custom fonts & design tokens located under `.claude/skills/ui-styling/`.

## Critical Utility Scripts
- **data‑generation**: `generate.py`, `render-html.py`, `search.py` (various sub‑directories).
- **CLI Tools**: `install.js`, `run.js`, `verify_repo.py` – used for environment bootstrapping & integrity checks.
- **Testing Utilities**: `verify_manifests_and_syntax.cjs`, `test_square_off.py` – ensure compliance with coding standards.

## Design‑System Tokens (used across UI)
- **Color Palette**: `primitive-tokens.md`, `semantic-tokens.md`.
- **Component Tokens**: `component-specs.md`.
- **Token Architecture**: `token-architecture.md`.
- **Semantic Tokens**: `semantic-tokens.md`.

## Workflow & Governance
- **Commit Message Format** – `type: description` (Co‑Authored‑By: Claude).
- **Code Review** – `code-reviewer` agent runs automatically post‑push.
- **Testing Pipeline** – `tdd-guide` enforces write‑tests‑first; target coverage ≥ 80 %.
- **Documentation** – Auto‑generated via `doc-updater` and hand‑maintained markdown in `templates/` and `daily/`.

## Data Flow (simplified)
1. **raw market feeds** → `useMarketData` hook → `signals.py`.
2. **signals** → `signal_generator` → `query_corrections` → `bot_forwarder`.
3. **bot_forwarder** → Broker API (`broker.py`, `angelone_feed.py`).
4. **Execution** → `trade_connection_status.csv` updates → `W_merge_timeliness.csv`.
5. **Feedback Loop** → `weight_prediction` updates next signal weights.

## Action Items (TODO)
- [ ] Audit all CSV records for schema compliance.
- [ ] Validate token consistency across UI components.
- [ ] Extend `weight_prediction` with ensemble model testing.
- [ ] Add unit tests for `bot_forwarder` error handling.
- [ ] Generate updated `token-architecture.md` after any palette change.