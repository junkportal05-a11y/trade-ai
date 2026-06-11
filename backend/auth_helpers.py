import os
import time
import bcrypt
import secrets
from fastapi import HTTPException, Header, Request
from dotenv import load_dotenv

load_dotenv()

ADMIN_KEY = os.getenv("ADMIN_KEY")
if not ADMIN_KEY:
    ADMIN_KEY = secrets.token_hex(24)
    print(
        f"\n[SECURITY WARNING] ADMIN_KEY is not set in environment! Generated a temporary admin key: {ADMIN_KEY}\n"
    )

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)

# In-memory session store: { token: { "username": str, "time": float } }
ACTIVE_SESSIONS = {}
SESSION_TTL = 8 * 3600  # 8 hours


# Hashing utilities
def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def is_bcrypt_hash(value: str) -> bool:
    return (
        value.startswith("$2a$") or value.startswith("$2b$") or value.startswith("$2y$")
    )


# Process credentials dynamically on startup to avoid keeping plaintext passwords in memory
USER_REGISTRY = {}

# 1. Admin account initialization
raw_pass_admin = (os.getenv("PASS_ADMIN") or "").strip() or (
    os.getenv("APP_PASSWORD") or ""
).strip()
if not raw_pass_admin:
    # Fallback to a secure random temporary password printed to terminal console
    temp_pass = secrets.token_urlsafe(16)
    print("\n" + "=" * 80)
    print(" [SECURITY WARNING] PASS_ADMIN / APP_PASSWORD is not configured in .env!")
    print(f" Generated a secure temporary session password for 'apex_head_quant':")
    print(f" {temp_pass}")
    print("=" * 80 + "\n")
    admin_hash = get_password_hash(temp_pass)
else:
    admin_hash = (
        raw_pass_admin
        if is_bcrypt_hash(raw_pass_admin)
        else get_password_hash(raw_pass_admin)
    )

USER_REGISTRY["apex_head_quant"] = {
    "pass_hash": admin_hash,
    "role": "Master Quant / Administrator",
    "clearance": "LEVEL_4_ROOT",
}

# 2. Other sandbox account initializations
for username, env_var, role, clearance in [
    ("user1", "PASS_USER1", "Quant Trader Level 1", "LEVEL_2_SECURE"),
    ("user2", "PASS_USER2", "Quant Trader Level 2", "LEVEL_2_SECURE"),
    ("user3", "PASS_USER3", "Risk Manager", "LEVEL_3_ELEVATED"),
]:
    val = os.getenv(env_var)
    if val:  # Only enable account if a password is configured in the environment
        hash_val = val if is_bcrypt_hash(val) else get_password_hash(val)
        USER_REGISTRY[username] = {
            "pass_hash": hash_val,
            "role": role,
            "clearance": clearance,
        }


def authenticate_user(username: str, password: str) -> bool:
    user_obj = USER_REGISTRY.get(username)
    if not user_obj:
        return None
    try:
        if bcrypt.checkpw(
            password.encode("utf-8"), user_obj["pass_hash"].encode("utf-8")
        ):
            return user_obj
    except Exception:
        pass
    return None


def require_admin(x_admin_key: str = Header(None)):
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=403, detail="Admin access required")


def create_session(username: str) -> str:
    token = "apt_" + os.urandom(24).hex()
    ACTIVE_SESSIONS[token] = {"username": username, "time": time.time()}
    return token


def require_session(request: Request):
    x_session_token = request.cookies.get("apt_token")
    if not x_session_token:
        raise HTTPException(
            status_code=401, detail="Authentication session token required"
        )

    if not x_session_token.startswith("apt_") or x_session_token not in ACTIVE_SESSIONS:
        raise HTTPException(status_code=401, detail="Invalid session token")

    session_data = ACTIVE_SESSIONS[x_session_token]
    created = session_data["time"]
    if time.time() - created > SESSION_TTL:
        del ACTIVE_SESSIONS[x_session_token]
        raise HTTPException(status_code=401, detail="Session expired")

    return {
        "username": session_data["username"],
        "role": USER_REGISTRY.get(session_data["username"], {}).get(
            "role", "Authorized Guest"
        ),
        "clearance": USER_REGISTRY.get(session_data["username"], {}).get(
            "clearance", "LEVEL_1_GUEST"
        ),
    }


def cleanup_sessions():
    now = time.time()
    expired = [k for k, v in ACTIVE_SESSIONS.items() if now - v["time"] > SESSION_TTL]
    for k in expired:
        del ACTIVE_SESSIONS[k]
