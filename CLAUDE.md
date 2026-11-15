# Workspace Directives: ARTEMIS & Google Agents CLI

## 1. ARTEMIS Mobile & App Testing (`google/artemis`)
- **Activate Artemis MCP (`artemis`)** when application updates, UI refactors, or feature changes occur.
- Available MCP Tools:
  - `mobile_run_task`: Run autonomous task verification
  - `mobile_get_device_state`: Capture real-time screenshots and hierarchy
  - `mobile_inspect_trace`: Inspect execution traces and step diagnostics
  - `mobile_diagnose`: Run doctor checks for ADB, emulator, and environment
- When the task needs it, run verification checks before marking an app update complete.

## 2. Google Agents CLI (`google/agents-cli`)
- **Use `google-agents-cli` when needed** for scaffolding, building, evaluating, or deploying AI agents.
- CLI Tool: `agents-cli` (installed globally via `uv tool install google-agents-cli`)
- Core Skills Installed:
  - `google-agents-cli-workflow`: Lifecycle, model routing, safety gates
  - `google-agents-cli-adk-code`: ADK Python orchestration, tools, and callbacks
  - `google-agents-cli-scaffold`: Scaffolding agent projects (`agents-cli create`)
  - `google-agents-cli-eval`: Rigorous evaluation datasets & LLM-as-judge benchmarks
  - `google-agents-cli-deploy`: Cloud Run and Google Cloud deployments
  - `google-agents-cli-publish`: Gemini registration
  - `google-agents-cli-observability`: Traces and logging


## 3. Hugging Face Deployment ("hg" / "hf")
- **CRITICAL TERMINOLOGY**: When the user mentions **"hg"**, **"hf"**, or **"huggingface"**, it **ALWAYS refers to Hugging Face Spaces** (`https://huggingface.co/spaces/apextrade-core/trade-ai-backend`), **NEVER Mercurial**.
- **WHY DIRECT `git push huggingface main` FAILS**:
  - The local repository's historical commits contain binary artifacts (`palace/chroma.sqlite3`), which triggers Hugging Face's server-side pre-receive hook error: `"Your push was rejected because it contains binary files"`.
- **CANONICAL DEPLOYMENT COMMAND**:
  - Always deploy using the automated script:
    ```bash
    python scripts/deploy_hf.py
    ```
    (Or dry run: `python scripts/deploy_hf.py --dry-run`)
- **MANUAL EQUIVALENT (commit-tree pattern)**:
  ```bash
  git fetch huggingface
  TREE=$(git rev-parse HEAD^{tree})
  HF_TIP=$(git rev-parse huggingface/main)
  DEPLOY_COMMIT=$(git commit-tree $TREE -p $HF_TIP -m "deploy: sync Space tree to main @$(git rev-parse --short HEAD)")
  git push huggingface ${DEPLOY_COMMIT}:refs/heads/main
  ```
- **TARGET REMOTES**:
  - Code changes: `origin` (`https://github.com/junkportal05-a11y/trade-ai.git`)
  - Live backend deployment: `huggingface` (`https://huggingface.co/spaces/apextrade-core/trade-ai-backend`)

## 4. Security Audit Skills (`.opencode/skills/`)
- **Use these before shipping auth, broker, API, or deployment changes.**
- `implementing-api-key-security-controls`: API key entropy, hashing, scoping, rotation.
- `performing-csrf-attack-simulation`: CSRF token and origin validation checks.
- `testing-jwt-token-security`: JWT algorithm, lifetime, revocation, and claim checks.
- `detecting-aws-credential-exposure-with-trufflehog`: secret scanning across repo and CI.
- `sebi-compliance-guard`: paper-only isolation, live-trading arming, broker custody,
  and SEBI algo-trading disclosure invariants.
- Record findings in `ApexTrade/06-Audits-Fixes/SECURITY_AUDIT_REPORT.md`.
