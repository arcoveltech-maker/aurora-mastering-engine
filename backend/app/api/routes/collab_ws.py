"""WebSocket collaboration hub — real-time multi-user mastering sessions."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger("aurora.collab")

# Max collaborators per tier
TIER_MAX_USERS = {"trial": 1, "artist": 1, "pro": 3, "enterprise": 8}
# Parameter lock expiry (seconds)
LOCK_TTL = 300  # 5 minutes


class CollaborationManager:
    def __init__(self) -> None:
        # session_id → {user_id → websocket}
        self._rooms: dict[str, dict[str, WebSocket]] = {}
        # session_id → {param_name → {user_id, expires_at}}
        self._locks: dict[str, dict[str, dict[str, Any]]] = {}

    # ── Connection management ─────────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        session_id: str,
        user_id: str,
        tier: str = "pro",
    ) -> bool:
        """Accept connection. Returns False if room is full."""
        await websocket.accept()
        room = self._rooms.setdefault(session_id, {})
        max_users = TIER_MAX_USERS.get(tier, 3)
        if len(room) >= max_users and user_id not in room:
            await websocket.send_json(
                {"type": "error", "code": "AURORA-B005", "message": f"Room full ({max_users} max for {tier})"}
            )
            await websocket.close(code=4003)
            return False

        room[user_id] = websocket
        logger.info("collab_connect: session=%s user=%s peers=%d", session_id, user_id, len(room))
        await self.broadcast(session_id, {"type": "user_joined", "user_id": user_id, "peer_count": len(room)}, exclude=user_id)
        return True

    async def disconnect(self, session_id: str, user_id: str) -> None:
        room = self._rooms.get(session_id, {})
        room.pop(user_id, None)
        # Release any locks held by this user
        locks = self._locks.get(session_id, {})
        released = [p for p, l in locks.items() if l.get("user_id") == user_id]
        for p in released:
            del locks[p]
        if room:
            await self.broadcast(session_id, {"type": "user_left", "user_id": user_id, "released_locks": released})
        else:
            self._rooms.pop(session_id, None)
            self._locks.pop(session_id, None)

    # ── Broadcast ─────────────────────────────────────────────────────────────

    async def broadcast(
        self,
        session_id: str,
        message: dict,
        exclude: str | None = None,
    ) -> None:
        room = self._rooms.get(session_id, {})
        dead: list[str] = []
        for uid, ws in room.items():
            if uid == exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(uid)
        for uid in dead:
            room.pop(uid, None)

    # ── Parameter locking (LWW with 5-minute expiry) ──────────────────────────

    def acquire_lock(self, session_id: str, param: str, user_id: str) -> bool:
        locks = self._locks.setdefault(session_id, {})
        existing = locks.get(param)
        now = time.time()
        if existing and existing["user_id"] != user_id and existing["expires_at"] > now:
            return False
        locks[param] = {"user_id": user_id, "expires_at": now + LOCK_TTL}
        return True

    def release_lock(self, session_id: str, param: str, user_id: str) -> bool:
        locks = self._locks.get(session_id, {})
        existing = locks.get(param)
        if existing and existing["user_id"] == user_id:
            del locks[param]
            return True
        return False

    def get_locks(self, session_id: str) -> dict:
        locks = self._locks.get(session_id, {})
        now = time.time()
        return {p: l for p, l in locks.items() if l["expires_at"] > now}


manager = CollaborationManager()


@router.websocket("/ws/collab/{session_id}")
async def collab_websocket(websocket: WebSocket, session_id: str) -> None:
    """
    Real-time collaboration WebSocket endpoint.

    Expected message types (JSON):
        {type: "auth",         token: str}
        {type: "param_update", param: str, value: any, ts: number}
        {type: "lock_acquire", param: str}
        {type: "lock_release", param: str}
        {type: "chat",         message: str}
        {type: "ping"}
    """
    user_id: str | None = None
    tier = "pro"

    try:
        # First message must be auth
        raw = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        data = json.loads(raw)
        if data.get("type") != "auth":
            await websocket.close(code=4001)
            return

        token = data.get("token", "")
        # Verify token
        try:
            from app.core.security import verify_access_token
            payload = verify_access_token(token)
            user_id = str(payload["sub"])
            tier = payload.get("tier", "pro")
        except Exception:
            await websocket.close(code=4001)
            return

        connected = await manager.connect(websocket, session_id, user_id, tier)
        if not connected:
            return

        # Send current lock state
        await websocket.send_json({"type": "state_sync", "locks": manager.get_locks(session_id)})

        # Message loop
        while True:
            try:
                raw = await websocket.receive_text()
                msg = json.loads(raw)
            except WebSocketDisconnect:
                break
            except Exception:
                continue

            mtype = msg.get("type", "")

            if mtype == "param_update":
                param = msg.get("param")
                value = msg.get("value")
                ts    = msg.get("ts", time.time())
                # LWW: broadcast to all peers
                await manager.broadcast(
                    session_id,
                    {"type": "param_update", "param": param, "value": value, "ts": ts, "from": user_id},
                    exclude=user_id,
                )

            elif mtype == "lock_acquire":
                param = msg.get("param")
                ok = manager.acquire_lock(session_id, param, user_id)
                await websocket.send_json({"type": "lock_result", "param": param, "success": ok})
                if ok:
                    await manager.broadcast(
                        session_id,
                        {"type": "lock_acquired", "param": param, "user_id": user_id},
                        exclude=user_id,
                    )

            elif mtype == "lock_release":
                param = msg.get("param")
                ok = manager.release_lock(session_id, param, user_id)
                if ok:
                    await manager.broadcast(
                        session_id,
                        {"type": "lock_released", "param": param, "user_id": user_id},
                    )

            elif mtype == "chat":
                # Append-only chat — broadcast to all including sender
                content = str(msg.get("message", ""))[:2000]
                await manager.broadcast(
                    session_id,
                    {"type": "chat", "from": user_id, "message": content, "ts": time.time()},
                )

            elif mtype == "ping":
                await websocket.send_json({"type": "pong", "ts": time.time()})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("collab_ws_error: session=%s user=%s error=%s", session_id, user_id, e)
    finally:
        if user_id:
            await manager.disconnect(session_id, user_id)
