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

This is the Python FastAPI backend for the ApexTrade platform, deployed as a Docker container on Hugging Face Spaces.

## Setup & Running on Hugging Face Spaces

1. Create a new Space on Hugging Face (https://huggingface.co/new-space).
2. Choose **Docker** as the SDK.
3. Link your GitHub repository or push this repository directly to the Hugging Face Space Git remote.
4. Set up the required environment variables in the Hugging Face Space settings (Settings -> Variables and secrets):
   - `DATABASE_URL`: Your Supabase Postgres connection string (e.g. `postgresql://...`).
   - `JWT_SECRET`: Secret key for token generation.
   - `UPSTOX_API_KEY`: Your Upstox API key.
   - `UPSTOX_API_SECRET`: Your Upstox API secret.
   - `UPSTOX_REDIRECT_URI`: The redirect URI configured in Upstox developer portal (usually matches your Vercel frontend domain).
   - `GEMINI_API_KEY`: Google Gemini API key.
   - Any other secret variables needed by your app.
