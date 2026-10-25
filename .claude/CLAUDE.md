# graphify
- **graphify** (`.claude/skills/graphify/SKILL.md`) - any input to knowledge graph. Trigger: `/graphify`
When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

# ARTEMIS Mobile & App Testing (google/artemis)
- Use Artemis MCP server (`artemis`) whenever any app or UI update occurs.
- Key tools: `mobile_run_task`, `mobile_get_device_state`, `mobile_inspect_trace`, `mobile_manage_task`, `mobile_diagnose`.
- Always verify live UI flows and device states before finalizing updates.

# Google Agents CLI (google/agents-cli)
- Use `google-agents-cli` commands (`agents-cli`) and skills every time when building, scaffolding, evaluating, and deploying agents:
  - `google-agents-cli-workflow`: Agent lifecycle & development flow
  - `google-agents-cli-adk-code`: ADK Python patterns, tools, state
  - `google-agents-cli-scaffold`: Project scaffolding
  - `google-agents-cli-eval`: Evaluation metrics, datasets, LLM-as-judge
  - `google-agents-cli-deploy`: Deployment to Cloud Run & Google Cloud
  - `google-agents-cli-observability`: Cloud Trace & monitoring

