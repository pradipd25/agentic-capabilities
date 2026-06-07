"""Tests for the Claude agent backend's pure routing helpers (no pipecat needed)."""

from backend.processors.agent_routing import extract_last_user_text, route_event, strip_markdown


def test_speak_delta_routes_to_speak():
    assert route_event({"type": "speak_delta", "text": "Hi"}) == ("speak", "Hi")


def test_speak_delta_strips_markdown_through_routing():
    kind, payload = route_event({"type": "speak_delta", "text": "It's the **Presence** `Protocol`."})
    assert kind == "speak"
    assert payload == "It's the Presence Protocol."


# --- strip_markdown: defense-in-depth so TTS never reads literal symbols aloud ---


def test_strip_bold_and_italic():
    assert strip_markdown("This is **bold** and *italic*.") == "This is bold and italic."


def test_underscores_preserved_for_snake_case_identifiers():
    # NOT treated as emphasis — this agent constantly names snake_case symbols;
    # stripping underscores would mangle speak_delta into "speakdelta".
    assert strip_markdown("See `speak_delta` and ask_response in claude_agent.py.") == \
        "See speak_delta and ask_response in claude_agent.py."


def test_stray_backtick_and_asterisk_stragglers_removed():
    # Simulates a code span split across two streamed deltas: paired regexes can't
    # match across the boundary, so lone symbols must be swept up by the catch-all.
    assert strip_markdown("opening ` and a lone * here") == "opening  and a lone  here"


def test_strip_inline_code_keeps_content():
    assert strip_markdown("Run `npm install` to set up.") == "Run npm install to set up."


def test_strip_code_fence_markers():
    assert strip_markdown("```python\nprint(1)\n```") == "\nprint(1)\n"


def test_strip_headings():
    assert strip_markdown("# Title\n## Subtitle\nBody") == "Title\nSubtitle\nBody"


def test_strip_bullet_and_numbered_lists():
    text = "Steps:\n- first\n* second\n1. third\n2) fourth"
    assert strip_markdown(text) == "Steps:\nfirst\nsecond\nthird\nfourth"


def test_plain_text_passes_through_unchanged():
    assert strip_markdown("Just a normal sentence, nothing special.") == \
        "Just a normal sentence, nothing special."


def test_empty_string_passes_through():
    assert strip_markdown("") == ""


def test_side_events_route_to_ws():
    for t in ("action", "ask", "status", "think"):
        kind, payload = route_event({"type": t, "name": "x"})
        assert kind == "ws"
        assert payload["type"] == t


def test_transcript_and_done_are_ignored():
    # rebuilt from streamed tokens by AvatarStateProcessor — avoid duplicates
    assert route_event({"type": "transcript", "speaker": "assistant", "text": "hi"}) == ("ignore", None)
    assert route_event({"type": "done", "full_text": "hi"}) == ("ignore", None)


def test_extract_last_user_text_string_content():
    msgs = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply"},
        {"role": "user", "content": "  latest  "},
    ]
    assert extract_last_user_text(msgs) == "latest"


def test_extract_last_user_text_list_content():
    msgs = [{"role": "user", "content": [{"type": "text", "text": "hello"}, {"type": "text", "text": "world"}]}]
    assert extract_last_user_text(msgs) == "hello world"


def test_extract_last_user_text_empty():
    assert extract_last_user_text([]) == ""
    assert extract_last_user_text(None) == ""
    assert extract_last_user_text([{"role": "assistant", "content": "x"}]) == ""
