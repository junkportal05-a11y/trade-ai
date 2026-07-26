# Contributing to ApexTrade Quant Server

Thank you for your interest in contributing to ApexTrade! We welcome contributions from developer, quantitative analyst, and trader communities.

---

## Code of Conduct

Please help us keep ApexTrade an inclusive, respectful, and productive project. Be welcoming, treat fellow contributors with respect, and focus on constructive feedback.

---

## How Can I Contribute?

- **Reporting Bugs**: Search existing issues first. If not found, open a bug report with clear reproduction steps.
- **Suggesting Features**: Submit a feature request describing the use case, proposed implementation, and trade-offs.
- **Improving Documentation**: Fix typos, improve setup guides, or add trading strategy references.
- **Submitting Code**: Fix open bugs, add test coverage, or implement quantitative indicators/frontend components.

---

## Local Development Workflow

### Prerequisites
- **Python**: `3.10+`
- **Node.js**: `18+` (npm 9+)
- **Git**

### 1. Fork & Clone
```bash
git clone https://github.com/YOUR_USERNAME/trade-ai.git
cd trade-ai
```

### 2. Backend Setup (`/backend`)
```bash
cd backend
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Run backend test suite:
```bash
pytest
```

Run dev server:
```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup (`/frontend`)
```bash
cd ../frontend
npm install
npm run dev
```

Check build:
```bash
npm run build
```

---

## Git Workflow & Branch Naming Conventions

Create feature or bugfix branches from `main`:

- `feature/short-description` (e.g. `feature/vwap-band-indicator`)
- `fix/short-description` (e.g. `fix/cors-proxy-rewrite`)
- `docs/short-description` (e.g. `docs/update-contributing-guide`)

Commit messages should follow standard conventional commit formats:
- `feat: add VWAP standard deviation bands`
- `fix: handle WebSocket reconnect backoff`
- `docs: improve backend setup instructions`
- `test: add unit tests for backtest engine`

---

## Pull Request Guidelines

1. **Keep PRs Focused**: Avoid mixing unrelated fixes or refactoring into one PR.
2. **Run Tests Locally**: Ensure `pytest` passes and `npm run build` succeeds cleanly without errors.
3. **Update Documentation**: If your PR introduces new environment variables or API endpoints, document them in `README.md` or relevant docs.
4. **Fill Out PR Template**: Provide a summary of changes, manual testing performed, and any breaking changes.

Thank you for helping make ApexTrade better!
