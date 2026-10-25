"""AI Chat router."""
from __future__ import annotations

import base64
import json
from typing import Any
from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import DbDep, SessionDep
from app.models.schemas import ChatRequest, ChatResponse, ChartAnalysisRequest, ChartAnalysisResponse
from app.core.config import settings
from app.core.limiter import limiter

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat", response_model=ChatResponse)
@limiter.limit(settings.rate_limit_user)
async def chat(
    req: ChatRequest,
    request: Request,
    db: Session = DbDep,
    _=SessionDep,
) -> dict:
    from app.services.chat import get_chat_reply

    symbol = (req.context or {}).get("symbol", "the market")
    price = (req.context or {}).get("price")
    chg_pct = (req.context or {}).get("changePct")

    return get_chat_reply(req, symbol, price, chg_pct)


# JSON endpoint for base64 image analysis
@router.post("/chat/chart", response_model=ChartAnalysisResponse)
async def analyze_chart_json(
    req: ChartAnalysisRequest,
    request: Request,
    _=SessionDep,
) -> ChartAnalysisResponse:
    """
    Analyze a candlestick chart image using Gemini 2.0 Flash multimodal.
    
    Accepts JSON with base64 encoded image:
    {
        "image_base64": "base64_encoded_png_or_jpeg",
        "symbol": "NIFTY"  // optional
    }
    """
    from app.services.chat import _analyze_chart_base64
    
    if not req.image_base64:
        raise HTTPException(status_code=400, detail="image_base64 is required")
    
    result = _analyze_chart_base64(req.image_base64, req.symbol or "")
    return ChartAnalysisResponse(**result)


# Multipart file upload endpoint - use response_model=None to avoid UploadFile validation issues
# Use Any type for file parameter to avoid Pydantic field creation
@router.post("/chat/chart/upload", response_model=None)
@limiter.limit(settings.rate_limit_user)
async def analyze_chart_upload(
    request: Request,
    file: Any = File(...),
    _=SessionDep,
) -> JSONResponse:
    """
    Analyze a candlestick chart image using Gemini 2.0 Flash multimodal.
    
    Accepts multipart/form-data with file upload (PNG/JPEG).
    """
    from app.services.chat import _analyze_chart_base64
    
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(status_code=400, detail="File too large (max 10MB)")
    
    # Validate content type
    if file.content_type not in ("image/png", "image/jpeg", "image/jpg"):
        raise HTTPException(status_code=400, detail="Only PNG/JPEG images supported")
    
    image_b64 = base64.b64encode(content).decode("utf-8")
    result = _analyze_chart_base64(image_b64, "")
    return JSONResponse(content=result)