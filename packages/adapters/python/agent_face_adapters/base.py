"""Adapter SPI — the interface every agent source implements.

An adapter translates a specific agent ecosystem (Claude Agent SDK, MCP, OpenAI,
raw stream) into the Presence Protocol. The renderer never sees the agent's native
events — only the normalized `PresenceEvent` wire dicts an adapter yields.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator


class Adapter(ABC):
    """Translates an agent source into a stream of Presence Protocol events.

    Implementations yield protocol wire dicts (see `presence_protocol`) from
    `run_turn`. Downstream transport (WebSocket/MCP/SSE) is the caller's concern.
    """

    @abstractmethod
    def run_turn(self, text: str) -> AsyncIterator[dict[str, Any]]:
        """Process one user turn; yield presence-event wire dicts as they occur."""
        raise NotImplementedError

    async def warm_up(self) -> None:
        """Eagerly establish any session/connection ahead of the first turn.

        Optional — adapters that pay a connection cost on first use (spawning a
        subprocess, opening a socket) can override this so a caller can pre-warm
        it (e.g. at session start, while the user is still reading the page)
        instead of the user's first message paying that latency. No-op by default.
        """
        return None

    async def interrupt(self) -> None:
        """Cancel the in-flight turn (barge-in). No-op by default."""
        return None

    async def answer_ask(self, ask_id: str, value: str) -> None:
        """Provide the response to a pending `ask` event. No-op by default."""
        return None

    async def close(self) -> None:
        """Release any resources / sessions. No-op by default."""
        return None
