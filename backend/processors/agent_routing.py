"""Pure routing helpers for the Claude agent backend.

Kept free of pipecat imports so it is unit-testable on its own. Decides how each
Presence Protocol event from the adapter should be handled inside the pipeline:

- ``speak`` → conversational text to push as a TextFrame (TTS speaks it; the
  AvatarStateProcessor surfaces it as `llm_token` and builds the assistant bubble).
- ``ws``    → side activity (action/ask/status/think) to forward verbatim to the
  client websocket — shown, never spoken (the speech-vs-action split).
- ``ignore``→ handled elsewhere (e.g. `transcript`/`done`, reconstructed from the
  streamed tokens by the AvatarStateProcessor) to avoid duplicate bubbles.
"""

from __future__ import annotations

import re
from typing import Any

# Side-channel events forwarded to the websocket as-is (not spoken).
_WS_TYPES = frozenset({"action", "ask", "status", "think"})

# Defense-in-depth for the speech path: the system prompt asks Claude Code not to
# use markdown (its TTS output is read aloud verbatim — "**x**" becomes "asterisk
# asterisk x asterisk asterisk"), but the model slips into its default IDE style on
# some prompts regardless. These patterns strip the common offenders from streamed
# deltas so literal symbols are never spoken, without touching the `transcript`/
# `action` side channels (those are shown as text, where markdown renders fine).
_MD_FENCE = re.compile(r"```[a-zA-Z0-9]*")
_MD_INLINE_CODE = re.compile(r"`([^`]*)`")
# Asterisk emphasis only — NOT underscores. This is a codebase-aware agent that
# constantly names snake_case symbols (speak_delta, ask_response, claude_agent.py);
# treating `_` as an emphasis marker would mangle them into "speakdelta"/"askresponse".
_MD_BOLD_ITALIC = re.compile(r"(\*\*\*|\*\*|\*)")
_MD_HEADING = re.compile(r"(?m)^#{1,6}\s*")
_MD_BULLET = re.compile(r"(?m)^[ \t]*[-*+][ \t]+")
_MD_NUMBERED = re.compile(r"(?m)^[ \t]*\d+[.)][ \t]+")
# Catch-all for symbols left over when a construct spans two streamed deltas (e.g.
# an opening backtick in one chunk, the closing one in the next) — paired regexes
# above can't match across that boundary, so any stragglers are removed outright.
_MD_STRAGGLERS = re.compile(r"[`*]")


def strip_markdown(text: str) -> str:
    """Remove common markdown so streamed deltas read as plain spoken prose.

    Applied per-delta, so multi-character constructs split across deltas are
    handled by `_MD_STRAGGLERS` rather than the (delta-local) paired regexes —
    an acceptable trade for not buffering the stream and delaying speech further.
    """
    if not text:
        return text
    out = _MD_FENCE.sub("", text)
    out = _MD_INLINE_CODE.sub(r"\1", out)
    out = _MD_HEADING.sub("", out)
    out = _MD_BULLET.sub("", out)
    out = _MD_NUMBERED.sub("", out)
    out = _MD_BOLD_ITALIC.sub("", out)
    out = _MD_STRAGGLERS.sub("", out)
    return out


def route_event(event: dict[str, Any]) -> tuple[str, Any]:
    """Classify one adapter event. Returns (kind, payload)."""
    t = event.get("type")
    if t == "speak_delta":
        return ("speak", strip_markdown(event.get("text", "")))
    if t in _WS_TYPES:
        return ("ws", event)
    return ("ignore", None)


def extract_last_user_text(messages: list[dict[str, Any]] | None) -> str:
    """Pull the latest user message text out of an LLM context message list."""
    for message in reversed(messages or []):
        if message.get("role") != "user":
            continue
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = [
                part.get("text", "")
                for part in content
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            return " ".join(parts).strip()
    return ""
