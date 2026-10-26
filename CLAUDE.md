# Workspace Directives: ARTEMIS & Google Agents CLI

## 1. ARTEMIS Mobile & App Testing (`google/artemis`)
- **Always activate and use Artemis MCP (`artemis`)** whenever any application update, UI refactor, or feature change occurs.
- Available MCP Tools:
  - `mobile_run_task`: Run autonomous task verification
  - `mobile_get_device_state`: Capture real-time screenshots and hierarchy
  - `mobile_inspect_trace`: Inspect execution traces and step diagnostics
  - `mobile_diagnose`: Run doctor checks for ADB, emulator, and environment
- Never mark an app update complete without running verification checks.

## 2. Google Agents CLI (`google/agents-cli`)
- **Use `google-agents-cli` every time** when scaffolding, building, evaluating, or deploying AI agents.
- CLI Tool: `agents-cli` (installed globally via `uv tool install google-agents-cli`)
- Core Skills Installed:
  - `google-agents-cli-workflow`: Lifecycle, model routing, safety gates
  - `google-agents-cli-adk-code`: ADK Python orchestration, tools, and callbacks
  - `google-agents-cli-scaffold`: Scaffolding agent projects (`agents-cli create`)
  - `google-agents-cli-eval`: Rigorous evaluation datasets & LLM-as-judge benchmarks
  - `google-agents-cli-deploy`: Cloud Run and Google Cloud deployments
  - `google-agents-cli-publish`: Gemini registration
  - `google-agents-cli-observability`: Traces and logging
