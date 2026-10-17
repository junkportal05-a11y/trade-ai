"""App core configuration using pydantic-settings."""
from __future__ import annotations

import os
import secrets
from typing import List, Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    load_dotenv(_env_path, override=False)
    load_dotenv(override=False)
except Exception:
    pass


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────
    app_name: str = "ApexTrade API"
    app_version: str = "3.0.0"
    debug: bool = Field(default=False, alias="DEBUG")
    environment: Literal["development", "staging", "production"] = "development"

    # ── Database ─────────────────────────────────────────────────────
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    db_path: str = Field(default="../trading_platform.db", alias="DB_PATH")

    @property
    def is_postgres(self) -> bool:
        return bool(self.database_url)

    # ── Security ─────────────────────────────────────────────────────
    jwt_secret: str = Field(default_factory=lambda: secrets.token_hex(32), alias="JWT_SECRET")
    fernet_keys: List[str] | str = Field(
        default_factory=lambda: [secrets.token_urlsafe(32)],
        alias="FERNET_KEYS"
    )

    @field_validator("fernet_keys", mode="before")
    @classmethod
    def _validate_fernet_keys(cls, v: Any) -> List[str]:
        env_keys = os.getenv("FERNET_KEYS") or os.getenv("FERNET_KEY")
        if env_keys:
            if isinstance(env_keys, str):
                if env_keys.startswith("[") and env_keys.endswith("]"):
                    try:
                        import json
                        parsed = json.loads(env_keys)
                        if isinstance(parsed, list):
                            return [str(k) for k in parsed]
                    except Exception:
                        pass
                return [k.strip() for k in env_keys.split(",") if k.strip()]
        if isinstance(v, list) and v:
            return v
        if isinstance(v, str) and v:
            return [v]
        return [secrets.token_urlsafe(32)]

    admin_key: str = Field(default_factory=lambda: secrets.token_hex(24), alias="ADMIN_KEY")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        import logging
        is_prod = self.environment.lower() in ("production", "prod", "staging")
        missing = []

        if not os.getenv("JWT_SECRET"):
            if is_prod:
                missing.append("JWT_SECRET")
            else:
                logging.warning("JWT_SECRET using generated fallback — set JWT_SECRET env var for production")

        if not (os.getenv("FERNET_KEYS") or os.getenv("FERNET_KEY")):
            if is_prod:
                missing.append("FERNET_KEYS")
            else:
                logging.warning("FERNET_KEYS using generated fallback — set FERNET_KEYS env var for production")

        if not os.getenv("ADMIN_KEY"):
            if is_prod:
                missing.append("ADMIN_KEY")
            else:
                logging.warning("ADMIN_KEY using generated fallback — set ADMIN_KEY env var for production")

        if missing:
            raise ValueError(
                f"CRITICAL SECURITY FAILURE: Missing required environment variable(s) in {self.environment} mode: "
                f"{', '.join(missing)}. Production deployments require explicit JWT_SECRET, FERNET_KEYS, and ADMIN_KEY."
            )
    session_ttl: int = Field(default=8 * 3600, alias="SESSION_TTL")  # 8 hours
    algorithm: str = "HS256"

    # ── Broker ───────────────────────────────────────────────────────
    angel_api_key: str | None = Field(default=None, alias="ANGEL_API_KEY")
    angel_client_code: str | None = Field(default=None, alias="ANGEL_CLIENT_CODE")
    angel_pin: str | None = Field(default=None, alias="ANGEL_PIN")
    angel_totp_secret: str | None = Field(default=None, alias="ANGEL_TOTP_SECRET")

    # ── AI ───────────────────────────────────────────────────────────
    gemini_api_key: str | None = Field(default="AIzaSyAZvgGUycrvWhuH37nSygGXiYWvQstPnNw", alias="GEMINI_API_KEY")
    news_api_key: str | None = Field(default=None, alias="NEWS_API_KEY")

    # ── CORS ─────────────────────────────────────────────────────────
    # Env var ALLOWED_ORIGINS (comma-separated) overrides the hardcoded default.
    allowed_origins: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://localhost:3000,"
        "http://127.0.0.1:5173,http://127.0.0.1:3000,"
        "https://trade-ai-beta.vercel.app,https://frontend-two-tau-82.vercel.app"
    )

    # ── Trading Constants ────────────────────────────────────────────
    max_concurrent_trades: int = 2
    min_agent_confidence: int = 72
    cache_ttl_seconds: int = 300
    auto_scan_interval_open: int = 60
    auto_scan_interval_closed: int = 3600
    daily_loss_limit: float = -3.0
    daily_drawdown_limit: float = -4.0
    max_consecutive_losses: int = 5
    default_capital: float = 100_000.0
    trading_mode: Literal["paper", "live"] = Field(default="paper", alias="TRADING_MODE")
    live_trading_armed: bool = Field(default=False, alias="LIVE_TRADING_ARMED")

    # ── Rate Limits ──────────────────────────────────────────────────
    rate_limit_login: str = "10/minute"
    rate_limit_signals: str = "15/minute"
    rate_limit_signals_burst: str = "5/10seconds"
    rate_limit_chat: str = "30/minute"
    rate_limit_chat_burst: str = "10/10seconds"
    rate_limit_public: str = "30/minute"
    rate_limit_user: str = "60/minute"
    rate_limit_user_burst: str = "10/10seconds"
    rate_limit_backtest: str = "5/minute"

    # ── Data Paths ───────────────────────────────────────────────────
    knowledge_dir: str = "../knowledge"
    historical_data_dir: str = "../historical_data"


# Singleton instance
settings = Settings()