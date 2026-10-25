# APEXTRADE AI — Free Tier Production Setup Guide

This guide walks you through setting up ApexTrade AI on 100% free tier services for production deployment.

---

## 🏗️ Architecture Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend API    │────▶│   PostgreSQL    │
│  (Vercel/       │     │  (Cloud Run      │     │  (Supabase/     │
│   Netlify)      │     │   Free Tier)     │     │   Neon)         │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
            ┌─────────────┐ ┌──────────┐ ┌────────────┐
            │  Upstash    │ │  Sentry  │ │   Gemini   │
            │  Redis      │ │  (Free)  │ │ 2.0 Flash  │
            │  (Free)     │ │          │ │  (Free)    │
            └─────────────┘ └──────────┘ └────────────┘
```

---

## 📋 Prerequisites

1. **Google Cloud Account** — [cloud.google.com](https://cloud.google.com) (Free Tier: $300 credit + Always Free)
2. **GitHub Account** — For source deployment
3. **Domain (optional)** — For custom domain mapping

---

## 🔑 Free Service Credentials

### 1. Google AI Studio — Gemini 2.0 Flash API Key
- **Cost:** $0 (Free tier: 15 RPM, 1M tokens/day)
- **Get key:** https://aistudio.google.com/app/apikey
- **Env var:** `GEMINI_API_KEY`

### 2. Supabase — PostgreSQL Database
- **Cost:** $0 (Free tier: 500MB database, 1GB bandwidth)
- **Alternative:** Neon (neon.tech) — 0.5GB storage free
- **Get URL:** Create project at https://supabase.com → Settings → Database → Connection string
- **Env var:** `DATABASE_URL` (format: `postgresql://user:pass@host:5432/dbname`)

### 3. Upstash — Redis for Rate Limiting
- **Cost:** $0 (Free tier: 10K requests/day, 256MB)
- **Get URL:** https://upstash.com → Create Database → Redis → Copy connection string
- **Env var:** `UPSTASH_REDIS_URL` (format: `redis://default:password@host:port`)

### 4. Google Cloud Run — Backend Hosting
- **Cost:** $0 (Always Free: 2M requests/month, 360k vCPU-seconds, 180k GiB-seconds)
- **Setup:** Enable Cloud Run API in GCP Console
- **Deploy:** Use `scripts/deploy_cloud_run.sh` or `.bat`

### 5. Sentry — Error Tracking (Optional)
- **Cost:** $0 (Free tier: 5K errors/month, 10K transactions)
- **Get DSN:** https://sentry.io → Create Project → Settings → Client Keys (DSN)
- **Env var:** `SENTRY_DSN`

### 6. Vercel — Frontend Hosting
- **Cost:** $0 (Free tier: 100GB bandwidth, unlimited personal projects)
- **Deploy:** Connect GitHub repo → Auto-deploy on push
- **Env var:** `VITE_API_URL` (your Cloud Run service URL)

---

## 🚀 Deployment Steps

### 1. Prepare Google Cloud Project
```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud auth application-default login

# Create/select project
gcloud projects create YOUR_PROJECT_ID  # or use existing
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com
```

### 2. Set Up Supabase/Neon Database
1. Create project at https://supabase.com or https://neon.tech
2. Get connection string (PostgreSQL)
3. Run migrations (optional - auto-runs on startup):
   ```bash
   # Local test
   DATABASE_URL="postgresql://..." .venv\Scripts\python.exe -m alembic upgrade head
   ```

### 3. Set Up Upstash Redis
1. Create database at https://upstash.com
2. Select "Redis" type, choose region close to `us-central1`
3. Copy connection string (starts with `redis://`)

### 4. Get Gemini API Key
1. Go to https://aistudio.google.com/app/apikey
2. Create API key
3. Copy key

### 5. Deploy Backend to Cloud Run
```bash
# Make script executable
chmod +x scripts/deploy_cloud_run.sh

# Run deployment
./scripts/deploy_cloud_run.sh
```

### 6. Configure Cloud Run Environment Variables
In Google Cloud Console → Cloud Run → `apextrade-backend` → Edit & Deploy New Revision → Variables & Secrets:

| Variable | Value | Source |
|----------|-------|--------|
| `ENVIRONMENT` | `production` | Direct |
| `DATABASE_URL` | `postgresql://...` | Secret Manager (recommended) |
| `GEMINI_API_KEY` | `your-key` | Secret Manager |
| `UPSTASH_REDIS_URL` | `redis://...` | Secret Manager |
| `SENTRY_DSN` | `https://...` | Secret Manager |
| `JWT_SECRET` | `generate: openssl rand -hex 32` | Secret Manager |
| `FERNET_KEYS` | `generate: openssl rand -urlsafe 32` | Secret Manager |
| `ADMIN_KEY` | `generate: openssl rand -hex 24` | Secret Manager |
| `ALLOWED_ORIGINS` | `https://your-frontend.vercel.app` | Direct |

**Generate secrets locally:**
```bash
# JWT_SECRET (32 bytes hex)
openssl rand -hex 32

# FERNET_KEYS (url-safe base64)
openssl rand -urlsafe 32

# ADMIN_KEY (24 bytes hex)
openssl rand -hex 24
```

### 7. Deploy Frontend to Vercel
1. Push code to GitHub
2. Import project in Vercel: https://vercel.com/new
3. Set Root Directory: `frontend`
4. Add Environment Variable:
   - `VITE_API_URL` = Your Cloud Run service URL (e.g., `https://apextrade-backend-xyz.us-central1.run.app`)
5. Deploy

---

## 🔐 Security Checklist

- [ ] All secrets stored in Secret Manager (not in code/env files)
- [ ] `ENVIRONMENT=production` set
- [ ] `ALLOWED_ORIGINS` restricted to your frontend domain
- [ ] `JWT_SECRET`, `FERNET_KEYS`, `ADMIN_KEY` are strong random values
- [ ] Database uses SSL (`sslmode=require`)
- [ ] CORS configured correctly
- [ ] Rate limiting enabled (Upstash Redis connected)

---

## 💰 Cost Summary (Monthly)

| Service | Free Tier Limit | Estimated Cost |
|---------|----------------|----------------|
| Cloud Run | 2M requests, 360k vCPU-sec | $0 |
| Supabase/Neon | 500MB DB, 1GB bandwidth | $0 |
| Upstash Redis | 10K req/day, 256MB | $0 |
| Gemini 2.0 Flash | 1M tokens/day | $0 |
| Sentry | 5K errors/month | $0 |
| Vercel | 100GB bandwidth | $0 |
| **Total** | | **$0/month** |

---

## 🛠️ Local Development

```bash
# Backend
cd backend
cp .env.example .env
# Edit .env with your local keys
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/macOS
uvicorn app.main:app --reload --port 7860

# Frontend
cd frontend
npm install
npm run dev
```

---

## 📝 Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ENVIRONMENT` | Yes | `development` \| `staging` \| `production` | `production` |
| `DATABASE_URL` | Yes | PostgreSQL connection string | `postgresql://user:pass@host/db` |
| `GEMINI_API_KEY` | Yes | Google AI Studio API key | `AIza...` |
| `UPSTASH_REDIS_URL` | Yes | Upstash Redis connection | `redis://default:pass@host:port` |
| `SENTRY_DSN` | No | Sentry error tracking DSN | `https://key@o0.ingest.sentry.io/0` |
| `JWT_SECRET` | Yes | 32-byte hex for JWT signing | `a1b2c3...` |
| `FERNET_KEYS` | Yes | URL-safe base64 for encryption | `abc123...` |
| `ADMIN_KEY` | Yes | Admin API access key | `def456...` |
| `ALLOWED_ORIGINS` | Yes | Comma-separated frontend URLs | `https://app.example.com` |
| `TRADING_MODE` | No | `paper` \| `live` | `paper` |
| `PORT` | No | Server port (Cloud Run sets automatically) | `7860` |

---

## 🆘 Troubleshooting

### Cloud Run Deployment Fails
- Check `gcloud` version: `gcloud version` (update if needed)
- Ensure billing is enabled on GCP project
- Verify all APIs enabled: `gcloud services list --enabled`

### Database Connection Errors
- Verify `DATABASE_URL` format: `postgresql://user:pass@host:5432/dbname?sslmode=require`
- Check Supabase/Neon allows connections from 0.0.0.0/0 (Cloud Run IPs)
- Run migrations manually if needed

### Redis Connection Errors
- Verify Upstash Redis allows connections from anywhere
- Check `UPSTASH_REDIS_URL` format: `redis://default:password@host:port`

### Frontend Can't Connect to Backend
- Verify `VITE_API_URL` in Vercel matches Cloud Run service URL exactly
- Check `ALLOWED_ORIGINS` in Cloud Run includes frontend domain
- Check browser console for CORS errors

---

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Supabase Docs](https://supabase.com/docs)
- [Upstash Docs](https://upstash.com/docs)
- [Gemini API Docs](https://ai.google.dev/docs)
- [Sentry Python Docs](https://docs.sentry.io/platforms/python/)
- [Vercel Docs](https://vercel.com/docs)