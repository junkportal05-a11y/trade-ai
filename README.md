---
title: ApexTrade Quant Server
emoji: 📈
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# ApexTrade Quant Server

ApexTrade is an advanced quantitative trading platform designed for real-time market analysis, automated technical signal generation, portfolio capital allocation, and performance tracking.

This repository hosts the code for both the **FastAPI backend** (deployed as a Docker space on Hugging Face) and the **React + Vite frontend** (deployed on Vercel).

---

## Architecture & Features

ApexTrade is divided into two primary services:

1. **FastAPI Backend (`/backend`)**
   - **Real-Time Data Feed:** Integrates with the AngelOne SmartAPI to stream live quotes and historical candlestick data.
   - **Quant Signal Engine:** Calculates complex technical indicators (VWAP, RSI, MACD, EMA) using vectorized NumPy computations for sub-millisecond execution times.
   - **Candlestick Pattern Analyzer:** Recognizes standard candlestick patterns (Doji, Engulfing, Hammer, Shooting Star, etc.) in real-time.
   - **Capital Allocator:** Features algorithmic risk management and allocation guidelines for open trade entries.
   - **SQLite Database Integration:** Tracks sessions, journaled trades, and token registry settings.
   - **Robust API & WebSockets:** Provides endpoints for live news sentiment scoring, backtesting, and websocket connections for live prices.

2. **React Frontend (`/frontend`)**
   - **ApexCharts Terminal:** High-performance charting terminal with interactive crosshair overlays and symbol watermarks.
   - **Trade Journal:** Glassmorphic trade tracker with real-time performance analytics (Total PnL, Win Rate, Best/Worst Trade metrics).
   - **Signals Panel:** Interactive dashboard display of live bullish/bearish scanner alerts.
   - **Account Settings:** Simplified code-based authentication and AngelOne API integration settings.

---

## Repository Structure

```directory
trade-ai/
├── backend/                  # FastAPI Python Backend
│   ├── tests/                # Automated pytest suite & performance benchmarks
│   ├── main.py               # Main application entry point & routing
│   ├── db.py                 # SQLite ORM & database interactions
│   ├── signals.py            # Vectorized indicator calculations (RSI, MACD, OBV, etc.)
│   ├── angelone_feed.py      # WebSockets consumer for AngelOne real-time feeds
│   ├── news_feed.py          # News aggregation & sentiment classification
│   ├── backtest_routes.py    # Backtesting api execution endpoints
│   ├── Dockerfile            # Container deployment specification
│   └── requirements.txt      # Python dependencies
│
├── frontend/                 # React + Vite + Vanilla CSS Frontend
│   ├── src/                  # React components & state custom hooks
│   │   ├── App.jsx           # Main trading dashboard & ApexCharts Terminal
│   │   ├── JournalPanel.jsx  # Trade journaling dashboard & analytics
│   │   └── hooks/            # Custom hooks (e.g., useMarketData websocket hook)
│   ├── vercel.json           # Vercel SPA routing configurations
│   └── package.json          # Node dependencies & scripts
│
├── knowledge/                # Trading reference documents & guides (PDFs/Text)
└── pytest.ini                # Test runner configurations
```

---

## Local Setup & Development

### 1. Backend Setup

Prerequisites: **Python 3.10+**

```bash
# Navigate to backend directory
cd backend

# Create a virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create your .env file
cp .env.example .env  # or manually create it
```

#### Required Backend Environment Variables (`backend/.env`):
```env
DATABASE_URL=postgresql://...  # Supabase Postgres or local SQLite path
JWT_SECRET=your_jwt_secret
ANGEL_API_KEY=your_angelone_api_key
ANGEL_CLIENT_CODE=your_angelone_client_code
ANGEL_PIN=your_angelone_pin
ANGEL_TOTP_SECRET=your_angelone_totp_secret
GEMINI_API_KEY=your_gemini_api_key
```

Run the backend server:
```bash
uvicorn main:app --reload --port 8000
```

---

### 2. Frontend Setup

Prerequisites: **Node.js 18+**

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run Vite dev server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Running Tests

We use `pytest` for backend testing and optimization verification.

```bash
# From the root directory:
pip install pytest pytest-asyncio
pytest
```

---

## Production Deployment

### Backend (Hugging Face Spaces)
The backend uses Docker and is automatically deployed to Hugging Face Spaces on pushes to the `huggingface` remote.
- Ensure all environment variables are set up in the Hugging Face **Space Settings ➔ Variables and secrets**.

### Frontend (Vercel)
The frontend is optimized for deployment on Vercel.

**CORS note:** the backend runs on Hugging Face Spaces, whose edge gateway
auto-answers the browser's CORS `OPTIONS` preflight and returns an empty
`Access-Control-Allow-Credentials` header. That breaks credentialed
(`credentials: 'include'`) cross-origin calls. To avoid it entirely, the
frontend is served **same-origin** and `vercel.json` rewrites `/api/:path*`
to the HF Space backend (a server-side proxy, so no browser preflight occurs).

- `vercel.json` already contains the `/api/:path*` → HF Space rewrite **and** the
  SPA fallback rewrite. Do **not** remove the API rewrite.
- Leave `VITE_API_URL` **empty** in `vercel.json` (and in Vercel project env vars)
  so the app calls its own origin and the rewrite proxies to the backend.
  Setting it to the HF Space URL reintroduces the cross-origin `OPTIONS` preflight
  and the CORS failure.
- `VITE_WS_URL` stays pointed at the HF Space `wss://` URL (Vercel rewrites cannot
  proxy WebSockets, and the WS auth uses a token query param so it is unaffected).
