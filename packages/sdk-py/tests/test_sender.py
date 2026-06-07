"""Tests for the Python headless SDK (PresenceSender + drive_adapter)."""

import asyncio
import json

import pytest

import presence_protocol as p
from agent_face_sdk import PresenceSender, drive_adapter


class FakeWS:
    """Captures send_text payloads (FastAPI-WebSocket-shaped)."""

    def __init__(self):
        self.sent = []

    async def send_text(self, text):
        self.sent.append(json.loads(text))


class FakeSocket:
    """Transport exposing plain `send` instead of `send_text`."""

    def __init__(self):
        self.sent = []

    async def send(self, text):
        self.sent.append(json.loads(text))


def test_typed_emitters_send_valid_events():
    async def run():
        ws = FakeWS()
        s = PresenceSender(ws)
        await s.speak_delta("hi")
        await s.action("Read", detail="auth.py", status="start", id="t1")
        await s.ask("a1", "Run tests?", kind="approve", options=["Yes", "No"])
        await s.status("working", 0.5)
        await s.done(full_text="ok", turns=2)
        return ws.sent

    sent = asyncio.run(run())
    assert all(p.is_valid_presence_event(e) for e in sent)
    assert [e["type"] for e in sent] == ["speak_delta", "action", "ask", "status", "done"]
    assert sent[1] == {"type": "action", "id": "t1", "name": "Read", "detail": "auth.py", "status": "start"}


def test_supports_plain_send_transport():
    async def run():
        sock = FakeSocket()
        await PresenceSender(sock).speak_delta("yo")
        return sock.sent

    sent = asyncio.run(run())
    assert sent == [{"type": "speak_delta", "text": "yo"}]


def test_emit_rejects_invalid_event():
    async def run():
        s = PresenceSender(FakeWS())
        with pytest.raises(ValueError):
            await s.emit({"type": "bogus"})

    asyncio.run(run())


def test_emit_accepts_wire_dict_from_adapter():
    async def run():
        ws = FakeWS()
        await PresenceSender(ws).emit({"type": "action", "name": "Bash", "status": "success"})
        return ws.sent

    sent = asyncio.run(run())
    assert sent[0]["name"] == "Bash" and sent[0]["status"] == "success"


class FakeAdapter:
    """Yields protocol wire dicts like a real Adapter.run_turn."""

    def run_turn(self, text):
        async def gen():
            yield {"type": "think", "text": "considering"}
            yield {"type": "action", "name": "Read", "detail": "app.py", "status": "start"}
            yield {"type": "transcript", "speaker": "assistant", "text": f"answered: {text}"}
            yield {"type": "done", "full_text": "answered"}

        return gen()


def test_drive_adapter_forwards_all_events():
    async def run():
        ws = FakeWS()
        await drive_adapter(PresenceSender(ws), FakeAdapter(), "hello")
        return ws.sent

    sent = asyncio.run(run())
    assert [e["type"] for e in sent] == ["think", "action", "transcript", "done"]
    assert all(p.is_valid_presence_event(e) for e in sent)
    assert sent[2]["text"] == "answered: hello"
