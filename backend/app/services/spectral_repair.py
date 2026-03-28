"""Spectral hole detection and interpolation."""
from __future__ import annotations

import numpy as np
from scipy import signal


async def repair_spectral_holes(
    audio: np.ndarray,
    sample_rate: int,
    threshold_db: float = -60.0,
) -> np.ndarray:
    """
    Detect and interpolate spectral holes/dropouts using STFT analysis.
    A 'hole' is a time-frequency bin that is significantly below the threshold
    while its temporal neighbours are not.
    """
    n_fft = 2048
    hop = 512

    # Handle stereo by processing each channel independently
    if audio.ndim == 2:
        repaired_channels = [
            await repair_spectral_holes(audio[:, ch], sample_rate, threshold_db)
            for ch in range(audio.shape[1])
        ]
        return np.stack(repaired_channels, axis=1)

    _, _, Zxx = signal.stft(audio, sample_rate, nperseg=n_fft, noverlap=n_fft - hop)
    magnitude = np.abs(Zxx)
    phase = np.angle(Zxx)

    threshold_lin = 10.0 ** (threshold_db / 20.0)
    holes = magnitude < threshold_lin

    # Interpolate holes that have non-hole neighbours in time
    for t in range(1, magnitude.shape[1] - 1):
        for f in range(magnitude.shape[0]):
            if holes[f, t] and not holes[f, t - 1] and not holes[f, t + 1]:
                magnitude[f, t] = (magnitude[f, t - 1] + magnitude[f, t + 1]) * 0.5
                # Linear phase interpolation
                phase[f, t] = (phase[f, t - 1] + phase[f, t + 1]) * 0.5

    Zxx_repaired = magnitude * np.exp(1j * phase)
    _, repaired = signal.istft(Zxx_repaired, sample_rate, nperseg=n_fft, noverlap=n_fft - hop)
    return repaired[: len(audio)].astype(audio.dtype)
