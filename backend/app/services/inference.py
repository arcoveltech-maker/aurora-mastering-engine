"""AuroraNet inference + heuristic fallback.

NORMALIZATION_VALIDATED = False — AuroraNet ML inference blocked until dataset
normalisation is validated. All callers receive heuristic predictions.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.analysis import AudioFeatures

logger = logging.getLogger("aurora.inference")

# ── IMMUTABLE CONSTRAINT ──────────────────────────────────────────────────────
NORMALIZATION_VALIDATED = False  # DO NOT CHANGE UNTIL VALIDATION COMPLETE
# ─────────────────────────────────────────────────────────────────────────────

GENRE_DR_TARGETS: dict[str, float] = {
    "pop": 8, "rock": 9, "hip-hop": 7, "r&b": 7, "edm": 6, "house": 6,
    "techno": 6, "jazz": 12, "acoustic": 11, "classical": 16, "orchestral": 18,
    "metal": 7, "lo-fi": 9, "ambient": 14, "afrobeat": 8, "latin": 8, "world": 10,
}

STREAMING_LUFS_TARGET = -14.0


def compute_heuristic_macros(features: "AudioFeatures") -> dict[str, float]:
    """
    Rule-based macro prediction when ML inference is blocked.
    Returns 12 macros in [0, 1] range (0 = min, 1 = max effect).
    """
    logger.warning(
        "heuristic_fallback: NORMALIZATION_VALIDATED=False, using rule-based macros"
    )

    macros: dict[str, float] = {}

    # EQ — compensate spectral imbalance
    macros["eq_low"]      = 0.5 + (0.25 - features.bass_ratio)     * 1.5
    macros["eq_mid"]      = 0.5
    macros["eq_high"]     = 0.5 + (0.40 - features.brightness)     * 1.0
    macros["eq_presence"] = 0.5 + (0.20 - features.presence_ratio) * 2.0

    # Compression — more for highly dynamic material
    dr = getattr(features, "dynamic_range", 10.0)
    macros["compression"] = float(min(0.8, dr / 20.0))

    # Saturation — gentle for harmonically rich material
    hr = getattr(features, "harmonic_ratio", 0.6)
    macros["saturation"] = 0.15 if hr > 0.75 else 0.35

    # Stereo width
    sw = getattr(features, "stereo_width", 0.5)
    macros["stereo_width"] = float(0.5 + (0.55 - sw) * 0.6)

    # Transients
    cf = getattr(features, "crest_factor", 10.0)
    macros["transient_attack"]  = float(min(0.75, cf / 20.0))
    macros["transient_sustain"] = 0.5

    # Air / Warmth
    macros["air"]    = float(0.5 - features.air_ratio  * 3.0)
    macros["warmth"] = 0.35 if features.bass_ratio < 0.20 else 0.25

    # Loudness target — bridge from current to -14 LUFS
    current = getattr(features, "integrated_lufs", -18.0)
    macros["loudness_target"] = float(
        max(0.0, min(1.0, (STREAMING_LUFS_TARGET - current + 10.0) / 20.0))
    )

    # Clamp all to [0, 1]
    return {k: float(max(0.0, min(1.0, v))) for k, v in macros.items()}


async def predict_macros(
    features: "AudioFeatures",
    genre: str | None = None,
) -> dict[str, float]:
    """
    Main inference entry point.
    Always uses heuristic until NORMALIZATION_VALIDATED=True.
    """
    if not NORMALIZATION_VALIDATED:
        return compute_heuristic_macros(features)

    # Future: load AuroraNet, run ONNX inference
    raise NotImplementedError("ML inference blocked until NORMALIZATION_VALIDATED=True")
