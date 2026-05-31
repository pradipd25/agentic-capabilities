from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SessionInfo:
    session_id: str
    avatar_id: str
    system_prompt: str
    llm_provider: str
    llm_model: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    task: object = None  # PipelineTask — typed as object to avoid circular import

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "avatar_id": self.avatar_id,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "created_at": self.created_at.isoformat(),
        }
