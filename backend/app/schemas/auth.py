"""Auth-related schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class GoogleOAuthRequest(BaseModel):
    id_token: str = Field(..., min_length=10)


class RefreshTokenRequest(BaseModel):
    refresh_token: str


