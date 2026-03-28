"""
Aurora security utilities: JWT (RS256), bcrypt, Redis token store.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from passlib.context import CryptContext
import redis.asyncio as aioredis

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# Cookie constants
# ---------------------------------------------------------------------------
COOKIE_ACCESS = "aurora_access_token"
COOKIE_REFRESH = "aurora_refresh_token"
COOKIE_KWARGS = {
    "httponly": True,
    "secure": True,
    "samesite": "strict",
    "path": "/",
}

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------
ALGORITHM = getattr(settings, "JWT_ALGORITHM", "RS256")
ACCESS_TOKEN_EXPIRE = timedelta(hours=1)
REFRESH_TOKEN_EXPIRE = timedelta(days=7)


def _load_private_key():
    try:
        private_key_path = getattr(settings, "JWT_PRIVATE_KEY_PATH", None)
        if private_key_path:
            with open(private_key_path, "rb") as f:
                return serialization.load_pem_private_key(f.read(), password=None)
        private_key_pem = getattr(settings, "JWT_PRIVATE_KEY", None)
        if private_key_pem:
            return serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    except Exception:
        pass
    # Generate ephemeral key for dev if not configured
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _load_public_key():
    priv = _load_private_key()
    return priv.public_key()


def _private_pem() -> bytes:
    return _load_private_key().private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )


def _public_pem() -> bytes:
    return _load_public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )


class TokenPayload:
    def __init__(self, sub: str, role: str, tier: str, jti: str, token_type: str):
        self.sub = sub
        self.role = role
        self.tier = tier
        self.jti = jti
        self.type = token_type


def create_access_token(user_id: str, role: str, tier: str) -> str:
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "tier": tier,
        "jti": jti,
        "type": "access",
        "iat": now,
        "exp": now + ACCESS_TOKEN_EXPIRE,
    }
    return jwt.encode(payload, _private_pem(), algorithm=ALGORITHM)


def create_refresh_token(user_id: str, role: str, tier: str) -> tuple[str, str]:
    """Returns (token, jti)"""
    jti = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "tier": tier,
        "jti": jti,
        "type": "refresh",
        "iat": now,
        "exp": now + REFRESH_TOKEN_EXPIRE,
    }
    token = jwt.encode(payload, _private_pem(), algorithm=ALGORITHM)
    return token, jti


def _decode_token(token: str) -> dict:
    return jwt.decode(token, _public_pem(), algorithms=[ALGORITHM])


def verify_access_token(token: str) -> Optional[TokenPayload]:
    try:
        data = _decode_token(token)
        if data.get("type") != "access":
            return None
        return TokenPayload(
            sub=data["sub"],
            role=data.get("role", "user"),
            tier=data.get("tier", "trial"),
            jti=data["jti"],
            token_type="access",
        )
    except jwt.ExpiredSignatureError:
        return None
    except jwt.PyJWTError:
        return None


def verify_refresh_token(token: str) -> Optional[TokenPayload]:
    try:
        data = _decode_token(token)
        if data.get("type") != "refresh":
            return None
        return TokenPayload(
            sub=data["sub"],
            role=data.get("role", "user"),
            tier=data.get("tier", "trial"),
            jti=data["jti"],
            token_type="refresh",
        )
    except jwt.PyJWTError:
        return None


# ---------------------------------------------------------------------------
# Redis token store
# ---------------------------------------------------------------------------
_REFRESH_PREFIX = "aurora:refresh:"
_BLOCKLIST_PREFIX = "aurora:jti_block:"
_ALL_REFRESH_PREFIX = "aurora:user_refresh:"


async def store_refresh_token(redis: aioredis.Redis, user_id: str, jti: str) -> None:
    ttl = int(REFRESH_TOKEN_EXPIRE.total_seconds())
    await redis.setex(f"{_REFRESH_PREFIX}{jti}", ttl, str(user_id))
    await redis.sadd(f"{_ALL_REFRESH_PREFIX}{user_id}", jti)
    await redis.expire(f"{_ALL_REFRESH_PREFIX}{user_id}", ttl)


async def verify_refresh_token_stored(redis: aioredis.Redis, user_id: str, jti: str) -> bool:
    val = await redis.get(f"{_REFRESH_PREFIX}{jti}")
    if val is None:
        return False
    if isinstance(val, bytes):
        val = val.decode()
    return val == str(user_id)


async def revoke_refresh_token(redis: aioredis.Redis, user_id: str, jti: str) -> None:
    await redis.delete(f"{_REFRESH_PREFIX}{jti}")
    await redis.srem(f"{_ALL_REFRESH_PREFIX}{user_id}", jti)


async def revoke_all_refresh_tokens(redis: aioredis.Redis, user_id: str) -> None:
    key = f"{_ALL_REFRESH_PREFIX}{user_id}"
    jtis = await redis.smembers(key)
    if jtis:
        pipe = redis.pipeline()
        for jti in jtis:
            jti_str = jti.decode() if isinstance(jti, bytes) else jti
            pipe.delete(f"{_REFRESH_PREFIX}{jti_str}")
        pipe.delete(key)
        await pipe.execute()


async def blocklist_jti(redis: aioredis.Redis, jti: str, ttl_seconds: int = 3600) -> None:
    await redis.setex(f"{_BLOCKLIST_PREFIX}{jti}", ttl_seconds, "1")


async def is_jti_blocked(redis: aioredis.Redis, jti: str) -> bool:
    val = await redis.get(f"{_BLOCKLIST_PREFIX}{jti}")
    return val is not None
