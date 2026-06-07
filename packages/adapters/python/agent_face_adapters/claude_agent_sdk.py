"""Claude Agent SDK adapter — embeds Claude Code's agent loop behind the protocol.

The SDK->protocol translation lives in `map_sdk_message`, a pure function that
inspects messages by class name so it is unit-testable without importing or
authenticating the Claude Agent SDK. The `ClaudeAgentAdapter` wraps a persistent
`ClaudeSDKClient` and is exercised only when the SDK + an API key are present.

Mapping (with `include_partial_messages=True`):
  StreamEvent text_delta  -> speak_delta   (streamed, spoken)
  AssistantMessage TextBlock -> transcript (final assistant line, spoken)
  AssistantMessage ToolUseBlock -> action  (shown, never spoken)
  ResultMessage           -> done
A PreToolUse hook (wired in the adapter) -> ask, for edit/bash approvals.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Optional

from presence_protocol import (
    Action,
    Done,
    SpeakDelta,
    Transcript,
    to_wire,
)

from agent_face_adapters.base import Adapter

# Read-only "discussion" default — safe first integration (no edits / no shell).
READ_ONLY_TOOLS = ["Read", "Glob", "Grep", "WebSearch", "WebFetch"]

# Side-effecting built-in tools that must be denied unless explicitly allowed.
# This is the *enforced* gate: in this SDK's non-interactive (streaming) mode the
# `can_use_tool` callback is never invoked and `allowed_tools` only auto-approves —
# it does not restrict — so a "read-only" run would otherwise still reach for Bash.
# `disallowed_tools` is the one knob the CLI actually enforces (verified: a denied
# Edit leaves the file untouched even when the model spawns a subagent to retry).
WRITE_TOOLS = frozenset({"Bash", "Edit", "Write", "NotebookEdit"})


def _base_tool_name(name: str) -> str:
    """Strip any specifier — ``Bash(npm:*)`` -> ``Bash`` — for allowlist matching."""
    return name.split("(", 1)[0].strip()


def _disallowed_for(allowed: list[str]) -> list[str]:
    """Side-effecting tools to block: every WRITE_TOOL not in the allowlist.

    ``"*"`` anywhere in ``allowed`` disables the restriction entirely (opt-in to the
    agent's full default toolset).
    """
    if any(_base_tool_name(t) == "*" for t in allowed):
        return []
    permitted = {_base_tool_name(t) for t in allowed}
    return sorted(WRITE_TOOLS - permitted)


def _summarize_tool(name: str, tool_input: Optional[dict[str, Any]]) -> Optional[str]:
    """Human one-line summary for an action chip (path, pattern, or command)."""
    data = tool_input or {}
    if name in ("Read", "Edit", "Write"):
        return data.get("file_path") or data.get("path")
    if name in ("Glob", "Grep"):
        return data.get("pattern") or data.get("path") or data.get("file_path")
    if name == "Bash":
        cmd = str(data.get("command", ""))
        return (cmd[:60] + "…") if len(cmd) > 60 else cmd or None
    return None


def map_sdk_message(message: Any) -> list[dict[str, Any]]:
    """Translate one Claude Agent SDK message into Presence Protocol wire dicts.

    Pure and SDK-import-free: dispatches on `type(message).__name__` so synthetic
    objects can drive it in tests.
    """
    events: list[Any] = []
    cls = type(message).__name__

    if cls == "StreamEvent":
        event = getattr(message, "event", None) or {}
        if isinstance(event, dict) and event.get("type") == "content_block_delta":
            delta = event.get("delta") or {}
            if delta.get("type") == "text_delta" and delta.get("text"):
                events.append(SpeakDelta(text=delta["text"]))

    elif cls == "AssistantMessage":
        for block in getattr(message, "content", None) or []:
            bname = type(block).__name__
            if bname == "TextBlock":
                text = getattr(block, "text", "") or ""
                if text.strip():
                    events.append(Transcript(speaker="assistant", text=text))
            elif bname == "ToolUseBlock":
                name = getattr(block, "name", "tool")
                tool_input = getattr(block, "input", None)
                events.append(
                    Action(
                        id=getattr(block, "id", None),
                        name=name,
                        detail=_summarize_tool(name, tool_input),
                        input=tool_input,
                        status="start",
                    )
                )

    elif cls == "ResultMessage":
        events.append(
            Done(
                full_text=getattr(message, "result", None),
                cost_usd=getattr(message, "total_cost_usd", None),
                duration_ms=getattr(message, "duration_ms", None),
                turns=getattr(message, "num_turns", None),
            )
        )

    # SystemMessage(init) etc. carry no presence payload here.
    return [to_wire(e) for e in events]


class ClaudeAgentAdapter(Adapter):
    """Embeds Claude Code's agent loop via the Claude Agent SDK.

    Lazily imports `claude_agent_sdk` so importing this module never requires the
    SDK. Construct with `allowed_tools=None` to keep the read-only default.
    """

    def __init__(
        self,
        *,
        allowed_tools: Optional[list[str]] = None,
        system_prompt: Optional[Any] = None,
        cwd: Optional[str] = None,
        permission_mode: str = "default",
        model: Optional[str] = None,
    ) -> None:
        self._allowed_tools = READ_ONLY_TOOLS if allowed_tools is None else allowed_tools
        self._system_prompt = system_prompt
        self._cwd = cwd
        self._permission_mode = permission_mode
        self._model = model
        self._client: Any = None
        # `_ensure_client` can be entered concurrently — `warm_up()` (background,
        # at session start) and `run_turn()` (on the user's first message) race to
        # connect. Without serializing, the second caller would see `_client` set
        # (assigned before `connect()` resolves) and proceed to `query()` on a
        # not-yet-connected client, hanging indefinitely. The lock makes the second
        # caller wait for the first connect to finish instead.
        self._connect_lock = asyncio.Lock()

    async def _ensure_client(self) -> None:
        # `warm_up()` (background, at session start) and `run_turn()` (on the
        # user's first message) can race to connect here. Without the lock, the
        # second caller would see `_client` set — assigned before `connect()`
        # resolves — and proceed to `query()` on a not-yet-connected client,
        # hanging indefinitely. Serialize, and only publish `_client` once
        # `connect()` has actually completed.
        async with self._connect_lock:
            if self._client is not None:
                return
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

            options = ClaudeAgentOptions(
                allowed_tools=self._allowed_tools,
                disallowed_tools=_disallowed_for(self._allowed_tools),
                system_prompt=self._system_prompt,
                cwd=self._cwd,
                permission_mode=self._permission_mode,
                include_partial_messages=True,
                **({"model": self._model} if self._model else {}),
            )
            client = ClaudeSDKClient(options=options)
            await client.connect()
            self._client = client

    async def warm_up(self) -> None:
        """Spawn + connect the `claude` CLI subprocess ahead of the first turn.

        Measured ~3-5s on a cold connect — paid once per adapter instance. Calling
        this at session start (in the background, while STT/TTS models load) means
        the user's first message doesn't wait on it; `_ensure_client` is a no-op
        once connected.
        """
        await self._ensure_client()

    async def run_turn(self, text: str) -> AsyncIterator[dict[str, Any]]:
        await self._ensure_client()
        await self._client.query(text)
        async for message in self._client.receive_response():
            for wire in map_sdk_message(message):
                yield wire

    async def interrupt(self) -> None:
        if self._client is not None:
            await self._client.interrupt()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None
