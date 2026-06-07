"""Tests for the MCP presence bridge (builders + AskRegistry).

Depends only on `presence_protocol` (resolved via the bridge's path shim) and
asyncio — no `mcp`/`pipecat` required.
"""

import asyncio

import presence_protocol as p

from backend.mcp_server import presence


def test_action_event_is_valid_and_shaped():
    ev = presence.action_event(name="Edit", detail="app.py", status="success", id="t1")
    assert p.is_valid_presence_event(ev)
    assert ev == {"type": "action", "id": "t1", "name": "Edit", "detail": "app.py", "status": "success"}


def test_ask_event_with_options():
    ev = presence.ask_event(id="a1", question="Run tests?", kind="approve", options=["Yes", "No"])
    assert p.is_valid_presence_event(ev)
    assert ev["type"] == "ask" and ev["kind"] == "approve" and ev["options"] == ["Yes", "No"]


def test_status_and_avatar_and_voice_events_valid():
    assert p.is_valid_presence_event(presence.status_event(text="working", progress=0.5))
    assert p.is_valid_presence_event(presence.avatar_state_event("thinking"))
    assert p.is_valid_presence_event(presence.transcript_event("assistant", "hi"))
    ev = presence.voice_changed_event("nova", reconnect_required=True)
    assert p.is_valid_presence_event(ev) and ev["reconnect_required"] is True


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, text):
        self.sent.append(text)


def test_send_event_serializes_to_websocket():
    async def run():
        ws = FakeWS()
        await presence.send_event(ws, presence.action_event(name="Read", detail="auth.py"))
        return ws.sent

    sent = asyncio.run(run())
    assert len(sent) == 1
    assert '"type": "action"' in sent[0]
    assert '"name": "Read"' in sent[0]


def test_ask_registry_resolves_waiter():
    async def run():
        reg = presence.AskRegistry()

        async def answer_later():
            await asyncio.sleep(0.01)
            assert reg.resolve("a1", "Yes") is True

        waiter = asyncio.create_task(reg.wait("a1", timeout=2))
        await answer_later()
        return await waiter

    assert asyncio.run(run()) == "Yes"


def test_ask_registry_times_out():
    async def run():
        reg = presence.AskRegistry()
        return await reg.wait("missing", timeout=0.05)

    assert asyncio.run(run()) is None


def test_ask_registry_resolve_unknown_is_false():
    reg = presence.AskRegistry()
    assert reg.resolve("nope", "x") is False
