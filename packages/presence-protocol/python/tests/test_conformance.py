"""Conformance tests for the Presence Protocol (v0.1.0)."""

import pytest

import presence_protocol as p


@pytest.mark.parametrize(
    "event",
    [
        {"type": "session_ready", "session_id": "s1"},
        {"type": "avatar_state", "animation": "talking", "speaking": True},
        {"type": "speak_delta", "text": "hello"},
        {"type": "transcript", "speaker": "assistant", "text": "hi there"},
        {"type": "think", "text": "considering options"},
        {"type": "action", "name": "Edit", "detail": "app.py", "status": "success"},
        {"type": "ask", "id": "a1", "question": "Run tests?", "kind": "approve", "options": ["yes", "no"]},
        {"type": "status", "text": "working", "progress": 0.5},
        {"type": "voice_changed", "voice_id": "nova", "reconnect_required": True},
        {"type": "error", "message": "boom", "code": "E1"},
        {"type": "done", "full_text": "done", "cost_usd": 0.01, "turns": 3},
    ],
)
def test_valid_presence_events(event):
    assert p.is_valid_presence_event(event)


@pytest.mark.parametrize(
    "bad",
    [
        {"type": "bogus"},
        {"type": "avatar_state", "animation": "flying"},  # bad enum
        {"type": "speak_delta"},  # missing required text
        {"type": "user_turn", "text": "x"},  # upstream, not a presence event
    ],
)
def test_invalid_presence_events(bad):
    assert not p.is_valid_presence_event(bad)


@pytest.mark.parametrize(
    "msg",
    [
        {"type": "user_turn", "text": "add dark mode"},
        {"type": "interrupt"},
        {"type": "ask_response", "id": "a1", "value": "yes"},
        {"type": "set_avatar", "avatar_id": "nova"},
        {"type": "set_voice", "voice_id": "coral"},
    ],
)
def test_valid_control_messages(msg):
    assert p.is_valid_control_message(msg)


def test_invalid_control_message_wrong_direction():
    assert not p.is_valid_control_message({"type": "speak_delta", "text": "x"})


def test_roundtrip_construct_wire_parse():
    wire = p.to_wire(p.Action(name="Read", detail="auth.py"))
    assert wire == {"type": "action", "name": "Read", "detail": "auth.py", "status": "start"}
    parsed = p.parse_presence_event(wire)
    assert parsed.name == "Read"
    assert parsed.status == "start"


def test_json_string_input():
    parsed = p.parse_presence_event('{"type": "speak_delta", "text": "hi"}')
    assert parsed.text == "hi"


def test_protocol_version():
    assert p.PROTOCOL_VERSION == "0.1.0"
