# Pydantic models for ApexTrade API

from __future__ import annotations
from typing import Optional
from fastapi import Header
from pydantic import BaseModel, Field

class AdminKeyParams(BaseModel):
    x_admin_key: str = Field(..., alias="X-Admin-Key", header=True)

class AngelOneCredentials(BaseModel):
    api_key: str
    client_code: str
    pin: str
    totp_secret: str