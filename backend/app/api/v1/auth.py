"""Authentication router."""
from __future__ import annotations

import os

from fastapi import APIRouter, Request, Response, Depends
from sqlalchemy.orm import Session

from app.api.deps import DbDep, get_user_or_ip
from app.core.config import settings
from app.core.security import (
    user_registry,
    create_access_token,
    get_token_from_request,
    generate_csrf_token,
    revoke_access_token,
    CsrfDep,
)
from app.models.schemas import LoginRequest, LoginResponse, StatusResponse

from app.core.limiter import limiter
from fastapi import APIRouter, Request, Response, Depends, Body

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit(os.getenv("RATE_LIMIT_AUTH", "5/minute"))
async def login(
    request: Request,
    response: Response,
    db: Session = DbDep,
) -> dict:
    """Authenticate and set the session cookie.

    Deliberately CSRF-exempt (documented exemption): at login time no prior
    authenticated session cookie is in play for this origin to ride, and the
    response itself replaces any cookie value, so a cross-site login CSRF has
    no session-mutation surface worth gating (login-CSRF risk accepted).
    """
    from fastapi import HTTPException

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    try:
        req = LoginRequest.model_validate(body)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))

    username, user_obj = None, None
    if req.username and req.username != "code":
        user_obj = user_registry.authenticate(req.username, req.password)
        if user_obj:
            username = req.username
    else:
        username, user_obj = user_registry.authenticate_by_code(req.password)

    if not username or not user_obj:
        raise HTTPException(status_code=401, detail="Invalid access code")

    token = create_access_token({"sub": username})
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key="apt_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.session_ttl,
    )
    response.set_cookie(
        key="apt_csrf",
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="none",
        max_age=settings.session_ttl,
    )
    return {
        "csrf_token": csrf_token,
        "username": username,
        "role": user_obj.get("role", "Quant Trader"),
        "clearance": user_obj.get("clearance", "LEVEL_2_SECURE"),
        "expires_in": settings.session_ttl,
    }


@router.post("/logout", response_model=StatusResponse, dependencies=[CsrfDep])
@limiter.limit(os.getenv("RATE_LIMIT_AUTH", "5/minute"))
async def logout(request: Request, response: Response) -> dict:
    token = get_token_from_request(request)
    if token:
        revoke_access_token(token)
    response.delete_cookie(
        key="apt_token",
        httponly=True,
        secure=True,
        samesite="none",
    )
    response.delete_cookie(
        key="apt_csrf",
        httponly=False,
        secure=True,
        samesite="none",
    )
    return {"status": "logged out", "message": "Session terminated"}


@router.get("/auth/verify")
@limiter.limit(os.getenv("RATE_LIMIT_AUTH", "5/minute"))
async def verify(request: Request, response: Response) -> dict:
    from fastapi import HTTPException
    from app.core.security import decode_access_token, get_token_from_request

    token = get_token_from_request(request)
    if not token or not decode_access_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")

    csrf_token = request.cookies.get("apt_csrf") or generate_csrf_token()
    response.set_cookie(
        key="apt_csrf",
        value=csrf_token,
        httponly=False,
        secure=True,
        samesite="none",
        max_age=settings.session_ttl,
    )
    return {"status": "valid", "message": "Token is valid", "csrf_token": csrf_token}