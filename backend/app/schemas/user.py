"""Pydantic schemas for user and subscription."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.models.enums import SubscriptionState, SubscriptionTier, UserRole


class UserBase(BaseModel):
    email: EmailStr
    display_name: str = Field(..., max_length=255)

    model_config = {"from_attributes": True}


class UserCreate(UserBase):
    password: str = Field(min_length=12)


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=255)
    timezone: str | None = None

    model_config = {"from_attributes": True}


class UserResponse(UserBase):
    id: uuid.UUID
    role: UserRole
    is_email_verified: bool
    created_at: datetime
    updated_at: datetime


class SubscriptionResponse(BaseModel):
    user_id: uuid.UUID
    state: SubscriptionState
    tier: SubscriptionTier
    tracks_used_this_period: int
    storage_used_bytes: int
    tracks_limit: int | None
    storage_limit_bytes: int | None

    model_config = {"from_attributes": True}


class SubscriptionStateTransition(BaseModel):
    from_state: SubscriptionState
    to_state: SubscriptionState
    metadata: dict[str, Any] | None = None

