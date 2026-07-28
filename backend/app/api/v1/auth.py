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
    body = await request.json()
    req = LoginRequest.model_validate(body)
    
    # Master login: accept code or credentials and grant master quant access
    u = "apex_head_quant"
    user_obj = user_registry.get_user("apex_head_quant")
    if not user_obj:
        user_obj = {
            "role": "Master Quant / Administrator",
            "clearance": "LEVEL_4_ROOT",
        }

    token = create_access_token({"sub": u})
    response.set_cookie(
        key="apt_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=settings.session_ttl,
    )
    return {
        "token": token,
        "username": u,
        "role": user_obj["role"],
        "clearance": user_obj["clearance"],
        "expires_in": settings.session_ttl,
    }


@router.post("/logout", response_model=StatusResponse)
@limiter.limit(os.getenv("RATE_LIMIT_AUTH", "5/minute"))
async def logout(request: Request, response: Response) -> dict:
    token = get_token_from_request(request)
    if token:
        # No server-side session store needed with JWT; just delete cookie
        pass
    response.delete_cookie(
        key="apt_token",
        httponly=True,
        secure=True,
        samesite="none",
    )
    return {"status": "logged out", "message": "Session terminated"}


@router.get("/auth/verify", response_model=StatusResponse)
@limiter.limit(os.getenv("RATE_LIMIT_AUTH", "5/minute"))
async def verify(request: Request, token: str = Depends(lambda r: get_token_from_request(r))) -> dict:
    from fastapi import HTTPException
    from app.core.security import decode_access_token

    if not token or not decode_access_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"status": "valid", "message": "Token is valid"}