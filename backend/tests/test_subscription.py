"""Subscription state machine tests."""

from __future__ import annotations

from app.models.enums import SubscriptionState


def test_valid_transitions_enumerated():
    assert SubscriptionState.WAITLIST.value == "waitlist"
    assert SubscriptionState.TRIAL.value == "trial"
    assert SubscriptionState.ACTIVE_ARTIST.value == "active_artist"
    assert SubscriptionState.ACTIVE_PRO.value == "active_pro"
    assert SubscriptionState.ACTIVE_ENTERPRISE.value == "active_enterprise"

