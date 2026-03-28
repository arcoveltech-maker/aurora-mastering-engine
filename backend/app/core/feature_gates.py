"""
Feature gate enforcement by subscription tier.
"""
from __future__ import annotations

from typing import Optional, Set

from app.core.errors import AuroraHTTPException
from app.models.enums import SubscriptionTier, SubscriptionState

# ---------------------------------------------------------------------------
# Tier feature matrix
# ---------------------------------------------------------------------------
TIER_FEATURES: dict[str, dict] = {
    SubscriptionTier.TRIAL: {
        "tracks_per_period": 3,
        "storage_bytes": 1 * 1024**3,  # 1 GB
        "export_formats": {"wav_16", "wav_24"},
        "qc_checks": 5,
        "reference_matching": False,
        "spatial_rendering": False,
        "ddp_export": False,
        "ddex_distribution": False,
        "collaboration": False,
        "collaboration_max_users": 0,
        "stem_separation": False,
        "spectral_repair": False,
        "codec_optimization": False,
        "custom_training": False,
        "priority_render": False,
        "api_access": False,
    },
    SubscriptionTier.ARTIST: {
        "tracks_per_period": 100,
        "storage_bytes": 5 * 1024**3,  # 5 GB
        "export_formats": {"wav_16", "wav_24", "mp3_320", "aac_256"},
        "qc_checks": 10,
        "reference_matching": True,
        "spatial_rendering": False,
        "ddp_export": False,
        "ddex_distribution": False,
        "collaboration": False,
        "collaboration_max_users": 0,
        "stem_separation": True,
        "spectral_repair": False,
        "codec_optimization": False,
        "custom_training": False,
        "priority_render": False,
        "api_access": False,
    },
    SubscriptionTier.PRO: {
        "tracks_per_period": 500,
        "storage_bytes": 50 * 1024**3,  # 50 GB
        "export_formats": {"wav_16", "wav_24", "wav_32f", "mp3_320", "aac_256", "flac", "ddp"},
        "qc_checks": 18,
        "reference_matching": True,
        "spatial_rendering": True,
        "ddp_export": True,
        "ddex_distribution": False,
        "collaboration": True,
        "collaboration_max_users": 3,
        "stem_separation": True,
        "spectral_repair": True,
        "codec_optimization": True,
        "custom_training": False,
        "priority_render": True,
        "api_access": False,
    },
    SubscriptionTier.ENTERPRISE: {
        "tracks_per_period": None,  # unlimited
        "storage_bytes": None,  # unlimited
        "export_formats": {"wav_16", "wav_24", "wav_32f", "mp3_320", "aac_256", "flac", "ddp", "ddex"},
        "qc_checks": 18,
        "reference_matching": True,
        "spatial_rendering": True,
        "ddp_export": True,
        "ddex_distribution": True,
        "collaboration": True,
        "collaboration_max_users": 8,
        "stem_separation": True,
        "spectral_repair": True,
        "codec_optimization": True,
        "custom_training": True,
        "priority_render": True,
        "api_access": True,
    },
}


def _get_features(tier: str) -> dict:
    return TIER_FEATURES.get(tier, TIER_FEATURES[SubscriptionTier.TRIAL])


def _check_active(sub_state: str) -> None:
    canceled_states = (
        SubscriptionState.CANCELED,
        SubscriptionState.PAST_DUE,
        SubscriptionState.EXPIRED,
        SubscriptionState.SUSPENDED,
    )
    if sub_state in canceled_states:
        raise AuroraHTTPException("AURORA-B005", "Active subscription required")


def require_feature(feature_name: str, user_tier: str, sub_state: str) -> None:
    _check_active(sub_state)
    features = _get_features(user_tier)
    if not features.get(feature_name, False):
        raise AuroraHTTPException(
            "AURORA-B001",
            f"Feature '{feature_name}' is not available on the {user_tier} plan",
        )


def require_tier(required_tier: str, user_tier: str, sub_state: str) -> None:
    _check_active(sub_state)
    tier_order = [
        SubscriptionTier.TRIAL,
        SubscriptionTier.ARTIST,
        SubscriptionTier.PRO,
        SubscriptionTier.ENTERPRISE,
    ]
    if tier_order.index(user_tier) < tier_order.index(required_tier):
        raise AuroraHTTPException(
            "AURORA-B001",
            f"This feature requires the {required_tier} plan or higher",
        )


def require_track_quota(tracks_used: int, user_tier: str, sub_state: str) -> None:
    _check_active(sub_state)
    limit = _get_features(user_tier)["tracks_per_period"]
    if limit is not None and tracks_used >= limit:
        raise AuroraHTTPException(
            "AURORA-B002",
            f"Track quota exceeded ({tracks_used}/{limit} this period)",
        )


def require_storage_quota(
    storage_used_bytes: int,
    file_size_bytes: int,
    user_tier: str,
    sub_state: str,
) -> None:
    _check_active(sub_state)
    limit = _get_features(user_tier)["storage_bytes"]
    if limit is not None and (storage_used_bytes + file_size_bytes) > limit:
        raise AuroraHTTPException(
            "AURORA-B003",
            f"Storage quota exceeded. Used: {storage_used_bytes / 1024**3:.1f}GB / {limit / 1024**3:.0f}GB",
        )


def require_export_format(fmt: str, user_tier: str, sub_state: str) -> None:
    _check_active(sub_state)
    allowed: Set[str] = _get_features(user_tier)["export_formats"]
    if fmt not in allowed:
        raise AuroraHTTPException(
            "AURORA-B004",
            f"Export format '{fmt}' is not available on the {user_tier} plan",
        )
