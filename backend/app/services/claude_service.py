"""Claude AI assistant service for Aurora mastering guidance."""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator

logger = logging.getLogger("aurora.claude")

SYSTEM_PROMPT = """You are Aurora AI, an expert audio mastering assistant embedded in the Aurora AI Mastering Engine v5.0.

You help users:
1. Understand their audio's characteristics and how to improve them
2. Recommend macro settings (brighten, glue, width, punch, warmth, loudness) with specific numeric values
3. Explain audio engineering concepts in plain language
4. Troubleshoot mastering issues (phase, dynamic range, spectral balance)
5. Suggest platform-specific loudness targets

Technical context:
- Macros are 0–100 scale (50 = neutral)
- Integrated LUFS targets: Spotify -14, Apple Music -16, YouTube -14, Club -8
- True Peak ceiling: -1 dBTP for streaming, -0.3 dBTP for lossless
- LRA: 6–12 LU typical for pop/rock, 14–20 LU for classical

When suggesting macro changes, always output a JSON block like:
```json
{"macros": {"brighten": 65, "warmth": 55}}
```

Be concise and technically precise. Reference specific frequency ranges, dB values, and time constants when relevant."""


async def chat(
    messages: list[dict],
    audio_features: dict | None = None,
    current_macros: dict | None = None,
    stream: bool = False,
) -> str:
    """Non-streaming chat completion."""
    from app.core.config import settings
    import anthropic

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    context = _build_context(audio_features, current_macros)
    system = SYSTEM_PROMPT + context

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system,
        messages=messages,
    )
    return response.content[0].text


async def stream_chat(
    messages: list[dict],
    audio_features: dict | None = None,
    current_macros: dict | None = None,
) -> AsyncIterator[dict]:
    """
    Streaming chat. Yields SSE-compatible dicts:
        {type: "thinking", delta: str}   — extended thinking
        {type: "text", delta: str}       — response text
        {type: "done", params: dict|null} — finished, extracted macro params
    """
    from app.core.config import settings
    import anthropic
    import re

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    context = _build_context(audio_features, current_macros)
    system = SYSTEM_PROMPT + context

    full_text = ""

    try:
        with client.messages.stream(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream_obj:
            for text_delta in stream_obj.text_stream:
                full_text += text_delta
                yield {"type": "text", "delta": text_delta}
    except Exception as e:
        logger.error("claude_stream_error: %s", e)
        yield {"type": "error", "delta": str(e)}
        return

    # Extract macro params from response
    params = _extract_macros(full_text)
    yield {"type": "done", "params": params}


def _build_context(
    audio_features: dict | None,
    current_macros: dict | None,
) -> str:
    parts = []
    if audio_features:
        parts.append(f"\n\nCurrent audio analysis:\n{json.dumps(audio_features, indent=2)}")
    if current_macros:
        parts.append(f"\n\nCurrent macro settings:\n{json.dumps(current_macros, indent=2)}")
    return "".join(parts)


def _extract_macros(text: str) -> dict | None:
    """Extract JSON macro suggestion block from response text."""
    import re
    pattern = r'```json\s*(\{[^`]+\})\s*```'
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(1))
        return data.get("macros")
    except Exception:
        return None
