"""Broker integration router (AngelOne)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.models.schemas import AngelOneCredentials, AngelOneStatusResponse
from app.core.security import encrypt_value, decrypt_value
from app.db.repositories import repo

from app.core.limiter import limiter
import os

RATE_LIMIT_BROKER = os.getenv("RATE_LIMIT_BROKER", "3/minute")

from fastapi import APIRouter, Request, Response, Depends, HTTPException, Body

router = APIRouter(prefix="/api/angelone", tags=["broker"])


@router.post("/login", response_model=dict)
@limiter.limit(RATE_LIMIT_BROKER)
async def angelone_login(
    request: Request,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    body = await request.json()
    creds = AngelOneCredentials.model_validate(body)
    from app.services.broker import get_broker_feed

    try:
        feed = get_broker_feed()
        result = feed.login(
            api_key=creds.api_key,
            client_code=creds.client_code,
            pin=creds.pin,
            totp_secret=creds.totp_secret,
        )
        if isinstance(result, dict) and result.get("status") == "success":
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
            msg = result.get("message", "Login failed") if isinstance(result, dict) else "Login failed"
            raise HTTPException(status_code=400, detail=msg)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"AngelOne login error: {str(e)}")


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