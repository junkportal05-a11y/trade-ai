"""App core configuration using pydantic-settings."""
from __future__ import annotations

import secrets
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    admin_key: str = Field(default_factory=lambda: secrets.token_hex(24), alias="ADMIN_KEY")
    session_ttl: int = Field(default=8 * 3600, alias="SESSION_TTL")  # 8 hours
    algorithm: str = "HS256"

    # ── Broker ───────────────────────────────────────────────────────
    angel_api_key: str | None = Field(default=None, alias="ANGEL_API_KEY")
    angel_client_code: str | None = Field(default=None, alias="ANGEL_CLIENT_CODE")
    angel_pin: str | None = Field(default=None, alias="ANGEL_PIN")
    angel_totp_secret: str | None = Field(default=None, alias="ANGEL_TOTP_SECRET")

    # ── AI ───────────────────────────────────────────────────────────
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    news_api_key: str | None = Field(default=None, alias="NEWS_API_KEY")

    # ── CORS ─────────────────────────────────────────────────────────
    allowed_origins: str = (
        "http://localhost:5173,http://localhost:3000,"
        "http://127.0.0.1:5173,http://127.0.0.1:3000,"
        "https://trade-ai-beta.vercel.app,https://frontend-two-tau-82.vercel.app"
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_origins(cls, v: str | list) -> str:
        if isinstance(v, list):
            return ",".join(v)
        return v

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

    # ── Rate Limits ──────────────────────────────────────────────────
    rate_limit_login: str = "10/minute"
    rate_limit_signals: str = "15/minute"
    rate_limit_signals_burst: str = "5/10seconds"
    rate_limit_chat: str = "30/minute"
    rate_limit_chat_burst: str = "10/10seconds"

    # ── Data Paths ───────────────────────────────────────────────────
    knowledge_dir: str = "../knowledge"
    historical_data_dir: str = "../historical_data"


# Singleton instance
settings = Settings()
