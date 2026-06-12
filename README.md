---
title: ApexTrade Quant Server
emoji: 📈
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# 📈 ApexTrade Quant Server

ApexTrade is an advanced quantitative trading platform designed for real-time market analysis, automated technical signal generation, portfolio capital allocation, and performance tracking.

This repository hosts the code for both the **FastAPI backend** (deployed as a Docker space on Hugging Face) and the **React + Vite frontend** (deployed on Vercel).

---

## 🏗️ Architecture & Features

ApexTrade is divided into two primary services:

1. **FastAPI Backend (`/backend`)**
   - **Real-Time Data Feed:** Integrates with the Upstox API to stream live quotes and historical candlestick data.
   - **Quant Signal Engine:** Calculates complex technical indicators (VWAP, RSI, MACD, EMA) using vectorized NumPy computations for sub-millisecond execution times.
   - **Candlestick Pattern Analyzer:** Recognizes standard candlestick patterns (Doji, Engulfing, Hammer, Shooting Star, etc.) in real-time.
   - **Capital Allocator:** Features algorithmic risk management and allocation guidelines for open trade entries.
   - **SQLite Database Integration:** Tracks sessions, journaled trades, and token registry settings.
   - **Robust API & WebSockets:** Provides endpoints for live news sentiment scoring, backtesting, and websocket connections for live prices.

2. **React Frontend (`/frontend`)**
   - **ApexCharts Terminal:** High-performance charting terminal with interactive crosshair overlays and symbol watermarks.
   - **Trade Journal:** Glassmorphic trade tracker with real-time performance analytics (Total PnL, Win Rate, Best/Worst Trade metrics).
   - **Signals Panel:** Interactive dashboard display of live bullish/bearish scanner alerts.
   - **Account Settings:** Simplified code-based authentication and Upstox API integration settings.

---

## 📂 Repository Structure

```directory
trade-ai/
├── backend/                  # FastAPI Python Backend
│   ├── tests/                # Automated pytest suite & performance benchmarks
│   ├── main.py               # Main application entry point & routing
│   ├── db.py                 # SQLite ORM & database interactions
│   ├── signals.py            # Vectorized indicator calculations (RSI, MACD, OBV, etc.)
│   ├── upstox_feed.py        # WebSockets consumer for Upstox real-time feeds
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

## 🚀 Local Setup & Development

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
UPSTOX_API_KEY=your_upstox_api_key
UPSTOX_API_SECRET=your_upstox_api_secret
UPSTOX_REDIRECT_URI=http://localhost:5173/auth/callback
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

## 🧪 Running Tests

We use `pytest` for backend testing and optimization verification.

```bash
# From the root directory:
pip install pytest pytest-asyncio
pytest
```

---

## 🌐 Production Deployment

### Backend (Hugging Face Spaces)
The backend uses Docker and is automatically deployed to Hugging Face Spaces on pushes to the `huggingface` remote.
- Ensure all environment variables are set up in the Hugging Face **Space Settings ➔ Variables and secrets**.

### Frontend (Vercel)
The frontend is optimized for deployment on Vercel.
- Configure rewriting for React Router SPAs in `vercel.json`.
- Point `VITE_API_URL` to your live Hugging Face Spaces backend API domain.
