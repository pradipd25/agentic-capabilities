"""ClaudeAgentProcessor — drive the avatar from Claude Code's agent loop.

Drops into the pipeline where the LLM service normally sits. On each user turn
(an ``LLMContextFrame`` produced from STT transcription or typed input) it runs a
turn on a `ClaudeAgentAdapter` and translates the adapter's Presence Protocol
events into the pipeline:

- speech tokens → ``TextFrame`` downstream (TTS speaks; AvatarStateProcessor shows
  them and builds the assistant bubble),
- action/ask/status/think → forwarded verbatim to the client websocket (shown,
  never spoken),
- the turn is wrapped in ``LLMFullResponseStartFrame`` / ``LLMFullResponseEndFrame``
  so the existing AvatarStateProcessor + TTS behave exactly as for the LLM path.

The turn runs as a background task so the processor keeps handling frames; an
``InterruptionFrame`` (barge-in) cancels it and calls ``adapter.interrupt()``.

The Agent SDK keeps its own session state, so the Pipecat context aggregators and
ContextSanitizer are not needed on this path.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any, Optional

from fastapi import WebSocket
from pipecat.frames.frames import (
    Frame,
    InterruptionFrame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from backend.processors.agent_routing import extract_last_user_text, route_event

# Local-first: make the in-repo adapter + protocol packages importable without install.
for _pkg in ("adapters/python", "presence-protocol/python"):
    _path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "packages", _pkg))
    if os.path.isdir(_path) and _path not in sys.path:
        sys.path.insert(0, _path)


class ClaudeAgentProcessor(FrameProcessor):
    def __init__(self, adapter: Any, websocket: WebSocket, **kwargs):
        super().__init__(**kwargs)
        self._adapter = adapter
        self._ws = websocket
        self._turn: Optional[asyncio.Task] = None
        # Pre-warm in the background (spawns the `claude` CLI subprocess, ~3-5s)
        # while the session finishes connecting (STT/VAD model loads etc.), so
        # the user's first message doesn't pay that cold-start cost.
        self._warm_up: asyncio.Task = asyncio.create_task(self._warm_up_safely())

    async def _warm_up_safely(self) -> None:
        try:
            await self._adapter.warm_up()
        except Exception:
            pass  # `_ensure_client` retries lazily on the first real turn

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, InterruptionFrame):
            await self._cancel_turn()
            try:
                await self._adapter.interrupt()
            except Exception:
                pass
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, LLMContextFrame):
            text = self._user_text(frame)
            if text:
                await self._cancel_turn()
                self._turn = asyncio.create_task(self._run_turn(text))
            return  # consume — the adapter, not the LLM service, handles this turn

        await self.push_frame(frame, direction)

    def _user_text(self, frame: LLMContextFrame) -> str:
        ctx = getattr(frame, "context", None)
        messages = []
        if ctx is not None:
            getter = getattr(ctx, "get_messages", None)
            messages = getter() if callable(getter) else getattr(ctx, "messages", [])
        return extract_last_user_text(messages)

    async def _run_turn(self, text: str) -> None:
        # The agent loop typically runs several tool calls (Read/Glob/Grep/...)
        # before producing its first word — 10-15s of silence in practice. Without
        # feedback the avatar looks frozen, so switch it to "thinking" immediately;
        # the first `action`/`speak_delta` from the adapter will update it further.
        await self._send_ws({"type": "think", "text": "Thinking…"})
        await self.push_frame(LLMFullResponseStartFrame(), FrameDirection.DOWNSTREAM)
        try:
            async for event in self._adapter.run_turn(text):
                kind, payload = route_event(event)
                if kind == "speak":
                    if payload:
                        await self.push_frame(TextFrame(text=payload), FrameDirection.DOWNSTREAM)
                elif kind == "ws":
                    await self._send_ws(payload)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # surface adapter errors to the client
            await self._send_ws({"type": "error", "message": str(e)})
        finally:
            await self.push_frame(LLMFullResponseEndFrame(), FrameDirection.DOWNSTREAM)

    async def _cancel_turn(self) -> None:
        if self._turn and not self._turn.done():
            self._turn.cancel()
            try:
                await self._turn
            except (asyncio.CancelledError, Exception):
                pass
        self._turn = None

    async def cleanup(self) -> None:
        # Tear down everything tied to this session: an in-flight turn would
        # otherwise keep streaming TextFrames/TTS into a closing pipeline, and the
        # warm-up task / adapter session would leak the `claude` CLI subprocess.
        if self._warm_up and not self._warm_up.done():
            self._warm_up.cancel()
            try:
                await self._warm_up
            except (asyncio.CancelledError, Exception):
                pass
        await self._cancel_turn()
        try:
            await self._adapter.close()
        except Exception:
            pass
        await super().cleanup()

    async def _send_ws(self, payload: dict[str, Any]) -> None:
        try:
            await self._ws.send_text(json.dumps(payload))
        except Exception:
            pass


def build_claude_adapter(settings: Any) -> Any:
    """Construct a ClaudeAgentAdapter from settings (lazy import of the package)."""
    from agent_face_adapters import ClaudeAgentAdapter

    allowed = [t.strip() for t in (settings.agent_allowed_tools or "").split(",") if t.strip()]
    # "preset" + "append" keeps Claude Code's baseline tool-use grounding (better
    # answers/tool choices than replacing the prompt outright) while layering on
    # the voice constraints — TTS reads this output aloud, so markdown/length matter.
    system_prompt = (
        {"type": "preset", "preset": "claude_code", "append": settings.agent_system_prompt}
        if settings.agent_system_prompt
        else None
    )
    return ClaudeAgentAdapter(
        allowed_tools=allowed or None,
        system_prompt=system_prompt,
        permission_mode=settings.agent_permission_mode,
        model=settings.llm_model or None,
    )
