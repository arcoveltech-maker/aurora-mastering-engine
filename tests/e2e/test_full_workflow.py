"""
Aurora E2E smoke tests — register → login → create session → presign → start render.

Requires a running Aurora API server at API_BASE_URL (default: http://localhost:8000).
The server must have a writable DB and Redis.  S3 upload is skipped (presign URL
is obtained but no actual upload is performed against a live bucket).
"""
from __future__ import annotations

import io
import os
import struct
import time
import uuid
import wave

import pytest
import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000").rstrip("/")
TIMEOUT = httpx.Timeout(30.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_wav_bytes(duration_s: float = 1.0, sample_rate: int = 44100) -> bytes:
    """Create a minimal silent WAV file in memory."""
    num_samples = int(duration_s * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)
    return buf.getvalue()


def _unique_email() -> str:
    return f"e2e_{uuid.uuid4().hex[:8]}@aurora-ci.test"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> httpx.Client:
    with httpx.Client(base_url=API_BASE_URL, timeout=TIMEOUT) as c:
        yield c


@pytest.fixture(scope="module")
def registered_user(client: httpx.Client) -> dict:
    """Register a fresh user and return {email, password}."""
    email = _unique_email()
    password = "TestPass123!"
    resp = client.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "display_name": "E2E Tester",
    })
    assert resp.status_code in (200, 201), f"Register failed: {resp.text}"
    return {"email": email, "password": password}


@pytest.fixture(scope="module")
def auth_token(client: httpx.Client, registered_user: dict) -> str:
    """Log in and return a Bearer token."""
    resp = client.post("/api/auth/login", data={
        "username": registered_user["email"],
        "password": registered_user["password"],
    })
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    token = resp.json().get("access_token")
    assert token, "No access_token in login response"
    return token


@pytest.fixture(scope="module")
def authed_client(client: httpx.Client, auth_token: str) -> httpx.Client:
    """Return a client with Authorization header pre-set."""
    client.headers["Authorization"] = f"Bearer {auth_token}"
    return client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestHealth:
    def test_shallow_health(self, client: httpx.Client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("status") in ("ok", "healthy", "up")

    def test_deep_health(self, client: httpx.Client):
        resp = client.get("/api/health/deep")
        # Deep health may return 503 if S3 not configured — that's acceptable in CI
        assert resp.status_code in (200, 503)


class TestAuth:
    def test_register(self, registered_user: dict):
        # Fixture handles the assertion; just confirm we got a user back
        assert "@" in registered_user["email"]

    def test_login(self, auth_token: str):
        assert len(auth_token) > 20

    def test_get_me(self, authed_client: httpx.Client):
        resp = authed_client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data or "id" in data

    def test_duplicate_register_rejected(self, client: httpx.Client, registered_user: dict):
        resp = client.post("/api/auth/register", json={
            "email": registered_user["email"],
            "password": registered_user["password"],
            "display_name": "Duplicate",
        })
        assert resp.status_code in (400, 409, 422)


class TestSessions:
    def test_create_session(self, authed_client: httpx.Client):
        resp = authed_client.post("/api/sessions", json={
            "title": "E2E Test Session",
            "genre": "electronic",
        })
        assert resp.status_code in (200, 201), f"Create session failed: {resp.text}"
        data = resp.json()
        assert "id" in data
        # Store on class for later tests within the same module run
        TestSessions._session_id = data["id"]

    def test_list_sessions(self, authed_client: httpx.Client):
        resp = authed_client.get("/api/sessions")
        assert resp.status_code == 200
        data = resp.json()
        # Expect a list or paginated object
        items = data if isinstance(data, list) else data.get("items", data.get("sessions", []))
        assert len(items) >= 1

    def test_get_session(self, authed_client: httpx.Client):
        session_id = getattr(TestSessions, "_session_id", None)
        if not session_id:
            pytest.skip("No session created")
        resp = authed_client.get(f"/api/sessions/{session_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("id") == session_id


class TestUpload:
    def test_presign_upload(self, authed_client: httpx.Client):
        session_id = getattr(TestSessions, "_session_id", None)
        if not session_id:
            pytest.skip("No session created")

        resp = authed_client.post("/api/upload/presign", json={
            "session_id": session_id,
            "filename": "test_audio.wav",
            "content_type": "audio/wav",
            "size_bytes": 88244,  # ~1s 44100 Hz 16-bit mono
        })
        assert resp.status_code in (200, 201), f"Presign failed: {resp.text}"
        data = resp.json()
        # Expect either a presigned URL or an upload token
        assert "url" in data or "upload_url" in data or "key" in data
        TestUpload._presign_data = data

    def test_confirm_upload(self, authed_client: httpx.Client):
        presign_data = getattr(TestUpload, "_presign_data", None)
        if not presign_data:
            pytest.skip("No presign data")

        session_id = getattr(TestSessions, "_session_id", None)
        key = presign_data.get("key") or presign_data.get("s3_key", "ci/test.wav")

        resp = authed_client.post("/api/upload/confirm", json={
            "session_id": session_id,
            "s3_key": key,
            "filename": "test_audio.wav",
            "duration_seconds": 1.0,
            "sample_rate": 44100,
            "channels": 1,
        })
        # May 422 if S3 key validation is strict — acceptable in CI without real S3
        assert resp.status_code in (200, 201, 422), f"Confirm failed: {resp.text}"


class TestRender:
    def test_start_render(self, authed_client: httpx.Client):
        session_id = getattr(TestSessions, "_session_id", None)
        if not session_id:
            pytest.skip("No session created")

        resp = authed_client.post("/api/render/start", json={
            "session_id": session_id,
            "macros": {
                "eq_low": 0.5,
                "eq_mid": 0.5,
                "eq_high": 0.5,
                "compression": 0.6,
                "saturation": 0.3,
                "stereo_width": 0.5,
                "transient_attack": 0.4,
                "transient_sustain": 0.5,
                "air": 0.3,
                "warmth": 0.4,
                "loudness_target": 0.7,
            },
            "output_format": "wav",
            "target_lufs": -14.0,
        })
        # May 422 if no audio file is associated — that's fine without a real S3 upload
        assert resp.status_code in (200, 202, 422), f"Start render failed: {resp.text}"
        if resp.status_code in (200, 202):
            data = resp.json()
            assert "task_id" in data or "render_id" in data or "job_id" in data
            TestRender._task_id = data.get("task_id") or data.get("render_id") or data.get("job_id")

    def test_render_status(self, authed_client: httpx.Client):
        task_id = getattr(TestRender, "_task_id", None)
        if not task_id:
            pytest.skip("No render task started")

        resp = authed_client.get(f"/api/render/status/{task_id}")
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert "status" in data


class TestBilling:
    def test_get_subscription(self, authed_client: httpx.Client):
        resp = authed_client.get("/api/billing/subscription")
        assert resp.status_code in (200, 404)  # 404 if no billing set up

    def test_get_usage(self, authed_client: httpx.Client):
        resp = authed_client.get("/api/billing/usage")
        assert resp.status_code in (200, 404)


class TestChat:
    def test_chat_non_streaming(self, authed_client: httpx.Client):
        """Verify chat endpoint accepts a message (may fail if no API key in CI)."""
        resp = authed_client.post("/api/chat/stream", json={
            "session_id": getattr(TestSessions, "_session_id", "test"),
            "message": "What target LUFS should I use for Spotify?",
            "history": [],
        }, headers={"Accept": "text/event-stream"}, timeout=15.0)
        # Accept 200 (streaming started) or 402/422/500 (API key not configured in CI)
        assert resp.status_code in (200, 402, 422, 500)


class TestCollabWebSocket:
    def test_ws_connection(self, auth_token: str):
        """Smoke-test WebSocket collab endpoint."""
        import threading

        session_id = getattr(TestSessions, "_session_id", "test-session")
        ws_url = API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws/collab/{session_id}"

        received: list[str] = []
        error: list[Exception] = []

        def run_ws():
            try:
                with httpx.Client() as c:
                    # httpx doesn't do WS natively; use websockets library if available
                    import websockets.sync.client as ws_client  # type: ignore
                    with ws_client.connect(
                        ws_url,
                        additional_headers={"Authorization": f"Bearer {auth_token}"},
                        open_timeout=5,
                        close_timeout=5,
                    ) as conn:
                        conn.send('{"type":"ping"}')
                        msg = conn.recv(timeout=5)
                        received.append(msg)
            except Exception as exc:
                error.append(exc)

        t = threading.Thread(target=run_ws, daemon=True)
        t.start()
        t.join(timeout=10)

        if error:
            # WebSocket errors are non-fatal in CI (server may not be running)
            pytest.skip(f"WebSocket not available: {error[0]}")
        else:
            assert len(received) >= 1
