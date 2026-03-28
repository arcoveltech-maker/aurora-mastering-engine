"""
Authentication routes.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.core.database import get_db
from app.core.errors import AuroraHTTPException
from app.core.security import (
    COOKIE_ACCESS, COOKIE_KWARGS, COOKIE_REFRESH,
    create_access_token, create_refresh_token,
    hash_password, revoke_all_refresh_tokens, revoke_refresh_token,
    store_refresh_token, verify_password, verify_refresh_token,
    verify_refresh_token_stored,
)
from app.api.dependencies import get_current_user, get_redis
from app.models.user import User
from app.services import crud

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str

    @validator("password")
    def password_min_length(cls, v):
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

    @validator("new_password")
    def min_length(cls, v):
        if len(v) < 12:
            raise ValueError("Password must be at least 12 characters")
        return v


def _set_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(COOKIE_ACCESS, access_token, **COOKIE_KWARGS)
    response.set_cookie(COOKIE_REFRESH, refresh_token, **COOKIE_KWARGS)


def _clear_cookies(response: Response) -> None:
    response.delete_cookie(COOKIE_ACCESS, path="/")
    response.delete_cookie(COOKIE_REFRESH, path="/")


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if await crud.get_user_by_email(db, email=body.email):
        raise AuroraHTTPException("AURORA-E004")
    hashed = hash_password(body.password)
    user = await crud.create_user(
        db,
        email=body.email,
        password_hash=hashed,
        display_name=body.display_name,
    )
    await crud.create_subscription(db, user_id=str(user.id))
    return {"id": str(user.id), "email": user.email, "display_name": user.display_name}


@router.post("/login")
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    user = await crud.get_user_by_email(db, email=body.email)
    if not user or not verify_password(body.password, user.password_hash):
        raise AuroraHTTPException("AURORA-E001")
    sub = await crud.get_subscription(db, user_id=str(user.id))
    tier = sub.tier.value if sub and hasattr(sub.tier, "value") else (sub.tier if sub else "trial")
    role = user.role.value if hasattr(user.role, "value") else getattr(user, "role", "user")
    access_token = create_access_token(str(user.id), role, tier)
    refresh_token, jti = create_refresh_token(str(user.id), role, tier)
    await store_refresh_token(redis, str(user.id), jti)
    await crud.update_user(db, user_id=str(user.id), display_name=user.display_name)
    _set_cookies(response, access_token, refresh_token)
    return {"message": "Login successful"}


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    raw = request.cookies.get(COOKIE_REFRESH)
    if not raw:
        raise AuroraHTTPException("AURORA-E003", "Missing refresh token", status_code=401)
    payload = verify_refresh_token(raw)
    if not payload:
        raise AuroraHTTPException("AURORA-E002", status_code=401)
    if not await verify_refresh_token_stored(redis, payload.sub, payload.jti):
        raise AuroraHTTPException("AURORA-E003", "Token revoked", status_code=401)
    await revoke_refresh_token(redis, payload.sub, payload.jti)
    user = await crud.get_user_by_id(db, user_id=payload.sub)
    if not user:
        raise AuroraHTTPException("AURORA-E001", status_code=401)
    sub = await crud.get_subscription(db, user_id=str(user.id))
    tier = sub.tier.value if sub and hasattr(sub.tier, "value") else (sub.tier if sub else "trial")
    role = user.role.value if hasattr(user.role, "value") else getattr(user, "role", "user")
    access_token = create_access_token(str(user.id), role, tier)
    new_refresh, new_jti = create_refresh_token(str(user.id), role, tier)
    await store_refresh_token(redis, str(user.id), new_jti)
    _set_cookies(response, access_token, new_refresh)
    return {"message": "Tokens refreshed"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    redis: aioredis.Redis = Depends(get_redis),
):
    raw = request.cookies.get(COOKIE_REFRESH)
    if raw:
        payload = verify_refresh_token(raw)
        if payload:
            await revoke_refresh_token(redis, payload.sub, payload.jti)
    _clear_cookies(response)
    return {"message": "Logged out"}


@router.post("/logout-all")
async def logout_all(
    response: Response,
    current_user: User = Depends(get_current_user),
    redis: aioredis.Redis = Depends(get_redis),
):
    await revoke_all_refresh_tokens(redis, str(current_user.id))
    _clear_cookies(response)
    return {"message": "All sessions terminated"}


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await crud.get_subscription(db, user_id=str(current_user.id))
    tier = sub.tier.value if sub and hasattr(sub.tier, "value") else (sub.tier if sub else "trial")
    state = sub.state.value if sub and hasattr(sub.state, "value") else (sub.state if sub else "active")
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "display_name": current_user.display_name,
        "email_verified": current_user.is_email_verified,
        "subscription": {"tier": tier, "state": state} if sub else None,
    }


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not verify_password(body.old_password, current_user.password_hash):
        raise AuroraHTTPException("AURORA-E001", "Current password is incorrect", status_code=400)
    new_hash = hash_password(body.new_password)
    await crud.update_user(db, user_id=str(current_user.id), display_name=current_user.display_name)
    # Update password_hash directly since update_user doesn't support it yet
    current_user.password_hash = new_hash
    await db.flush()
    await revoke_all_refresh_tokens(redis, str(current_user.id))
    return {"message": "Password updated"}
