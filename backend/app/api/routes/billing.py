"""
Billing routes: checkout, portal, subscription, usage.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.services import crud
from app.services.billing import StripeService

router = APIRouter(prefix="/billing", tags=["billing"])
stripe_svc = StripeService()


class CheckoutRequest(BaseModel):
    tier: str


@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    url = await stripe_svc.create_checkout_session(current_user, body.tier, db)
    return {"checkout_url": url}


@router.post("/portal")
async def create_portal(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    url = await stripe_svc.create_portal_session(current_user, db)
    return {"portal_url": url}


@router.get("/subscription")
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await crud.get_subscription(db, user_id=str(current_user.id))
    if not sub:
        return {"tier": "trial", "state": "active"}
    tier = sub.tier.value if hasattr(sub.tier, "value") else sub.tier
    state = sub.state.value if hasattr(sub.state, "value") else sub.state
    return {
        "tier": tier,
        "state": state,
        "current_period_end": sub.billing_period_end.isoformat() if sub.billing_period_end else None,
    }


@router.get("/usage")
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await crud.get_subscription(db, user_id=str(current_user.id))
    tier = sub.tier.value if sub and hasattr(sub.tier, "value") else (sub.tier if sub else "trial")
    tracks_used = getattr(sub, "tracks_used_this_period", 0) or 0
    storage_used = getattr(sub, "storage_used_bytes", 0) or 0
    return {
        "tracks_used": tracks_used,
        "storage_used_bytes": storage_used,
        "tier": tier,
    }
