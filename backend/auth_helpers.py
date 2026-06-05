import os
import time
from fastapi import HTTPException, Header, Depends
from dotenv import load_dotenv

load_dotenv()

ADMIN_KEY = os.getenv("ADMIN_KEY", "apextrade_admin_2024_secure")
APP_PASSWORD = os.getenv("APP_PASSWORD", "Ap3xTr@de#Secur1ty!2026")
SECRET_KEY = os.getenv("SECRET_KEY", "insecure-default")

# Secure backend-side registry of authorized entrants
USER_REGISTRY = {
    'apex_head_quant': { 'pass': APP_PASSWORD, 'role': 'Master Quant / Administrator', 'clearance': 'LEVEL_4_ROOT' },
    'user1': { 'pass': 'pass1', 'role': 'Quant Trader Level 1', 'clearance': 'LEVEL_2_SECURE' },
    'user2': { 'pass': 'pass2', 'role': 'Quant Trader Level 2', 'clearance': 'LEVEL_2_SECURE' },
    'user3': { 'pass': 'pass3', 'role': 'Risk Manager', 'clearance': 'LEVEL_3_ELEVATED' }
}

# In-memory session store: { token: { "username": str, "time": float } }
ACTIVE_SESSIONS = {}
SESSION_TTL = 8 * 3600  # 8 hours

def require_admin(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Admin access required")

def create_session(username: str) -> str:
    token = "apt_" + os.urandom(24).hex()
    ACTIVE_SESSIONS[token] = {
        "username": username,
        "time": time.time()
    }
    return token

def require_session(x_session_token: str = Header(None)):
    if not x_session_token or x_session_token not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=401, detail="Login required")
    session_data = ACTIVE_SESSIONS[x_session_token]
    created = session_data["time"]
    if time.time() - created > SESSION_TTL:
        del ACTIVE_SESSIONS[x_session_token]
        raise HTTPException(status_code=401, detail="Session expired")
    return x_session_token

def cleanup_sessions():
    now = time.time()
    expired = [k for k, v in ACTIVE_SESSIONS.items() if now - v["time"] > SESSION_TTL]
    for k in expired:
        del ACTIVE_SESSIONS[k]
