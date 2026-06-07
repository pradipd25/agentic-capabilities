"""Agent Face — Python headless SDK.

`PresenceSender` emits validated Presence Protocol events over any async transport
(anything with `async send_text(str)` or `async send(str)` — e.g. a FastAPI
WebSocket). `drive_adapter` pumps an `Adapter`'s output to a sender, wiring an
agent (e.g. the Claude Agent SDK adapter) to a face with one call.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any, AsyncIterator, Optional

# Local-first: resolve the in-repo presence-protocol package without an install.
_PP_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "presence-protocol", "python")
)
if os.path.isdir(_PP_PATH) and _PP_PATH not in sys.path:
    sys.path.insert(0, _PP_PATH)

from presence_protocol import (  # noqa: E402
    Action,
    Ask,
    AvatarState,
    Done,
    SpeakDelta,
    Status,
    Think,
    Transcript,
    is_valid_presence_event,
    to_wire,
)

__all__ = ["PresenceSender", "drive_adapter"]


class PresenceSender:
    """Validate and emit Presence Protocol events over an async transport."""

    def __init__(self, transport: Any) -> None:
        self._transport = transport

    async def _send(self, text: str) -> None:
        t = self._transport
        send_text = getattr(t, "send_text", None)
        if send_text is not None:
            await send_text(text)
        else:
            await t.send(text)

    async def emit(self, event: Any) -> dict[str, Any]:
        """Emit a wire dict or a protocol model. Validates before sending."""
        wire = event if isinstance(event, dict) else to_wire(event)
        if not is_valid_presence_event(wire):
            raise ValueError(f"not a valid presence event: {wire!r}")
        await self._send(json.dumps(wire))
        return wire

    # typed convenience emitters
    async def speak_delta(self, text: str) -> dict[str, Any]:
        return await self.emit(SpeakDelta(text=text))

    async def transcript(self, speaker: str, text: str) -> dict[str, Any]:
        return await self.emit(Transcript(speaker=speaker, text=text))

    async def think(self, text: Optional[str] = None) -> dict[str, Any]:
        return await self.emit(Think(text=text))

    async def action(
        self,
        name: str,
        detail: Optional[str] = None,
        status: str = "start",
        id: Optional[str] = None,
    ) -> dict[str, Any]:
        return await self.emit(Action(name=name, detail=detail, status=status, id=id))

    async def ask(
        self,
        id: str,
        question: str,
        kind: str = "clarify",
        options: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        return await self.emit(Ask(id=id, question=question, kind=kind, options=options))

    async def status(
        self, text: Optional[str] = None, progress: Optional[float] = None
    ) -> dict[str, Any]:
        return await self.emit(Status(text=text, progress=progress))

    async def avatar_state(self, animation: str, speaking: bool = False) -> dict[str, Any]:
        return await self.emit(AvatarState(animation=animation, speaking=speaking))

    async def done(self, **kwargs: Any) -> dict[str, Any]:
        return await self.emit(Done(**kwargs))


async def drive_adapter(sender: PresenceSender, adapter: Any, text: str) -> None:
    """Run one turn on an Adapter and forward every event to the sender."""
    agen: AsyncIterator[dict[str, Any]] = adapter.run_turn(text)
    async for wire in agen:
        await sender.emit(wire)
