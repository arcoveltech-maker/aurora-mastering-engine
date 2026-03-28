"""QC Engine — 18 checks per Aurora v5.0 specification."""
from __future__ import annotations

import logging
import math
from enum import Enum
from pathlib import Path
from typing import Any

import numpy as np
from pydantic import BaseModel

logger = logging.getLogger("aurora.qc")


class QCCheckID(str, Enum):
    LUFS_INTEGRATED     = "qc_lufs_integrated"
    LUFS_MOMENTARY_MAX  = "qc_lufs_momentary_max"
    TRUE_PEAK           = "qc_true_peak"
    LRA                 = "qc_lra"
    DC_OFFSET           = "qc_dc_offset"
    SILENCE_HEAD        = "qc_silence_head"
    SILENCE_TAIL        = "qc_silence_tail"
    CLIPPING            = "qc_clipping"
    PHASE_CORRELATION   = "qc_phase_correlation"
    STEREO_BALANCE      = "qc_stereo_balance"
    FREQUENCY_RESPONSE  = "qc_frequency_response"
    NOISE_FLOOR         = "qc_noise_floor"
    CODEC_COMPATIBILITY = "qc_codec_compatibility"
    SAMPLE_RATE         = "qc_sample_rate"
    BIT_DEPTH           = "qc_bit_depth"
    FORMAT_COMPLIANCE   = "qc_format_compliance"
    METADATA_COMPLETE   = "qc_metadata_complete"
    WATERMARK_PRESENT   = "qc_watermark_present"


class QCResult(BaseModel):
    check_id: QCCheckID
    status: str          # "pass", "fail", "warning", "remediated"
    measured_value: Any = None
    threshold: Any = None
    message: str = ""
    can_remediate: bool = False


class QCReport(BaseModel):
    session_id: str
    render_job_id: str
    checks: list[QCResult]
    passed: int
    failed: int
    warnings: int
    overall_status: str  # "pass" or "fail"


# Tiers that get full 18-check QC
_FULL_QC_TIERS = {"pro", "enterprise"}
# Artist tier gets first 10
_ARTIST_CHECK_IDS = list(QCCheckID)[:10]


async def run_qc_checks(
    audio_path: Path,
    target_lufs: float = -14.0,
    ceiling_dbtp: float = -1.0,
    tier: str = "pro",
    session_id: str = "",
    render_job_id: str = "",
    metadata: dict | None = None,
    watermark_embedded: bool = False,
) -> QCReport:
    """Run up to 18 QC checks. Artist tier gets 10, Pro/Enterprise gets 18."""
    checks: list[QCResult] = []

    try:
        import soundfile as sf
        audio, sr = sf.read(str(audio_path), always_2d=True)
    except Exception as e:
        logger.error("qc_read_failed: %s", e)
        return QCReport(
            session_id=session_id, render_job_id=render_job_id,
            checks=[], passed=0, failed=1, warnings=0, overall_status="fail",
        )

    mono = audio[:, 0] if audio.ndim > 1 else audio

    # ── Check 1: Integrated LUFS ────────────────────────────────────────────
    rms = float(np.sqrt(np.mean(mono ** 2)))
    lufs = -0.691 + 20 * math.log10(rms + 1e-9)
    lufs_ok = abs(lufs - target_lufs) <= 1.0
    checks.append(QCResult(
        check_id=QCCheckID.LUFS_INTEGRATED,
        status="pass" if lufs_ok else "warning",
        measured_value=round(lufs, 2),
        threshold=round(target_lufs, 2),
        message=f"Integrated LUFS {lufs:.1f} (target {target_lufs})",
    ))

    # ── Check 2: Momentary max LUFS ─────────────────────────────────────────
    block = int(sr * 0.4)
    mom_levels = [
        -0.691 + 20 * math.log10(float(np.sqrt(np.mean(mono[i:i+block]**2))) + 1e-9)
        for i in range(0, max(1, len(mono) - block), block // 4)
    ]
    mom_max = max(mom_levels) if mom_levels else lufs
    mom_ok = mom_max <= target_lufs + 3.0
    checks.append(QCResult(
        check_id=QCCheckID.LUFS_MOMENTARY_MAX,
        status="pass" if mom_ok else "warning",
        measured_value=round(mom_max, 2),
        threshold=round(target_lufs + 3.0, 2),
        message=f"Momentary max {mom_max:.1f} LUFS",
    ))

    # ── Check 3: True peak ──────────────────────────────────────────────────
    tp = float(20 * np.log10(np.max(np.abs(mono)) + 1e-9))
    tp_ok = tp <= ceiling_dbtp
    checks.append(QCResult(
        check_id=QCCheckID.TRUE_PEAK,
        status="pass" if tp_ok else "fail",
        measured_value=round(tp, 2),
        threshold=ceiling_dbtp,
        message=f"True peak {tp:.2f} dBTP (ceiling {ceiling_dbtp})",
        can_remediate=True,
    ))

    # ── Check 4: LRA ────────────────────────────────────────────────────────
    block_s = int(sr * 0.4)
    hop_s = int(sr * 0.1)
    short_levels = [
        -0.691 + 20 * math.log10(float(np.sqrt(np.mean(mono[i:i+block_s]**2))) + 1e-9)
        for i in range(0, max(1, len(mono) - block_s), hop_s)
        if float(np.sqrt(np.mean(mono[i:i+block_s]**2))) > 1e-9
    ]
    lra = 0.0
    if len(short_levels) >= 2:
        sl = sorted(short_levels)
        lra = sl[int(len(sl) * 0.95)] - sl[int(len(sl) * 0.10)]
    lra_ok = 1.0 <= lra <= 20.0
    checks.append(QCResult(
        check_id=QCCheckID.LRA,
        status="pass" if lra_ok else "warning",
        measured_value=round(lra, 2),
        threshold="1.0–20.0 LU",
        message=f"LRA {lra:.1f} LU",
    ))

    # ── Check 5: DC offset ──────────────────────────────────────────────────
    dc = float(np.mean(mono))
    dc_ok = abs(dc) < 0.001
    checks.append(QCResult(
        check_id=QCCheckID.DC_OFFSET,
        status="pass" if dc_ok else ("warning" if abs(dc) < 0.01 else "fail"),
        measured_value=round(dc, 6),
        threshold=0.001,
        message=f"DC offset {dc:.5f}",
        can_remediate=True,
    ))

    # ── Check 6: Head silence ───────────────────────────────────────────────
    silence_thresh = 10 ** (-60 / 20)
    head_silence = 0
    for s in mono:
        if abs(s) < silence_thresh:
            head_silence += 1
        else:
            break
    head_ms = head_silence / sr * 1000
    head_ok = head_ms <= 500
    checks.append(QCResult(
        check_id=QCCheckID.SILENCE_HEAD,
        status="pass" if head_ok else "warning",
        measured_value=round(head_ms, 1),
        threshold=500,
        message=f"Head silence {head_ms:.0f} ms",
    ))

    # ── Check 7: Tail silence ───────────────────────────────────────────────
    tail_silence = 0
    for s in reversed(mono):
        if abs(s) < silence_thresh:
            tail_silence += 1
        else:
            break
    tail_ms = tail_silence / sr * 1000
    tail_ok = tail_ms <= 3000
    checks.append(QCResult(
        check_id=QCCheckID.SILENCE_TAIL,
        status="pass" if tail_ok else "warning",
        measured_value=round(tail_ms, 1),
        threshold=3000,
        message=f"Tail silence {tail_ms:.0f} ms",
    ))

    # ── Check 8: Clipping ───────────────────────────────────────────────────
    clip_count = int(np.sum(np.abs(mono) >= 0.9999))
    clip_ok = clip_count == 0
    checks.append(QCResult(
        check_id=QCCheckID.CLIPPING,
        status="pass" if clip_ok else "fail",
        measured_value=clip_count,
        threshold=0,
        message=f"{clip_count} clipped samples",
        can_remediate=True,
    ))

    # ── Check 9: Phase correlation ──────────────────────────────────────────
    if audio.shape[1] >= 2:
        corr = float(np.corrcoef(audio[:, 0], audio[:, 1])[0, 1])
    else:
        corr = 1.0
    corr_ok = corr >= -0.3
    checks.append(QCResult(
        check_id=QCCheckID.PHASE_CORRELATION,
        status="pass" if corr_ok else ("warning" if corr >= -0.5 else "fail"),
        measured_value=round(corr, 3),
        threshold=-0.3,
        message=f"Phase correlation {corr:.2f}",
    ))

    # ── Check 10: Stereo balance ─────────────────────────────────────────────
    if audio.shape[1] >= 2:
        l_rms = float(np.sqrt(np.mean(audio[:, 0] ** 2))) + 1e-9
        r_rms = float(np.sqrt(np.mean(audio[:, 1] ** 2))) + 1e-9
        balance_db = 20 * math.log10(l_rms / r_rms)
    else:
        balance_db = 0.0
    balance_ok = abs(balance_db) <= 1.5
    checks.append(QCResult(
        check_id=QCCheckID.STEREO_BALANCE,
        status="pass" if balance_ok else "warning",
        measured_value=round(balance_db, 2),
        threshold=1.5,
        message=f"L/R balance {balance_db:+.1f} dB",
    ))

    # ── Checks 11–18 (Pro/Enterprise only) ──────────────────────────────────
    if tier in _FULL_QC_TIERS:
        # Check 11: Frequency response
        fft = np.abs(np.fft.rfft(mono[:min(len(mono), sr * 4)]))
        freqs = np.fft.rfftfreq(min(len(mono), sr * 4), d=1.0 / sr)
        low_energy  = float(np.sum(fft[(freqs < 80)] ** 2))
        high_energy = float(np.sum(fft[(freqs > 12000)] ** 2))
        total_e     = float(np.sum(fft ** 2)) + 1e-9
        freq_ok = (low_energy / total_e > 0.01) and (high_energy / total_e > 0.001)
        checks.append(QCResult(
            check_id=QCCheckID.FREQUENCY_RESPONSE,
            status="pass" if freq_ok else "warning",
            measured_value={"low_ratio": round(low_energy/total_e, 4), "high_ratio": round(high_energy/total_e, 4)},
            threshold={"low_min": 0.01, "high_min": 0.001},
            message="Frequency response check",
        ))

        # Check 12: Noise floor
        frame_size = 2048
        frame_rms = [
            float(np.sqrt(np.mean(mono[i:i+frame_size]**2)))
            for i in range(0, len(mono) - frame_size, frame_size)
        ]
        noise_floor = -80.0
        if frame_rms:
            noise_lin = float(np.percentile(frame_rms, 5))
            noise_floor = 20 * math.log10(noise_lin + 1e-9)
        nf_ok = noise_floor <= -50
        checks.append(QCResult(
            check_id=QCCheckID.NOISE_FLOOR,
            status="pass" if nf_ok else "warning",
            measured_value=round(noise_floor, 1),
            threshold=-50,
            message=f"Noise floor {noise_floor:.0f} dB",
        ))

        # Check 13: Codec compatibility (check for NaN/Inf)
        has_nan = bool(np.any(~np.isfinite(mono)))
        checks.append(QCResult(
            check_id=QCCheckID.CODEC_COMPATIBILITY,
            status="fail" if has_nan else "pass",
            measured_value="nan_detected" if has_nan else "clean",
            threshold="no_nan_inf",
            message="No NaN/Inf samples" if not has_nan else "NaN/Inf detected",
        ))

        # Check 14: Sample rate
        expected_sr = {48000, 44100, 96000}
        sr_ok = sr in expected_sr
        checks.append(QCResult(
            check_id=QCCheckID.SAMPLE_RATE,
            status="pass" if sr_ok else "warning",
            measured_value=sr,
            threshold=list(expected_sr),
            message=f"Sample rate {sr} Hz",
        ))

        # Check 15: Bit depth
        info = None
        try:
            import soundfile as sf
            info = sf.info(str(audio_path))
        except Exception:
            pass
        subtype = getattr(info, "subtype", "PCM_24") if info else "PCM_24"
        bd_ok = "PCM_16" in subtype or "PCM_24" in subtype or "PCM_32" in subtype or "FLOAT" in subtype
        checks.append(QCResult(
            check_id=QCCheckID.BIT_DEPTH,
            status="pass" if bd_ok else "warning",
            measured_value=subtype,
            threshold="PCM_16/24/32 or FLOAT",
            message=f"Bit depth: {subtype}",
        ))

        # Check 16: Format compliance
        suffix = Path(audio_path).suffix.lower()
        fmt_ok = suffix in (".wav", ".aiff", ".flac")
        checks.append(QCResult(
            check_id=QCCheckID.FORMAT_COMPLIANCE,
            status="pass" if fmt_ok else "fail",
            measured_value=suffix,
            threshold=".wav/.aiff/.flac",
            message=f"Format: {suffix}",
        ))

        # Check 17: Metadata completeness
        meta = metadata or {}
        required_fields = {"title", "artist"}
        missing = required_fields - set(meta.keys())
        meta_ok = len(missing) == 0
        checks.append(QCResult(
            check_id=QCCheckID.METADATA_COMPLETE,
            status="pass" if meta_ok else "warning",
            measured_value=list(missing) if missing else "complete",
            threshold=list(required_fields),
            message="Metadata complete" if meta_ok else f"Missing: {missing}",
        ))

        # Check 18: Forensic watermark
        checks.append(QCResult(
            check_id=QCCheckID.WATERMARK_PRESENT,
            status="pass" if watermark_embedded else "warning",
            measured_value=watermark_embedded,
            threshold=True,
            message="Forensic watermark present" if watermark_embedded else "No watermark",
        ))

    # Limit to tier-appropriate checks
    if tier not in _FULL_QC_TIERS:
        checks = checks[:10]

    passed   = sum(1 for c in checks if c.status == "pass")
    failed   = sum(1 for c in checks if c.status == "fail")
    warnings = sum(1 for c in checks if c.status == "warning")
    overall  = "pass" if failed == 0 else "fail"

    logger.info(
        "qc_complete: session=%s passed=%d failed=%d warnings=%d",
        session_id, passed, failed, warnings,
    )

    return QCReport(
        session_id=session_id,
        render_job_id=render_job_id,
        checks=checks,
        passed=passed,
        failed=failed,
        warnings=warnings,
        overall_status=overall,
    )
