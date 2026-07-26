# 🚨 2AM Incident Runbook

> Follow these steps IN ORDER. Don't think, just do.

## Step 0: Is the market even open?
- NSE trading hours: 9:15 AM – 3:30 PM IST (Mon–Fri)
- If it's outside market hours, the bot is idle. Check if there are open positions that need manual attention.

## Step 1: Check if the backend is alive
```bash
curl -s http://localhost:8000/
# Expected: {"status": "ok", ...}
# If no response → go to Step 4 (restart)
```

## Step 2: Check database health
```bash
sqlite3 backend/trading_platform.db "PRAGMA integrity_check; PRAGMA journal_mode;"
# Expected: "ok" and "wal"
# If integrity_check fails → STOP. Do NOT restart. Copy the DB file first:
cp backend/trading_platform.db backend/trading_platform.db.backup-$(date +%Y%m%d-%H%M)
```

## Step 3: Check AngelOne connection
```bash
curl -s http://localhost:8000/api/bot/status
# Look at the response. If broker connection is down:
# 1. Check AngelOne API status: https://smartapi.angelone.in/
# 2. Re-login may be needed (tokens expire daily at ~5:30 AM IST)
# 3. The bot auto-reconnects, but if stuck, restart (Step 4)
```

## Step 4: Restart the backend
```bash
# 1. Kill existing process
# On Windows:
taskkill /F /IM python.exe /FI "WINDOWTITLE eq uvicorn*"
# Or find the PID:
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# 2. Restart
cd "C:\Users\aryan\OneDrive\Desktop\trade ai app\backend"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 3. Verify it's back
curl -s http://localhost:8000/
```

## Step 5: Check for stuck trades
```bash
curl -s http://localhost:8000/api/bot/trades
# Look for trades with status "PENDING" that are older than 30 minutes
# These may need manual square-off via the dashboard
```

## Step 6: If all else fails
1. Stop the bot: `curl -X POST http://localhost:8000/api/bot/stop`
2. This triggers automatic square-off of all positions
3. Wait for market open to investigate further
4. Check logs: `backend/logs/` directory

---
*Created: 2026-07-23 | Last updated: 2026-07-23*
