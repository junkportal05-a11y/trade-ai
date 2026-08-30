import asyncio
import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import logging

logger = logging.getLogger(__name__)
import db
from app.core.logging import logger

router = APIRouter(prefix="/ws", tags=["websocket"])

def _now_ist() -> datetime:
    utc = datetime.now(timezone.utc)
    return utc + timedelta(hours=5, minutes=30)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.polling_task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Start background polling when the first client connects
        if len(self.active_connections) == 1 and not self.polling_task:
            self.polling_task = asyncio.create_task(self.poll_db())

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        # Stop polling if no clients are left
        if len(self.active_connections) == 0 and self.polling_task:
            self.polling_task.cancel()
            self.polling_task = None

    async def broadcast(self, message: dict):
        text_data = json.dumps(message)
        # Broadcast to a copy of the list to avoid modification during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_text(text_data)
            except Exception:
                self.disconnect(connection)

    async def poll_db(self):
        while True:
            try:
                # Fetch bot status
                state = db.get_bot_state()
                today = _now_ist().strftime("%Y-%m-%d")
                with db._conn() as c:
                    row = c.execute(
                        "SELECT COALESCE(SUM(pnl_pct),0) AS pnl FROM predictions_history "
                        "WHERE status IN ('WIN','LOSS','TIMEOUT') AND resolved_at LIKE ?",
                        (today + "%",),
                    ).fetchone()
                    todays_pnl = float(row["pnl"]) if row else 0.0

                    sig = c.execute(
                        "SELECT * FROM signals_history ORDER BY scanned_at DESC LIMIT 1"
                    ).fetchone()
                    last_signal = dict(sig) if sig else None

                    pos = c.execute(
                        "SELECT * FROM predictions_history WHERE status='PENDING' "
                        "ORDER BY prediction_date DESC"
                    ).fetchall()
                    positions = [dict(p) for p in pos]

                    rows = c.execute(
                        "SELECT * FROM predictions_history "
                        "WHERE status IN ('PENDING','WIN','LOSS','TIMEOUT') "
                        "ORDER BY prediction_date DESC LIMIT 50"
                    ).fetchall()
                    trades = [dict(r) for r in rows]

                data = {
                    "type": "bot_update",
                    "status": {
                        "state": state,
                        "today_pnl": round(todays_pnl, 2),
                        "last_signal": last_signal,
                        "positions": positions
                    },
                    "trades": trades
                }

                await self.broadcast(data)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[WS] Polling error: {e}")
                
            await asyncio.sleep(2) # Poll every 2 seconds

manager = ConnectionManager()

def _require_ws_auth(websocket: WebSocket) -> dict | None:
    token = websocket.query_params.get("token") or websocket.cookies.get("apt_token")
    if not token:
        auth = websocket.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth[7:]
    if not token:
        return None
    from app.core.security import decode_access_token
    return decode_access_token(token)

@router.websocket("/bot")
async def websocket_bot_endpoint(websocket: WebSocket):
    session = _require_ws_auth(websocket)
    if not session:
        await websocket.close(code=4001, reason="Authentication required")
        return
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.websocket("/prices")
async def websocket_prices_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live price ticks - requires auth token query param."""
    session = _require_ws_auth(websocket)
    if not session:
        await websocket.close(code=4001, reason="Authentication required")
        return
    await websocket.accept()
    subscribed_symbols: List[str] = []

    async def send_ticks():
        import random
        base_prices = {
            'YESBANK.NS': 25.0, 'TATASTEEL.NS': 170.0, 'BANKBARODA.NS': 280.0,
            'TATAPOWER.NS': 445.0, 'SBIN.NS': 830.0
        }
        while True:
            await asyncio.sleep(3)
            if not subscribed_symbols:
                continue
            ticks = []
            now = _now_ist().isoformat()
            for sym in subscribed_symbols:
                base_price = base_prices.get(sym, 100.0)
                price = round(base_price * (1 + random.uniform(-0.003, 0.003)), 2)
                ticks.append({
                    "symbol": sym,
                    "price": price,
                    "prev_close": base_price,
                    "timestamp": now
                })
            try:
                await websocket.send_text(json.dumps({"type": "tick", "data": ticks}))
            except Exception:
                break

    tick_task = asyncio.create_task(send_ticks())

    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                continue
            try:
                msg = json.loads(data)
                if isinstance(msg, dict) and msg.get("action") == "subscribe":
                    syms = msg.get("symbols")
                    if isinstance(syms, list):
                        subscribed_symbols.clear()
                        subscribed_symbols.extend(syms)
                        await websocket.send_text(json.dumps({"type": "subscribed", "symbols": syms}))
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        tick_task.cancel()
