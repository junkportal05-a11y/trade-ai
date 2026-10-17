"""Core security utilities — hashing, JWT, encryption, password management."""
from __future__ import annotations

import base64
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from cryptography.fernet import Fernet, MultiFernet
from fastapi import Header, HTTPException, Request
from jose import JWTError, jwt

from app.core.config import settings
from app.core.logging import logger

# ── Fernet for encrypting sensitive broker credentials ────────────────────────
_fernet_list = []
if settings.fernet_keys:
    for key in settings.fernet_keys:
        try:
            _fernet_list.append(Fernet(key))
        except Exception as e:
            logger.error(f"Failed to initialize Fernet with key: {e}")

# Ensure at least one Fernet instance exists (generate a new key if none valid)
if not _fernet_list:
    try:
        _fernet_list = [Fernet(Fernet.generate_key())]
        logger.warning("Generated new Fernet key (no valid keys in settings.fernet_keys)")
    except Exception as e:
        logger.error(f"Failed to generate Fernet key: {e}")

_fernet = MultiFernet(_fernet_list) if _fernet_list else None


def encrypt_value(plaintext: str | None) -> str | None:
    """Encrypt a sensitive string for storage. Returns base64 ciphertext."""
    if plaintext is None or _fernet is None:
        return None
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str | None) -> str | None:
    """Decrypt a Fernet-encrypted string."""
    if ciphertext is None or _fernet is None:
        return None
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except Exception:
        return None


# ── Password hashing ──────────────────────────────────────────────────────────
def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except (ValueError, TypeError):
        return False


def is_bcrypt_hash(value: str) -> bool:
    return value.startswith(("$2a$", "$2b$", "$2y$"))


# ── JWT tokens ────────────────────────────────────────────────────────────────
def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(seconds=settings.session_ttl)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        return None


# ── User registry (loaded from env, hashed at runtime) ────────────────────────
class UserRegistry:
    """In-memory user registry with bcrypt-hashed passwords."""

    def __init__(self) -> None:
        self._users: dict[str, dict] = {}
        self._load_from_env()

    def _load_from_env(self) -> None:
        raw_admin = os.getenv("PASS_ADMIN", os.getenv("APP_PASSWORD", "")).strip()
        if not raw_admin:
            raw_admin = secrets.token_urlsafe(32)
            logger.warning("PASS_ADMIN not set in env. Generated random ephemeral master password for runtime safety.")

        admin_hash = (
            raw_admin
            if is_bcrypt_hash(raw_admin)
            else get_password_hash(raw_admin)
        )
        self._users["apex_head_quant"] = {
            "pass_hash": admin_hash,
            "role": "Master Quant / Administrator",
            "clearance": "LEVEL_4_ROOT",
        }

        # Other users
        for username, env_var, role, clearance in [
            ("user1", "PASS_USER1", "Quant Trader Level 1", "LEVEL_2_SECURE"),
            ("user2", "PASS_USER2", "Quant Trader Level 2", "LEVEL_2_SECURE"),
            ("user3", "PASS_USER3", "Risk Manager", "LEVEL_3_ELEVATED"),
        ]:
            val = os.getenv(env_var)
            if val:
                h = val if is_bcrypt_hash(val) else get_password_hash(val)
                self._users[username] = {
                    "pass_hash": h,
                    "role": role,
                    "clearance": clearance,
                }

    def get_user(self, username: str) -> dict | None:
        return self._users.get(username)

    def authenticate(self, username: str, password: str) -> dict | None:
        try:
            user = self._users.get(username)
            if not user:
                return None
            if verify_password(password, user["pass_hash"]):
                return user
            return None
        except Exception as e:
            logger.error(f"[SECURITY AUTH ERROR] authenticate() failed for user '{username}': {e}", exc_info=True)
            return None

    def authenticate_by_code(self, code: str) -> tuple[str | None, dict | None]:
        """Authenticate by password alone — used for single-code login."""
        try:
            for username, user in self._users.items():
                if verify_password(code, user["pass_hash"]):
                    return username, user
            return None, None
        except Exception as e:
            logger.error(f"[SECURITY AUTH ERROR] authenticate_by_code() failed: {e}", exc_info=True)
            return None, None


user_registry = UserRegistry()


# ── Dependencies ─────────────────────────────────────────────────────────────
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security_bearer = HTTPBearer(auto_error=False)


def get_token_from_request(request: Request) -> str | None:
    """Extract token from cookie, header, or Authorization bearer."""
    token = request.cookies.get("apt_token")
    if token:
        return token
    token = request.headers.get("x-session-token")
    if token:
        return token
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:]
    return None


async def require_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
) -> dict[str, Any]:
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")

    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = user_registry.get_user(username)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return {
        "username": username,
        "role": user.get("role", "Authorized Guest"),
        "clearance": user.get("clearance", "LEVEL_1_GUEST"),
    }


async def optional_session(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_bearer),
) -> dict[str, Any] | None:
    token = get_token_from_request(request)
    if not token:
        return None

    payload = decode_access_token(token)
    if not payload:
        return None

    username = payload.get("sub")
    if not username:
        return None

    user = user_registry.get_user(username)
    if not user:
        return None

    return {
        "username": username,
        "role": user.get("role", "Authorized Guest"),
        "clearance": user.get("clearance", "LEVEL_1_GUEST"),
    }


# ── Clearance enforcement ─────────────────────────────────────────────────────
LEVELS = ["LEVEL_1_GUEST", "LEVEL_2_TRADER", "LEVEL_3_ADMIN", "LEVEL_4_ROOT"]

def require_clearance(min_level: str):
    """Dependency that requires minimum clearance level."""
    def checker(session: dict = Depends(require_session)):
        user_level = session.get("clearance", "LEVEL_1_GUEST")
        if LEVELS.index(user_level) < LEVELS.index(min_level):
            raise HTTPException(status_code=403, detail=f"Requires {min_level} clearance")
        return session
    return checker


async def csrf_protect(request: Request):
    """CSRF check that enforces X-Requested-With header on mutating routes.
    
    - When TESTING is "1" (default from conftest): passes through, no enforcement.
    - When TESTING is cleared: returns 403 if X-Requested-With header is missing.
    """
    if os.getenv("TESTING") != "1":
        x_requested_with = request.headers.get("X-Requested-With")
        if not x_requested_with:
            raise HTTPException(status_code=403, detail="CSRF token required")
    return True


# CSRF dependency - defined after csrf_protect to avoid forward reference
CsrfDep = Depends(csrf_protect)


def require_admin(
    request: Request,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> str:
    provided_key = x_admin_key or request.headers.get("X-Admin-Key") or request.headers.get("x-admin-key")
    if not provided_key or not secrets.compare_digest(provided_key, settings.admin_key):
        raise HTTPException(status_code=403, detail="Admin access required")
    return provided_key