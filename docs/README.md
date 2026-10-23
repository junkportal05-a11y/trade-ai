# 📚 ApexTrade / Trade AI Documentation Index

Welcome to the **Trade AI (ApexTrade)** engineering and system documentation. This directory outlines the architecture, data schemas, API routes, and operational playbooks for the trading platform.

---

## 📑 Core Documentation Map

| Document | Purpose | Key Contents |
| :--- | :--- | :--- |
| **[Architecture](architecture.md)** | System Design | 8-tier hierarchy, worker lifecycle, risk governance, fail-open/fail-closed boundaries |
| **[API Map](api-map.md)** | Backend Endpoint Spec | Complete inventory of FastAPI v1 REST and WebSocket endpoints |
| **[Routes](routes.md)** | Route Definitions | Authentication, Broker SmartAPI, Scanner, Simulator, Admin routes |
| **[Database Map](database-map.md)** | Database Schema | SQLAlchemy models, Supabase / SQLite migrations, table relations, indexes |
| **[Dependency Graph](dependency-graph.md)** | Component Topology | Internal import graphs, cross-module couplings, third-party services |
| **[Walkthrough](walkthrough.md)** | User Flow & Walkthrough | End-to-end user journeys: market scan, strategy backtest, trade resolution |
| **[Memory](memory.md)** | Architectural Decisions | Historical architecture decisions, gotchas, lessons learned |
| **[Roadmap](roadmap.md)** | Project Milestones | Active roadmap, pending feature phases, quant improvements |
| **[Incident Runbook](incident-runbook.md)** | Operations & Recovery | Kill-switch activation, broker failovers, degraded state recovery |
| **[Handoff](handoff.md)** | Engineering Handoff | Environment variables, local setup, test execution, deployment steps |
| **[Contributing](CONTRIBUTING.md)** | Contribution Standards | PR workflows, testing requirements, style rules |
| **[Security Policy](SECURITY.md)** | Security & Secrets | Secret handling, token rotations, vulnerability reporting |
| **[Agent Rules](AGENTS.md)** | AI Agent Guidelines | Architectural tiers, safety boundaries, lazy dev rungs |
| **[Claude Config](CLAUDE.md)** | Claude Engineering Rules | System commands, verification flows, code review rules |
| **[License](LICENSE)** | Open Source License | MIT License terms |

---

## 🚀 Quick Commands

### Run Full Test Suite
```bash
pytest
```

### Start Backend Server
```bash
python main.py --reload
```

### Run Frontend Development Server
```bash
cd frontend
npm run dev
```
