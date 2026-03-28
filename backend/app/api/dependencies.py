"""
FastAPI dependency injection helpers.
"""
from __future__ import annotations

import logging
from typing import Optional

import redis.asyncio as aioredis
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.errors import AuroraHTTPException
from app.core.security import (
    COOKIE_ACCESS,
    is_jti_blocked,
    verify_access_token,
)
from app.models.user import User
from app.services import crud

logger = logging.getLogger("aurora.deps")

# ---------------------------------------------------------------------------
# Redis singleton
# ---------------------------------------------------------------------------
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = await aioredis.from_url(
            settings.REDIS_URL, encoding="utf-8", decode_responses=False
        )
    return _redis_client


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------
_bearer = HTTPBearer(auto_error=False)


def _extract_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> Optional[str]:
    # 1. Prefer HttpOnly cookie
    cookie_token = request.cookies.get(COOKIE_ACCESS)
    if cookie_token:
        return cookie_token
    # 2. Fall back to Bearer header
    if credentials:
        return credentials.credentials
    return None


# ---------------------------------------------------------------------------
# Current user dependency
# ---------------------------------------------------------------------------
async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> User:
    token = _extract_token(request, credentials)
    if not token:
        raise AuroraHTTPException("AURORA-E003", "Authentication required", status_code=401)

    payload = verify_access_token(token)
    if payload is None:
        raise AuroraHTTPException("AURORA-E002", "Token expired or invalid", status_code=401)

    # Check JTI blocklist
    if await is_jti_blocked(redis, payload.jti):
        raise AuroraHTTPException("AURORA-E003", "Token has been revoked", status_code=401)

    user = await crud.get_user_by_id(db, user_id=payload.sub)
    if user is None:
        raise AuroraHTTPException("AURORA-E001", "User not found", status_code=401)

    # Set RLS context
    try:
        from sqlalchemy import text
        await db.execute(
            text("SELECT set_config('app.current_user_id', :uid, true)"),
            {"uid": str(user.id)},
        )
    except Exception:
        pass  # Non-Postgres envs

    return user


async def get_current_user_id(
    current_user: User = Depends(get_current_user),
) -> str:
    return str(current_user.id)


def require_role(*roles: str):
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        user_role = current_user.role.value if hasattr(current_user.role, "value") else current_user.role
        if user_role not in roles:
            raise AuroraHTTPException(
                "AURORA-E006",
                f"Role '{user_role}' is not permitted. Required: {roles}",
                status_code=403,
            )
        return current_user
    return _check


async def require_email_verified(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_email_verified:
        raise AuroraHTTPException("AURORA-E005", status_code=403)
    return current_user


async def require_active_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    sub = await crud.get_subscription(db, user_id=str(current_user.id))
    if sub is None:
        raise AuroraHTTPException("AURORA-B005", status_code=402)
    from app.models.enums import SubscriptionState
    if sub.state in (SubscriptionState.CANCELED, SubscriptionState.EXPIRED, SubscriptionState.SUSPENDED):
        raise AuroraHTTPException("AURORA-B005", "Subscription canceled", status_code=402)
    return current_user
