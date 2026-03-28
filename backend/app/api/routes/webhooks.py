"""
Stripe webhook handler.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_redis
from app.core.config import settings
from app.core.errors import AuroraHTTPException
from app.services import crud
import redis.asyncio as aioredis

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger("aurora.webhooks")


async def _idempotency_check(redis: aioredis.Redis, event_id: str) -> bool:
    key = f"aurora:stripe_event:{event_id}"
    result = await redis.set(key, "1", ex=86400, nx=True)
    return result is True  # True = first time, False = duplicate


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")

    webhook_secret = settings.STRIPE_WEBHOOK_SECRET
    if not webhook_secret:
        raise AuroraHTTPException("AURORA-E703", "Webhook secret not configured", status_code=400)

    try:
        event = stripe.Webhook.construct_event(payload, sig, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise AuroraHTTPException("AURORA-E703", status_code=400)
    except Exception as e:
        logger.error("Webhook parse error: %s", e)
        raise AuroraHTTPException("AURORA-E900", status_code=400)

    if not await _idempotency_check(redis, event["id"]):
        logger.info("Duplicate Stripe event %s — skipping", event["id"])
        return {"received": True}

    try:
        event_type = event["type"]
        data = event["data"]["object"]

        if event_type == "customer.subscription.created":
            await _handle_subscription_created(db, data)
        elif event_type == "customer.subscription.updated":
            await _handle_subscription_updated(db, data)
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(db, data)
        elif event_type == "invoice.payment_succeeded":
            await _handle_payment_succeeded(db, data)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, data)
        elif event_type == "customer.subscription.trial_will_end":
            logger.info("Trial ending for customer %s", data.get("customer"))
        else:
            logger.debug("Unhandled event type: %s", event_type)
    except Exception as e:
        logger.exception("Error handling Stripe event %s: %s", event["id"], e)
        return {"received": True, "error": str(e)}

    return {"received": True}


async def _get_user_by_customer_id(db: AsyncSession, customer_id: str):
    """Find user by Stripe customer ID via subscription."""
    from sqlalchemy import select
    from app.models.subscription import Subscription
    from app.models.user import User
    result = await db.execute(
        select(User).join(Subscription, Subscription.user_id == User.id)
        .where(Subscription.stripe_customer_id == customer_id)
    )
    return result.scalar_one_or_none()


async def _handle_subscription_created(db: AsyncSession, data: dict):
    customer_id = data.get("customer")
    user = await _get_user_by_customer_id(db, customer_id)
    if not user:
        logger.warning("No user found for Stripe customer %s", customer_id)
        return
    tier = _price_to_tier(
        data.get("items", {}).get("data", [{}])[0].get("price", {}).get("id", "")
    )
    sub = await crud.get_subscription(db, user_id=str(user.id))
    if sub:
        from app.models.enums import SubscriptionState, SubscriptionTier
        sub.tier = SubscriptionTier(tier)
        sub.state = SubscriptionState.ACTIVE_ARTIST if tier == "artist" else (
            SubscriptionState.ACTIVE_PRO if tier == "pro" else SubscriptionState.ACTIVE_ENTERPRISE
        )
        sub.stripe_subscription_id = data.get("id")
        period_end = data.get("current_period_end")
        if period_end:
            sub.billing_period_end = datetime.fromtimestamp(period_end, timezone.utc)
        await db.flush()


async def _handle_subscription_updated(db: AsyncSession, data: dict):
    await _handle_subscription_created(db, data)


async def _handle_subscription_deleted(db: AsyncSession, data: dict):
    customer_id = data.get("customer")
    user = await _get_user_by_customer_id(db, customer_id)
    if not user:
        return
    sub = await crud.get_subscription(db, user_id=str(user.id))
    if sub:
        from app.models.enums import SubscriptionState
        sub.state = SubscriptionState.CANCELED
        await db.flush()


async def _handle_payment_succeeded(db: AsyncSession, data: dict):
    customer_id = data.get("customer")
    user = await _get_user_by_customer_id(db, customer_id)
    if not user:
        return
    sub = await crud.get_subscription(db, user_id=str(user.id))
    if sub:
        from app.models.enums import SubscriptionState, SubscriptionTier
        tier = sub.tier
        if tier == SubscriptionTier.ARTIST:
            sub.state = SubscriptionState.ACTIVE_ARTIST
        elif tier == SubscriptionTier.PRO:
            sub.state = SubscriptionState.ACTIVE_PRO
        elif tier == SubscriptionTier.ENTERPRISE:
            sub.state = SubscriptionState.ACTIVE_ENTERPRISE
        await db.flush()


async def _handle_payment_failed(db: AsyncSession, data: dict):
    customer_id = data.get("customer")
    user = await _get_user_by_customer_id(db, customer_id)
    if not user:
        return
    sub = await crud.get_subscription(db, user_id=str(user.id))
    if sub:
        from app.models.enums import SubscriptionState
        sub.state = SubscriptionState.PAST_DUE
        await db.flush()


def _price_to_tier(price_id: str) -> str:
    artist_id = settings.STRIPE_PRICE_ARTIST_ID or ""
    pro_id = settings.STRIPE_PRICE_PRO_ID or ""
    if price_id == artist_id:
        return "artist"
    if price_id == pro_id:
        return "pro"
    return "trial"
