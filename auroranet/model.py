"""AuroraNet v2 — input 43 audio features + 8-dim genre embedding → 12 macros.

NOTE: NORMALIZATION_VALIDATED=False — model weights are stubs.
Do not use for inference until dataset normalisation is validated and model is trained.
"""
from __future__ import annotations

import torch
import torch.nn as nn

FEATURE_DIM = 43
GENRE_EMBED_DIM = 8
MACRO_NAMES = [
    "eq_low", "eq_mid", "eq_high", "eq_presence",
    "compression", "saturation", "stereo_width",
    "transient_attack", "transient_sustain",
    "air", "warmth", "loudness_target",
]
NUM_MACROS = len(MACRO_NAMES)

GENRE_LIST = [
    "pop", "rock", "hip-hop", "r&b", "edm", "house", "techno",
    "jazz", "acoustic", "classical", "orchestral", "metal",
    "lo-fi", "ambient", "afrobeat", "latin",
]
NUM_GENRES = len(GENRE_LIST)
GENRE_INDEX = {g: i for i, g in enumerate(GENRE_LIST)}


class AuroraNet(nn.Module):
    """
    Predicts 12 mastering macro parameters from 43 audio features + genre context.

    Architecture:
      - Genre embedding (NUM_GENRES → 8 dims)
      - Feature encoder: 51 → 128 → 256 → 128 with LayerNorm + GELU + Dropout
      - Per-macro output heads with sigmoid activation (output in [0, 1])
    """

    def __init__(self) -> None:
        super().__init__()

        self.genre_embed = nn.Embedding(NUM_GENRES, GENRE_EMBED_DIM, padding_idx=None)

        self.encoder = nn.Sequential(
            nn.Linear(FEATURE_DIM + GENRE_EMBED_DIM, 128),
            nn.LayerNorm(128),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(128, 256),
            nn.LayerNorm(256),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.LayerNorm(128),
            nn.GELU(),
        )

        self.heads = nn.ModuleDict({
            name: nn.Linear(128, 1) for name in MACRO_NAMES
        })

    def forward(
        self,
        features: torch.Tensor,      # (B, 43)
        genre_ids: torch.Tensor,     # (B,) — integer genre indices
    ) -> dict[str, torch.Tensor]:
        """Returns dict of macro_name → (B, 1) tensor in [0, 1]."""
        genre_emb = self.genre_embed(genre_ids)          # (B, 8)
        x = torch.cat([features, genre_emb], dim=-1)     # (B, 51)
        h = self.encoder(x)                              # (B, 128)
        return {name: torch.sigmoid(head(h)) for name, head in self.heads.items()}


def get_genre_id(genre: str | None) -> int:
    """Return genre index (0-based); defaults to 'pop' for unknown genres."""
    if genre is None:
        return GENRE_INDEX.get("pop", 0)
    return GENRE_INDEX.get(genre.lower(), GENRE_INDEX.get("pop", 0))
