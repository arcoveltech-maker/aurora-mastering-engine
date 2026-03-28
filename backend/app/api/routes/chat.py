"""AI chat streaming endpoint."""
from __future__ import annotations

import json
import logging
from typing import List

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.models.user import User

router = APIRouter(prefix="/chat", tags=["chat"])
logger = logging.getLogger("aurora.chat")


class ChatMessage(BaseModel):
    role: str    # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    session_id: str | None = None
    audio_features: dict | None = None
    current_macros: dict | None = None


@router.post("/stream")
async def stream_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Stream Claude AI responses as SSE."""
    from app.services.claude_service import stream_chat as _stream

    msgs = [{"role": m.role, "content": m.content} for m in body.messages]

    async def event_generator():
        try:
            async for chunk in _stream(
                messages=msgs,
                audio_features=body.audio_features,
                current_macros=body.current_macros,
            ):
                yield f"data: {json.dumps(chunk)}\n\n"
        except Exception as e:
            logger.error("chat_stream_error: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'delta': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
