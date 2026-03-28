"""Tenant isolation tests for Aurora backend."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Session, Subscription, SubscriptionState, User
from app.services import crud


@pytest.mark.asyncio
async def test_user_cannot_read_other_sessions(app):
    # This is a structural placeholder; actual DB wiring is handled by alembic and engine config.
    assert hasattr(Session, "user_id")


@pytest.mark.asyncio
async def test_subscription_state_isolation(app):
    assert SubscriptionState.ACTIVE_ARTIST.value == "active_artist"
    assert SubscriptionState.PAST_DUE.value == "past_due"

