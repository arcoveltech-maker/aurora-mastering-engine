"""Application-wide database and domain enums."""

from __future__ import annotations

import enum


class SubscriptionState(str, enum.Enum):
    WAITLIST = "waitlist"
    TRIAL = "trial"
    TRIAL_EXPIRED = "trial_expired"
    ACTIVE_ARTIST = "active_artist"
    ACTIVE_PRO = "active_pro"
    ACTIVE_ENTERPRISE = "active_enterprise"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class SubscriptionTier(str, enum.Enum):
    TRIAL = "trial"
    ARTIST = "artist"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class RenderStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    ENGINEER = "engineer"
    REVIEWER = "reviewer"
    VIEWER = "viewer"
    API = "api"
    USER = "user"


class MacroSource(str, enum.Enum):
    MODEL = "model"
    HEURISTIC = "heuristic"
    MANUAL = "manual"


class LimiterMode(str, enum.Enum):
    TRANSPARENT = "transparent"
    PUNCHY = "punchy"
    DENSE = "dense"
    BROADCAST = "broadcast"
    VINYL = "vinyl"


class QCCheckStatus(str, enum.Enum):
    PASS = "pass_"
    FAIL = "fail"
    WARNING = "warning"
    REMEDIATED = "remediated"
    SKIPPED = "skipped"


class StemType(str, enum.Enum):
    LEAD_VOCALS = "lead_vocals"
    BACKING_VOCALS = "backing_vocals"
    BASS = "bass"
    KICK = "kick"
    SNARE = "snare"
    HIHATS = "hihats"
    CYMBALS = "cymbals"
    ROOM = "room"
    GUITAR = "guitar"
    PIANO = "piano"
    SYNTHS_PADS = "synths_pads"
    FX_ATMOSPHERE = "fx_atmosphere"

