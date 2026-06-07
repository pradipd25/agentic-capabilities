"""Tests for the Claude Agent SDK -> Presence Protocol mapper.

Uses synthetic objects whose class names match the SDK's (StreamEvent,
AssistantMessage, TextBlock, ToolUseBlock, ResultMessage) so no SDK install or
API key is required.
"""

import presence_protocol as p

from agent_face_adapters.claude_agent_sdk import (
    READ_ONLY_TOOLS,
    WRITE_TOOLS,
    _disallowed_for,
    map_sdk_message,
)


# --- synthetic SDK-shaped objects (class names matter to the mapper) ---


class StreamEvent:
    def __init__(self, event):
        self.event = event


class TextBlock:
    def __init__(self, text):
        self.text = text


class ToolUseBlock:
    def __init__(self, name, tool_input, id="toolu_1"):
        self.name = name
        self.input = tool_input
        self.id = id


class AssistantMessage:
    def __init__(self, content):
        self.content = content


class ResultMessage:
    def __init__(self, result=None, total_cost_usd=None, duration_ms=None, num_turns=None):
        self.result = result
        self.total_cost_usd = total_cost_usd
        self.duration_ms = duration_ms
        self.num_turns = num_turns


class SystemMessage:
    def __init__(self, subtype):
        self.subtype = subtype


def _all_valid(events):
    assert events, "expected at least one event"
    for e in events:
        assert p.is_valid_presence_event(e), e
    return events


def test_stream_text_delta_maps_to_speak_delta():
    msg = StreamEvent({"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hi"}})
    events = _all_valid(map_sdk_message(msg))
    assert events == [{"type": "speak_delta", "text": "Hi"}]


def test_non_text_stream_event_yields_nothing():
    assert map_sdk_message(StreamEvent({"type": "message_start"})) == []
    assert map_sdk_message(StreamEvent({"type": "content_block_delta", "delta": {"type": "thinking_delta", "thinking": "x"}})) == []


def test_text_block_maps_to_transcript():
    msg = AssistantMessage([TextBlock("Done — added the toggle.")])
    events = _all_valid(map_sdk_message(msg))
    assert events[0]["type"] == "transcript"
    assert events[0]["speaker"] == "assistant"
    assert events[0]["text"] == "Done — added the toggle."


def test_tool_use_block_maps_to_action_with_detail():
    msg = AssistantMessage([ToolUseBlock("Read", {"file_path": "SettingsPage.tsx"})])
    events = _all_valid(map_sdk_message(msg))
    assert events[0]["type"] == "action"
    assert events[0]["name"] == "Read"
    assert events[0]["detail"] == "SettingsPage.tsx"
    assert events[0]["status"] == "start"


def test_bash_action_summary_truncates():
    long_cmd = "echo " + "x" * 100
    msg = AssistantMessage([ToolUseBlock("Bash", {"command": long_cmd})])
    detail = map_sdk_message(msg)[0]["detail"]
    assert detail.endswith("…")
    assert len(detail) <= 61


def test_mixed_text_and_tool_blocks():
    msg = AssistantMessage([TextBlock("Let me check."), ToolUseBlock("Grep", {"pattern": "TODO"})])
    events = _all_valid(map_sdk_message(msg))
    kinds = [e["type"] for e in events]
    assert kinds == ["transcript", "action"]


def test_result_message_maps_to_done():
    msg = ResultMessage(result="all set", total_cost_usd=0.012, duration_ms=4200, num_turns=3)
    events = _all_valid(map_sdk_message(msg))
    assert events[0] == {
        "type": "done",
        "full_text": "all set",
        "cost_usd": 0.012,
        "duration_ms": 4200,
        "turns": 3,
    }


def test_system_message_is_ignored():
    assert map_sdk_message(SystemMessage("init")) == []


def test_empty_text_block_ignored():
    assert map_sdk_message(AssistantMessage([TextBlock("   ")])) == []


# --- tool policy: _disallowed_for enforces the allowlist via a denylist ---


def test_read_only_default_blocks_all_write_tools():
    # The read-only default permits no write tools, so every WRITE_TOOL is denied.
    assert set(_disallowed_for(READ_ONLY_TOOLS)) == set(WRITE_TOOLS)


def test_opting_in_removes_those_from_denylist():
    disallowed = _disallowed_for(["Read", "Edit", "Bash"])
    assert "Edit" not in disallowed
    assert "Bash" not in disallowed
    # Write tools NOT opted into stay blocked.
    assert "Write" in disallowed
    assert "NotebookEdit" in disallowed


def test_specifier_is_stripped_for_matching():
    # "Bash(git:*)" should count as permitting Bash.
    assert "Bash" not in _disallowed_for(["Read", "Bash(git:*)"])


def test_star_disables_all_restrictions():
    assert _disallowed_for(["*"]) == []
    assert _disallowed_for(["Read", "*"]) == []
