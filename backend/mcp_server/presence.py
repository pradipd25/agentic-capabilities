"""Presence bridge for the MCP surface.

Dependency-light (only `presence_protocol`, no `mcp`/`pipecat`) so it is unit
testable on its own. Provides:

- pure event builders that return validated Presence Protocol wire dicts,
- `send_event` to push a wire dict to a session websocket,
- `AskRegistry`, an asyncio-future registry so an `avatar.ask` MCP tool call can
  block until the user answers in the UI (resolved by an upstream `ask_response`).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Optional

# Local-first: make the in-repo presence-protocol package importable without an
# install step (start.sh / dev). A real install (pip install -e) also works.
_PP_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "packages", "presence-protocol", "python")
)
if os.path.isdir(_PP_PATH) and _PP_PATH not in sys.path:
    sys.path.insert(0, _PP_PATH)

from presence_protocol import (  # noqa: E402
    Action,
    Ask,
    AvatarState,
    Status,
    Transcript,
    VoiceChanged,
    to_wire,
)


# ---- pure event builders (return wire dicts) ----


def action_event(
    name: str,
    detail: Optional[str] = None,
    status: str = "start",
    id: Optional[str] = None,
) -> dict[str, Any]:
    return to_wire(Action(id=id, name=name, detail=detail, status=status))


def ask_event(
    id: str,
    question: str,
    kind: str = "clarify",
    options: Optional[list[str]] = None,
) -> dict[str, Any]:
    return to_wire(Ask(id=id, question=question, kind=kind, options=options))


def status_event(text: Optional[str] = None, progress: Optional[float] = None) -> dict[str, Any]:
    return to_wire(Status(text=text, progress=progress))


def avatar_state_event(animation: str, speaking: bool = False) -> dict[str, Any]:
    return to_wire(AvatarState(animation=animation, speaking=speaking))


def transcript_event(speaker: str, text: str) -> dict[str, Any]:
    return to_wire(Transcript(speaker=speaker, text=text))


def voice_changed_event(voice_id: str, reconnect_required: bool = False) -> dict[str, Any]:
    return to_wire(VoiceChanged(voice_id=voice_id, reconnect_required=reconnect_required))


# ---- transport ----


async def send_event(ws: Any, event: dict[str, Any]) -> None:
    """Push a presence-event wire dict to a session websocket."""
    await ws.send_text(json.dumps(event))


# ---- ask round-trip ----


class AskRegistry:
    """Tracks pending `ask` requests so a tool call can await the user's answer.

    The MCP tool creates a future and `wait()`s on it; the websocket handler calls
    `resolve()` when an `ask_response` arrives for that id.
    """

    def __init__(self) -> None:
        self._futures: dict[str, asyncio.Future[str]] = {}

    def create(self, ask_id: str) -> "asyncio.Future[str]":
        fut: asyncio.Future[str] = asyncio.get_event_loop().create_future()
        self._futures[ask_id] = fut
        return fut

    def resolve(self, ask_id: str, value: str) -> bool:
        fut = self._futures.pop(ask_id, None)
        if fut is not None and not fut.done():
            fut.set_result(value)
            return True
        return False

    async def wait(self, ask_id: str, timeout: float = 120.0) -> Optional[str]:
        fut = self._futures.get(ask_id) or self.create(ask_id)
        try:
            return await asyncio.wait_for(fut, timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self._futures.pop(ask_id, None)
