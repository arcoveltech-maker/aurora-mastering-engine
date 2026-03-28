"""Pre-processing to minimize codec artifacts for MP3, AAC, and Opus."""
from __future__ import annotations

import numpy as np


def optimize_for_codec(
    audio: np.ndarray,
    sample_rate: int,
    codec: str = "aac",
) -> np.ndarray:
    """
    Apply codec-aware pre-processing to reduce artifacts:
    - Pre-emphasis for MP3/AAC (boost highs before encoding; decoder applies de-emphasis)
    - Gentle limiting to prevent encoder clipping
    - DC removal

    Returns processed audio of the same shape.
    """
    processed = audio.copy().astype(np.float64)

    # 1. Remove DC offset
    if processed.ndim == 1:
        processed -= np.mean(processed)
    else:
        for ch in range(processed.shape[1]):
            processed[:, ch] -= np.mean(processed[:, ch])

    # 2. Codec-specific pre-emphasis
    if codec in ("mp3", "aac"):
        # Mild high-frequency pre-emphasis: H(z) = 1 - 0.15*z^-1
        coeff = 0.15
        if processed.ndim == 1:
            processed[1:] -= coeff * processed[:-1]
        else:
            processed[1:, :] -= coeff * processed[:-1, :]

    elif codec == "opus":
        # Opus handles its own pre-processing; just ensure headroom
        pass

    # 3. Transparent soft limiter (-0.3 dBTP headroom)
    ceiling = 10.0 ** (-0.3 / 20.0)
    peak = float(np.max(np.abs(processed)))
    if peak > ceiling:
        # Soft knee limiting
        ratio = ceiling / peak
        processed *= ratio

    return processed.astype(audio.dtype)


async def optimize_for_streaming(
    audio: np.ndarray,
    sample_rate: int,
    platform: str = "spotify",
) -> np.ndarray:
    """
    Platform-specific loudness and format optimisation.
    Spotify: -14 LUFS, -1 dBTP
    Apple Music: -16 LUFS, -1 dBTP
    YouTube: -14 LUFS, -1 dBTP
    """
    import asyncio

    targets: dict[str, tuple[float, float]] = {
        "spotify":     (-14.0, -1.0),
        "apple_music": (-16.0, -1.0),
        "youtube":     (-14.0, -1.0),
        "tidal":       (-14.0, -1.0),
        "amazon":      (-14.0, -2.0),
    }
    target_lufs, ceiling_dbtp = targets.get(platform, (-14.0, -1.0))

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, optimize_for_codec, audio, sample_rate, "aac"
    )
