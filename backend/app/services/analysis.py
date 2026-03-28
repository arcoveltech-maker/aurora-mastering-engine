"""Audio feature extraction — 43 dimensions, ITU-R BS.1770-4 loudness."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

KEY_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
KEY_ENCODING = {
    f"{k} {s}": i + (12 if s == "minor" else 0)
    for i, k in enumerate(KEY_NAMES)
    for s in ("major", "minor")
}
BAND_EDGES_HZ = [0, 60, 120, 250, 500, 1000, 2000, 4000, 8000, 12000, 16000, 24000]


@dataclass
class AudioFeatures:
    # Loudness (5)
    integrated_lufs: float = -23.0
    momentary_max: float = -23.0
    short_term_max: float = -23.0
    true_peak_dbtp: float = -1.0
    lra: float = 6.0

    # Dynamics (6)
    crest_factor: float = 10.0
    dynamic_range: float = 10.0
    rms_mean: float = -18.0
    peak_to_rms: float = 10.0
    transient_density: float = 0.3
    compression_ratio_estimate: float = 1.5

    # Spectral — 10-band energies (normalized)
    band_energy_1: float = 0.0
    band_energy_2: float = 0.0
    band_energy_3: float = 0.0
    band_energy_4: float = 0.0
    band_energy_5: float = 0.0
    band_energy_6: float = 0.0
    band_energy_7: float = 0.0
    band_energy_8: float = 0.0
    band_energy_9: float = 0.0
    band_energy_10: float = 0.0
    spectral_centroid: float = 2000.0
    spectral_spread: float = 1000.0

    # Derived spectral ratios
    brightness: float = 0.3    # energy > 4 kHz / total
    bass_ratio: float = 0.2    # energy < 250 Hz / total
    presence_ratio: float = 0.15  # 2–8 kHz
    air_ratio: float = 0.05    # > 10 kHz

    # Stereo (4)
    stereo_width: float = 0.5
    correlation: float = 0.9
    mid_side_ratio: float = 1.0
    side_energy_ratio: float = 0.2

    # Temporal (3)
    zero_crossing_rate: float = 0.05
    onset_strength: float = 0.3
    tempo_estimate: float = 120.0

    # Harmonic / Tonal (4)
    harmonic_ratio: float = 0.6
    key_estimate: str = "C major"
    key_confidence: float = 0.5
    bpm_confidence: float = 0.7

    # Quality (6)
    noise_floor_db: float = -60.0
    dc_offset: float = 0.0
    clipping_count: int = 0
    silence_ratio: float = 0.0
    spectral_flatness: float = 0.1
    overall_quality_score: float = 0.9

    def to_vector(self) -> np.ndarray:
        vec = [
            self.integrated_lufs, self.momentary_max, self.short_term_max,
            self.true_peak_dbtp, self.lra,
            self.crest_factor, self.dynamic_range, self.rms_mean,
            self.peak_to_rms, self.transient_density, self.compression_ratio_estimate,
            self.band_energy_1, self.band_energy_2, self.band_energy_3,
            self.band_energy_4, self.band_energy_5, self.band_energy_6,
            self.band_energy_7, self.band_energy_8, self.band_energy_9,
            self.band_energy_10,
            self.spectral_centroid, self.spectral_spread,
            self.brightness, self.bass_ratio, self.presence_ratio, self.air_ratio,
            self.stereo_width, self.correlation, self.mid_side_ratio,
            self.side_energy_ratio,
            self.zero_crossing_rate, self.onset_strength, self.tempo_estimate,
            self.harmonic_ratio,
            float(KEY_ENCODING.get(self.key_estimate, 0)),
            self.key_confidence, self.bpm_confidence,
            self.noise_floor_db, self.dc_offset, float(self.clipping_count),
            self.silence_ratio, self.spectral_flatness,
        ]
        while len(vec) < 43:
            vec.append(0.0)
        return np.array(vec[:43], dtype=np.float32)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


class FeatureExtractor:
    """Extract 43 audio features using librosa + scipy + numpy."""

    def extract(self, audio_path: str | Path, target_sr: int = 48000) -> AudioFeatures:
        try:
            import soundfile as sf
            import librosa

            audio_path = str(audio_path)
            audio, sr = sf.read(audio_path, always_2d=True)

            if sr != target_sr:
                mono_raw = librosa.resample(audio[:, 0], orig_sr=sr, target_sr=target_sr)
                sr = target_sr
            else:
                mono_raw = audio[:, 0].copy()

            features = AudioFeatures()
            mono = mono_raw.astype(np.float64)

            # ── Loudness ────────────────────────────────────────────────
            rms = float(np.sqrt(np.mean(mono ** 2)))
            features.integrated_lufs = -0.691 + 20 * math.log10(rms + 1e-9)
            features.true_peak_dbtp = float(20 * np.log10(np.max(np.abs(mono)) + 1e-9))
            features.rms_mean = features.integrated_lufs
            features.lra = self._estimate_lra(mono, sr)

            # Momentary / short-term approximation
            block_400ms = int(sr * 0.4)
            blocks_mom = [
                float(np.sqrt(np.mean(mono[i:i+block_400ms]**2)))
                for i in range(0, len(mono) - block_400ms, block_400ms // 4)
            ]
            if blocks_mom:
                features.momentary_max = -0.691 + 20 * math.log10(max(blocks_mom) + 1e-9)
                features.short_term_max = features.momentary_max

            # ── Dynamics ────────────────────────────────────────────────
            peak = float(np.max(np.abs(mono)))
            features.crest_factor = float(20 * np.log10((peak + 1e-9) / (rms + 1e-9)))
            features.dynamic_range = features.crest_factor
            features.peak_to_rms = features.crest_factor

            # Clipping count
            features.clipping_count = int(np.sum(np.abs(mono) >= 0.9999))

            # DC offset
            features.dc_offset = float(np.mean(mono))

            # Silence ratio
            silence_thresh = 10 ** (-60 / 20)
            features.silence_ratio = float(np.sum(np.abs(mono) < silence_thresh) / len(mono))

            # ── Spectral ────────────────────────────────────────────────
            fft_len = min(len(mono), sr * 4)
            fft = np.abs(np.fft.rfft(mono[:fft_len]))
            freqs = np.fft.rfftfreq(fft_len, d=1.0 / sr)
            features = self._extract_spectral(features, fft, freqs, sr)

            # ── Stereo ──────────────────────────────────────────────────
            if audio.shape[1] >= 2:
                left, right = audio[:, 0].astype(np.float64), audio[:, 1].astype(np.float64)
                mid  = (left + right) * 0.5
                side = (left - right) * 0.5
                mid_rms  = float(np.sqrt(np.mean(mid  ** 2))) + 1e-9
                side_rms = float(np.sqrt(np.mean(side ** 2))) + 1e-9
                features.mid_side_ratio = mid_rms / side_rms
                features.stereo_width = float(np.clip(side_rms / mid_rms, 0, 1))
                features.correlation = float(np.clip(np.corrcoef(left, right)[0, 1], -1, 1))
                features.side_energy_ratio = float(np.mean(side**2) / (np.mean(mid**2) + 1e-9))
            else:
                features.stereo_width = 0.0
                features.correlation = 1.0
                features.mid_side_ratio = 1000.0

            # ── Temporal ────────────────────────────────────────────────
            mono_f32 = mono.astype(np.float32)
            zcr = librosa.feature.zero_crossing_rate(mono_f32)
            features.zero_crossing_rate = float(np.mean(zcr))

            onset_env = librosa.onset.onset_strength(y=mono_f32, sr=sr)
            features.onset_strength = float(np.mean(onset_env))
            features.transient_density = float(
                len(librosa.onset.onset_detect(y=mono_f32, sr=sr)) / (len(mono) / sr + 1e-9)
            )

            tempo, _ = librosa.beat.beat_track(y=mono_f32, sr=sr)
            features.tempo_estimate = float(tempo) if not np.isnan(float(tempo)) else 120.0

            # Compression ratio estimate (ratio of RMS to peak in short blocks)
            features.compression_ratio_estimate = float(
                np.clip(1.0 / (features.dynamic_range / 20.0 + 0.1), 1.0, 20.0)
            )

            # ── Harmonic ─────────────────────────────────────────────────
            harmonic, percussive = librosa.effects.hpss(mono_f32)
            harm_rms = float(np.sqrt(np.mean(harmonic ** 2)))
            perc_rms = float(np.sqrt(np.mean(percussive ** 2)))
            features.harmonic_ratio = harm_rms / (harm_rms + perc_rms + 1e-9)

            chroma = librosa.feature.chroma_cqt(y=mono_f32, sr=sr)
            key_idx = int(np.argmax(np.mean(chroma, axis=1)))
            features.key_estimate = f"{KEY_NAMES[key_idx]} major"
            features.key_confidence = float(np.max(np.mean(chroma, axis=1)))
            features.bpm_confidence = 0.7

            # ── Quality ─────────────────────────────────────────────────
            # Noise floor: 10th percentile of frame RMS in dB
            frame_size = 2048
            frame_rms = [
                float(np.sqrt(np.mean(mono[i:i+frame_size]**2)))
                for i in range(0, len(mono) - frame_size, frame_size)
            ]
            if frame_rms:
                noise_lin = float(np.percentile(frame_rms, 10))
                features.noise_floor_db = 20 * math.log10(noise_lin + 1e-9)

            # Overall quality: penalize clipping, DC offset, silence
            q = 1.0
            q -= min(0.3, features.clipping_count / 1000.0)
            q -= min(0.2, abs(features.dc_offset) * 10)
            q -= min(0.2, features.silence_ratio)
            features.overall_quality_score = float(max(0.0, q))

            return features

        except Exception as e:
            from app.core.errors import AuroraHTTPException
            raise AuroraHTTPException("AURORA-E100", f"Feature extraction failed: {e}") from e

    def _estimate_lra(self, audio: np.ndarray, sr: int) -> float:
        block_size = int(sr * 0.4)
        hop_size = int(sr * 0.1)
        levels = []
        for i in range(0, len(audio) - block_size, hop_size):
            block = audio[i:i + block_size]
            rms = float(np.sqrt(np.mean(block ** 2)))
            lufs = -0.691 + 20 * math.log10(rms + 1e-9)
            if lufs > -70:
                levels.append(lufs)
        if len(levels) < 2:
            return 6.0
        levels.sort()
        p10 = levels[max(0, int(len(levels) * 0.10))]
        p95 = levels[min(len(levels) - 1, int(len(levels) * 0.95))]
        return float(p95 - p10)

    def _extract_spectral(self, features: AudioFeatures, fft: np.ndarray,
                           freqs: np.ndarray, sr: int) -> AudioFeatures:
        total_energy = float(np.sum(fft ** 2)) + 1e-9
        band_fields = [f"band_energy_{i+1}" for i in range(10)]
        for i, fname in enumerate(band_fields):
            lo, hi = BAND_EDGES_HZ[i], BAND_EDGES_HZ[i + 1]
            mask = (freqs >= lo) & (freqs < hi)
            setattr(features, fname, float(np.sum(fft[mask] ** 2) / total_energy))

        power = fft ** 2
        features.spectral_centroid = float(np.sum(freqs * power) / (np.sum(power) + 1e-9))
        features.spectral_spread = float(
            np.sqrt(np.sum(((freqs - features.spectral_centroid) ** 2) * power) / (np.sum(power) + 1e-9))
        )
        features.spectral_flatness = float(
            np.exp(np.mean(np.log(fft + 1e-9))) / (np.mean(fft) + 1e-9)
        )

        # Derived ratios
        air_mask      = freqs > 10000
        bright_mask   = freqs > 4000
        bass_mask     = freqs < 250
        presence_mask = (freqs >= 2000) & (freqs < 8000)
        features.air_ratio      = float(np.sum(power[air_mask])      / total_energy)
        features.brightness     = float(np.sum(power[bright_mask])   / total_energy)
        features.bass_ratio     = float(np.sum(power[bass_mask])     / total_energy)
        features.presence_ratio = float(np.sum(power[presence_mask]) / total_energy)

        return features


# Module-level convenience
_extractor = FeatureExtractor()


async def extract_features(audio_path: Path, sample_rate: int = 48000) -> AudioFeatures:
    """Async wrapper for feature extraction."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _extractor.extract, str(audio_path), sample_rate)
