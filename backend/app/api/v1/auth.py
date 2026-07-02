"""Authentication router."""
from __future__ import annotations

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

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    request: Request,
    response: Response,
    db: Session = DbDep,
) -> dict:
    u = req.username.strip()
    p = req.password.strip()

    # Single-code login (no username or generic username)
    if not u or u.lower() in ("code", "login", "admin", "apex_head_quant"):
        matched_user, user_obj = user_registry.authenticate_by_code(p)
        if matched_user:
            u = matched_user
        else:
            # Fallback admin check
            user_obj = user_registry.authenticate("apex_head_quant", p)
            if user_obj:
                u = "apex_head_quant"
    else:
        user_obj = user_registry.authenticate(u, p)

    if not user_obj:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid access code or credentials")

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
async def verify(token: str = Depends(lambda r: get_token_from_request(r))) -> dict:
    from fastapi import HTTPException
    from app.core.security import decode_access_token

    if not token or not decode_access_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"status": "valid", "message": "Token is valid"}
