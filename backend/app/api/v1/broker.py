"""Broker integration router (AngelOne)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.models.schemas import AngelOneCredentials, AngelOneStatusResponse
from app.core.security import encrypt_value, decrypt_value
from app.db.repositories import repo

router = APIRouter(prefix="/api/angelone", tags=["broker"])


@router.post("/login", response_model=dict)
def angelone_login(
    creds: AngelOneCredentials,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    from app.services.broker import get_broker_feed

    feed = get_broker_feed()
    result = feed.login(
        api_key=creds.api_key,
        client_code=creds.client_code,
        pin=creds.pin,
        totp_secret=creds.totp_secret,
    )
    if result["status"] == "success":
        repo.broker.save(db, {
            "api_key": creds.api_key,
            "client_code": creds.client_code,
            "pin": creds.pin,
            "totp_secret": creds.totp_secret,
            "session_token": result.get("session_token"),
            "refresh_token": result.get("refresh_token"),
            "feed_token": result.get("feed_token"),
        })
        return {"status": "success", "client_code": creds.client_code}
    else:
        raise HTTPException(status_code=400, detail=result.get("message", "Login failed"))


@router.get("/status", response_model=AngelOneStatusResponse)
def angelone_status(
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    from app.services.broker import get_broker_feed
    from app.db.models import AngelOneSession

    feed = get_broker_feed()
    connected = feed.is_authorized(force_check=True)
    # Only fetch non-sensitive columns — never decrypt PIN/TOTP just for a status check
    row = db.query(AngelOneSession).first()
    return {
        "connected": connected,
        "client_code": feed.client_code or (row.client_code if row else ""),
        "credentials_saved": bool(row and row.pin_encrypted),
    }
