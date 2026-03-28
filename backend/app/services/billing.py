"""
Stripe billing service.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AuroraHTTPException
from app.models.user import User
from app.services import crud

try:
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY or ""
except ImportError:
    stripe = None  # type: ignore


def _get_stripe():
    if stripe is None:
        raise AuroraHTTPException("AURORA-E701", "Stripe library not installed")
    if not settings.STRIPE_SECRET_KEY:
        raise AuroraHTTPException("AURORA-E701", "Stripe not configured")
    return stripe


def _tier_price_map() -> dict:
    return {
        "artist": settings.STRIPE_PRICE_ARTIST_ID or "",
        "pro": settings.STRIPE_PRICE_PRO_ID or "",
    }


class StripeService:
    async def get_or_create_stripe_customer(self, user: User, db: AsyncSession) -> str:
        s = _get_stripe()
        sub = await crud.get_subscription(db, user_id=str(user.id))
        if sub and sub.stripe_customer_id:
            return sub.stripe_customer_id
        try:
            customer = s.Customer.create(
                email=user.email,
                name=user.display_name,
                metadata={"user_id": str(user.id)},
            )
            if sub:
                sub.stripe_customer_id = customer["id"]
                await db.flush()
            return customer["id"]
        except Exception as e:
            raise AuroraHTTPException("AURORA-E701", str(e))

    async def create_checkout_session(self, user: User, tier: str, db: AsyncSession) -> str:
        s = _get_stripe()
        price_id = _tier_price_map().get(tier)
        if not price_id:
            raise AuroraHTTPException("AURORA-E701", f"Invalid tier or unconfigured price: {tier}")
        customer_id = await self.get_or_create_stripe_customer(user, db)
        try:
            session = s.checkout.Session.create(
                customer=customer_id,
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=f"https://{settings.DOMAIN}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"https://{settings.DOMAIN}/billing/cancel",
            )
            return session["url"]
        except Exception as e:
            raise AuroraHTTPException("AURORA-E701", str(e))

    async def create_portal_session(self, user: User, db: AsyncSession) -> str:
        s = _get_stripe()
        customer_id = await self.get_or_create_stripe_customer(user, db)
        try:
            portal = s.billing_portal.Session.create(
                customer=customer_id,
                return_url=f"https://{settings.DOMAIN}/billing",
            )
            return portal["url"]
        except Exception as e:
            raise AuroraHTTPException("AURORA-E701", str(e))

    async def cancel_subscription_at_period_end(self, user: User, db: AsyncSession) -> None:
        s = _get_stripe()
        sub = await crud.get_subscription(db, user_id=str(user.id))
        if not sub or not sub.stripe_subscription_id:
            raise AuroraHTTPException("AURORA-E702")
        try:
            s.Subscription.modify(sub.stripe_subscription_id, cancel_at_period_end=True)
        except Exception as e:
            raise AuroraHTTPException("AURORA-E701", str(e))
