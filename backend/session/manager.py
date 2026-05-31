import asyncio
from datetime import datetime

from backend.session.models import SessionInfo


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, SessionInfo] = {}
        self._pending: dict[str, SessionInfo] = {}  # created but not yet connected
        self._lock = asyncio.Lock()

    async def create(
        self,
        session_id: str,
        avatar_id: str,
        system_prompt: str,
        llm_provider: str,
        llm_model: str,
    ) -> SessionInfo:
        async with self._lock:
            info = SessionInfo(
                session_id=session_id,
                avatar_id=avatar_id,
                system_prompt=system_prompt,
                llm_provider=llm_provider,
                llm_model=llm_model,
            )
            self._pending[session_id] = info
            return info

    async def register_task(self, session_id: str, task) -> None:
        async with self._lock:
            info = self._pending.pop(session_id, None)
            if info is None:
                info = self._sessions.get(session_id)
            if info:
                info.task = task
                self._sessions[session_id] = info

    async def remove(self, session_id: str) -> None:
        async with self._lock:
            self._sessions.pop(session_id, None)
            self._pending.pop(session_id, None)

    def get(self, session_id: str) -> SessionInfo | None:
        return self._sessions.get(session_id) or self._pending.get(session_id)

    def list_sessions(self) -> list[dict]:
        return [s.to_dict() for s in self._sessions.values()]

    async def close_session(self, session_id: str) -> bool:
        info = self._sessions.get(session_id)
        if info and info.task:
            await info.task.cancel()
            await self.remove(session_id)
            return True
        return False
