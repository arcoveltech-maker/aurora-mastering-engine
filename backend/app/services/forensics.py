"""Forensic watermarking — inaudible provenance embedding.

Trial watermark   : audible (tone every 30s)  — free tier
Forensic watermark: inaudible (spread spectrum) — paid tiers
"""
from __future__ import annotations

import hashlib
import logging
import struct

import numpy as np

logger = logging.getLogger("aurora.forensics")

# Carrier frequency for spread-spectrum watermark (18–20 kHz, above most perception)
_WM_FREQ_LO = 18000.0
_WM_FREQ_HI = 20000.0
# Amplitude: inaudible when masking is active; should be validated per release
_WM_AMPLITUDE = 0.0003   # ~-70 dBFS


def embed_forensic_watermark(
    audio: np.ndarray,
    session_id: str,
    user_id: str,
    render_job_id: str,
    sample_rate: int = 48000,
) -> np.ndarray:
    """
    Embed an inaudible forensic watermark using spread-spectrum encoding
    in the 18–20 kHz psychoacoustically masked region.

    Payload: SHA-256 of session_id:user_id:render_job_id (256 bits)
    Encoding: BPSK modulation on a PN carrier
    """
    payload = f"{session_id}:{user_id}:{render_job_id}"
    payload_hash = hashlib.sha256(payload.encode()).digest()  # 32 bytes = 256 bits
    bits = [int(b) for byte in payload_hash for b in f"{byte:08b}"]

    wm = _generate_watermark(bits, sample_rate, len(audio))
    result = audio.copy().astype(np.float64)

    if result.ndim == 1:
        result += wm
    else:
        for ch in range(result.shape[1]):
            result[:, ch] = result[:, ch] + wm

    logger.info(
        "forensic_watermark_embedded: session=%s user=%s job=%s bits=%d",
        session_id, user_id, render_job_id, len(bits),
    )
    return result.astype(audio.dtype)


def _generate_watermark(bits: list[int], sample_rate: int, length: int) -> np.ndarray:
    """Generate spread-spectrum watermark signal."""
    t = np.arange(length) / sample_rate
    # PN sequence seed derived from first 4 bits
    rng = np.random.default_rng(seed=int("".join(str(b) for b in bits[:8]), 2))

    # Carrier: swept sinusoid in 18–20 kHz band
    carrier_freq = ((_WM_FREQ_LO + _WM_FREQ_HI) / 2)
    carrier = np.sin(2 * np.pi * carrier_freq * t)

    # Modulate with bits (BPSK)
    bit_duration = length // max(len(bits), 1)
    wm = np.zeros(length)
    for i, bit in enumerate(bits):
        start = i * bit_duration
        end   = min(start + bit_duration, length)
        phase = 0 if bit == 1 else np.pi
        pn = rng.choice([-1, 1], size=end - start)  # PN spreading code
        wm[start:end] = _WM_AMPLITUDE * pn * np.sin(2 * np.pi * carrier_freq * t[start:end] + phase)

    return wm


def embed_trial_watermark(audio: np.ndarray, sample_rate: int = 48000) -> np.ndarray:
    """
    Embed an audible trial watermark: a brief 1 kHz tone burst every 30 seconds.
    Used for free/trial tier exports.
    """
    result = audio.copy().astype(np.float64)
    interval_samples = sample_rate * 30
    tone_duration = int(sample_rate * 0.5)  # 500 ms tone
    tone_freq = 1000.0
    tone_amp = 0.15   # -16 dBFS — clearly audible

    t = np.arange(tone_duration) / sample_rate
    tone = tone_amp * np.sin(2 * np.pi * tone_freq * t)
    # Fade in/out
    fade = int(sample_rate * 0.02)
    ramp = np.linspace(0, 1, fade)
    tone[:fade] *= ramp
    tone[-fade:] *= ramp[::-1]

    for start in range(0, len(result) - tone_duration, interval_samples):
        if result.ndim == 1:
            result[start:start + tone_duration] += tone
        else:
            for ch in range(result.shape[1]):
                result[start:start + tone_duration, ch] += tone

    logger.info("trial_watermark_embedded: interval=30s tone=1kHz")
    return result.astype(audio.dtype)
