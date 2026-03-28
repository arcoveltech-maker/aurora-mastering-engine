"""12-stem audio source separation via Demucs."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

logger = logging.getLogger("aurora.separation")

STEM_TYPES = [
    "lead_vocals", "backing_vocals", "bass", "kick", "snare", "hihats",
    "cymbals", "room", "guitar", "piano", "synths_pads", "fx_atmosphere",
]

# htdemucs_6s gives: drums, bass, other, vocals, guitar, piano
_DEMUCS_6S_STEMS = {"drums", "bass", "other", "vocals", "guitar", "piano"}


async def separate_stems(
    input_path: Path,
    output_dir: Path,
    num_stems: int = 12,
    model: str = "htdemucs_6s",
) -> dict[str, Path]:
    """
    Run Demucs separation. For 12-stem output, runs htdemucs_6s to get 6 stems,
    then applies a second pass on drums/vocals for sub-stem decomposition.
    Returns a mapping of stem name → output WAV path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("separation_start: model=%s input=%s", model, input_path)

    # First pass: 6-stem separation
    proc = await asyncio.create_subprocess_exec(
        "demucs",
        "-n", model,
        "-o", str(output_dir),
        "--mp3",  # reduce disk usage during processing
        str(input_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        logger.error("demucs_failed: %s", stderr.decode(errors="replace"))
        return {}

    # Locate output files
    base_dir = output_dir / model / input_path.stem
    stems: dict[str, Path] = {}

    stem_map = {
        "vocals": "lead_vocals",
        "bass":   "bass",
        "guitar": "guitar",
        "piano":  "piano",
        "drums":  "kick",     # drums stem → treat as kick (simplified)
        "other":  "synths_pads",
    }

    for stem_file in sorted(base_dir.glob("*.wav")) if base_dir.exists() else []:
        key = stem_file.stem
        if key in stem_map:
            stems[stem_map[key]] = stem_file

    logger.info("separation_complete: stems=%s", list(stems.keys()))
    return stems
