# Vite Production URLs for Hugging Face Space Deployment

## Current State
- Vite dev config proxies to `http://127.0.0.1:8000` (localhost)
- For HF Space production, update API/WebSocket endpoints

## Option A: Set Environment Variables (Recommended)

Add to your deployment environment or `.env`:

```bash
# API base URL (your HF Space backend)
VITE_API_URL=https://apextrade-core-trade-ai-backend.hf.space

# WebSocket URL (must use wss:// for production)
VITE_WS_URL=wss://apextrade-core-trade-ai-backend.hf.space
```

## Option B: Update Vite Config

Edit `frontend/vite.config.js` to update proxy targets:

```javascript
server: {
    proxy: {
      '/api': {
        target: 'https://apextrade-core-trade-ai-backend.hf.space',
        changeOrigin: true,
      },
      '/ws': {
        target: 'wss://apextrade-core-trade-ai-backend.hf.space',
        ws: true,
        changeOrigin: true,
      }
    }
},
```

## What These Configure

| Variable | Purpose | Default |
|----------|---------|---------|
| `VITE_API_URL` | Base API endpoint for `apiFetch()` calls | `http://127.0.0.1:8000` (dev) |
| `VITE_WS_URL` | WebSocket connection URL for bot | `ws://localhost:8000/ws` (dev) |

## Without Configuration

The frontend will use:
- `http://127.0.0.1:8000` API (localhost only)
- `ws://localhost:8000/ws` WebSocket (localhost only)

This works for local development but not for HF Space deployment.

## With Configuration

The frontend will use your configured URLs:
- All API calls route to your HF Space backend
- Bot WebSocket connects to your HF Space instance
- Trade Log, Journal, and all features work end-to-end

## Recommended Approach

1. **Set environment variables** (Option A) - cleaner, no code changes
2. **Or update vite.config.js** (Option B) - if you prefer code-based config
3. **Both** - env vars take precedence over vite.config.js defaults

## After Configuration

Restart your frontend development server or redeploy to HF Space, and:
- Trade Log will show entries
- Journal UI will be functional
- Bot WebSocket connection will establish
- All features work end-to-end