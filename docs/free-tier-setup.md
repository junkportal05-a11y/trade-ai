# APEXTRADE AI — Free-Tier Deployment Guide (revised, v6.1.1)

> **Status**: Revised 2026-10-28 (TAR-20 Task 13). The original guide targeted a
> Cloud Run deployment; the **shipped deployment reality** is a Hugging Face
> Spaces Docker backend + Vercel frontend + Supabase Postgres. The Cloud Run
> path (`scripts/deploy_cloud_run.sh`) still exists as a legacy alternative —
> the generic steps and the environment-variable reference below apply to
> either host.

---

## 🏗️ Shipped architecture

```
┌─────────────────┐     ┌──────────────────────┐     ┌──────────────────┐
│   Frontend      │────▶│  Backend API          │────▶│  Postgres        │
│  (Vercel,       │     │  (HF Spaces Docker    │     │  (Supabase/Neon, │
│   free tier)    │     │   root Dockerfile,    │     │   free tier)     │
│                 │     │   port 7860)          │     │                  │
└─────────────────┘     └──────────┬───────────┘     └──────────────────┘
                                   │
                     ┌─────────────┼─────────────┐
                     ▼             ▼             ▼
             ┌─────────────┐ ┌──────────┐ ┌──────────────┐
             │ Gemini      │ │ AngelOne │ │ Optional:    │
             │ 2.0 Flash   │ │ SmartAPI │ │ Redis/Sentry │
             │ (free tier) │ │ (paper)  │ │ (free tier)  │
             └─────────────┘ └──────────┘ └──────────────┘
```

- **Backend container**: repo-root `Dockerfile` (multi-stage, python:3.12-slim,
  non-root user, `PORT` default 7860). CI builds it and smoke-runs
  `GET /api/health/ping` on every push (`.github/workflows/ci.yml`).
- **Health endpoints**: `GET /api/health` (diagnostic),
  `GET /api/health/ping` (lightweight liveness), `GET /api/ready`.
- **Docs UI** (`/docs`, `/redoc`, `/openapi.json`) is served only outside
  `ENVIRONMENT=production` (v6.1.1 hardening, `7a391e3`).

---

## 🔑 Free service credentials

| Service | Cost (free tier) | Get it | Env var |
|---|---|---|---|
| Google AI Studio (Gemini 2.0 Flash) | $0 | https://aistudio.google.com/app/apikey | `GEMINI_API_KEY` |
| Supabase (or Neon) Postgres | $0 (500MB) | supabase.com → connection string | `DATABASE_URL` |
| Upstash Redis (rate limiting) | $0 (10K req/day) | upstash.com → Redis database | `UPSTASH_REDIS_URL` |
| Hugging Face Spaces | $0 | https://huggingface.co/spaces | manages Docker backend |
| Vercel | $0 | https://vercel.com/new | `VITE_API_URL` (frontend env) |
| Sentry (optional) | $0 | sentry.io → DSN | `SENTRY_DSN` |

---

## 🚀 Deployment steps (shipped path: HF Spaces + Vercel)

1. **Supabase/Neon Postgres** — create the project, copy the connection
   string. Optional locally: `DATABASE_URL="postgresql://..." python -m alembic upgrade head`
   (migrations also auto-run at startup).
2. **HF Space backend** — Space → **Settings → Repository secrets** → add the
   secrets from the table below. The Space builds the root `Dockerfile`
   automatically on push (set `App port` = 7860 in the Space metadata).
3. **Vercel frontend** — import the repo, root directory `frontend`, add
   `VITE_API_URL` = the Space URL (`https://apextrade-core-trade-ai-backend.hf.space`).
4. **Verify** —
   ```bash
   curl -fsS https://apextrade-core-trade-ai-backend.hf.space/api/health/ping
   # then authenticate and probe one protected route;
   # missing/invalid tokens must return 401 (never 422)
   ```

### 6.1.1 guardrails to honor at deploy time (`7a391e3`)

- Set **`ENVIRONMENT` explicitly** whenever `DATABASE_URL` is set — the app
  refuses to boot with a database configured but the environment unset.
- `DEBUG=false` outside development (the app refuses otherwise).
- Invalid `FERNET_KEYS` **fail startup** in production/staging — rotate keys
  properly (see `backend/app/core/security-rotation.md`), never paste a stale one.
- **Paper only**: `live_trading_armed` is refused outright (SEBI 2025
  algo-trading review gate). Never attempt to arm live trading in any host.

---

## 🔐 Secrets checklist

- [ ] All secrets live in HF Space secrets / Cloud Run Secret Manager — never in code or committed files (`backend/.env*` is gitignored by intent)
- [ ] `ENVIRONMENT=production` set explicitly
- [ ] `JWT_SECRET`, `FERNET_KEYS`, `ADMIN_KEY` are strong random values (generate below)
- [ ] Database URL uses SSL (`sslmode=require`)
- [ ] `ALLOWED_ORIGINS` restricted to the Vercel frontend domain(s)
- [ ] Rate limiting backend configured (Upstash Redis) if deployed multi-instance

**Generate secrets locally**:

```bash
# JWT_SECRET (32-byte hex)
openssl rand -hex 32

# FERNET_KEYS (url-safe base64)
openssl rand -urlsafe 32

# ADMIN_KEY (24-byte hex)
openssl rand -hex 24
```

---

## 💰 Cost summary

| Service | Free tier limit | Cost |
|---|---|---|
| HF Spaces (Docker, free CPU) | per-Space limit | $0 |
| Vercel | 100GB bandwidth | $0 |
| Supabase/Neon | 500MB DB | $0 |
| Gemini 2.0 Flash | 1M tokens/day | $0 |
| Upstash Redis | 10K req/day | $0 |
| Sentry (optional) | 5K errors/month | $0 |
| Cloud Run (legacy path) | 2M req/mo | $0 |
| **Total** | | **$0/month** |

---

## 🛠️ Local development

```bash
# Backend
cd backend
python -m venv .venv            # or cp .env.example .env and edit keys
.venv\Scripts\activate          # Windows | source .venv/bin/activate (POSIX)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 7860

# Frontend
cd frontend
npm install
npm run dev
```

## 📝 Environment variable reference

| Variable | Required | Description |
|---|---|---|
| `ENVIRONMENT` | Yes when `DATABASE_URL` set | `development` \| `staging` \| `production` (boot refuses otherwise) |
| `DATABASE_URL` | Optional | Postgres URL; unset ⇒ sanctioned local SQLite fallback |
| `GEMINI_API_KEY` | No | Unset ⇒ `/api/chat` answers with the honest deterministic `"heuristic"` fallback |
| `UPSTASH_REDIS_URL` | No | Distributed limiter backend |
| `SENTRY_DSN` | No | Error tracking |
| `JWT_SECRET` | Yes (prod) | 32-byte hex for session JWTs |
| `FERNET_KEYS` | Yes (prod) | URL-safe base64 list; invalid entries fail startup |
| `ADMIN_KEY` | Yes (prod) | `X-Admin-Key` header value for `/api/admin/*` |
| `PASS_ADMIN`/`APP_PASSWORD` | Yes (prod) | The single access code (bcrypt-hashed at runtime) |
| `ALLOWED_ORIGINS` | No | Comma-separated frontend origins |
| `PORT` | No | Server port (host platforms set it; default 7860) |

> **Paper only.** This project never enables live trading; Phase 1 builds
> resolved paper records for future model training (see README + codebase.md).
