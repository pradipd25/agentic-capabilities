"""Presence Protocol event models (version 0.1.0).

The transport-agnostic contract between an agent adapter and a face renderer.
See ../../README.md for the full spec.

Downstream (agent -> face): ``PresenceEvent``
Upstream   (face -> agent): ``ControlMessage``
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, Field, TypeAdapter

PROTOCOL_VERSION = "0.1.0"

# ---- shared vocabulary ----

Animation = Literal["idle", "listening", "thinking", "talking", "greeting"]
Speaker = Literal["user", "assistant"]
ActionStatus = Literal["start", "success", "error"]
AskKind = Literal["clarify", "approve"]


# ---- downstream: agent -> face (presence events) ----


class SessionReady(BaseModel):
    type: Literal["session_ready"] = "session_ready"
    session_id: str
    protocol_version: str = PROTOCOL_VERSION
    avatar: Optional[dict[str, Any]] = None
    available_avatars: list[dict[str, Any]] = Field(default_factory=list)
    voice_id: Optional[str] = None


class AvatarState(BaseModel):
    type: Literal["avatar_state"] = "avatar_state"
    animation: Animation
    speaking: bool = False
    audio_level: Optional[float] = None


class SpeakDelta(BaseModel):
    """A streamed token of conversational text. Spoken via TTS."""

    type: Literal["speak_delta"] = "speak_delta"
    text: str


class Transcript(BaseModel):
    type: Literal["transcript"] = "transcript"
    speaker: Speaker
    text: str


class Think(BaseModel):
    type: Literal["think"] = "think"
    text: Optional[str] = None


class Action(BaseModel):
    """A tool/step the agent took. Rendered as a chip; never spoken aloud."""

    type: Literal["action"] = "action"
    name: str
    detail: Optional[str] = None
    input: Optional[dict[str, Any]] = None
    status: ActionStatus = "start"
    id: Optional[str] = None


class Ask(BaseModel):
    type: Literal["ask"] = "ask"
    id: str
    question: str
    kind: AskKind = "clarify"
    options: Optional[list[str]] = None


class Status(BaseModel):
    type: Literal["status"] = "status"
    text: Optional[str] = None
    progress: Optional[float] = None


class AvatarChanged(BaseModel):
    type: Literal["avatar_changed"] = "avatar_changed"
    avatar: dict[str, Any]


class VoiceChanged(BaseModel):
    type: Literal["voice_changed"] = "voice_changed"
    voice_id: str
    reconnect_required: bool = False


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str
    code: Optional[str] = None


class Done(BaseModel):
    type: Literal["done"] = "done"
    full_text: Optional[str] = None
    cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    turns: Optional[int] = None


PresenceEvent = Annotated[
    Union[
        SessionReady,
        AvatarState,
        SpeakDelta,
        Transcript,
        Think,
        Action,
        Ask,
        Status,
        AvatarChanged,
        VoiceChanged,
        ErrorEvent,
        Done,
    ],
    Field(discriminator="type"),
]


# ---- upstream: face -> agent (control messages) ----


class UserTurn(BaseModel):
    type: Literal["user_turn"] = "user_turn"
    text: str


class Interrupt(BaseModel):
    type: Literal["interrupt"] = "interrupt"


class AskResponse(BaseModel):
    type: Literal["ask_response"] = "ask_response"
    id: str
    value: str


class SetAvatar(BaseModel):
    type: Literal["set_avatar"] = "set_avatar"
    avatar_id: str


class SetVoice(BaseModel):
    type: Literal["set_voice"] = "set_voice"
    voice_id: str


ControlMessage = Annotated[
    Union[UserTurn, Interrupt, AskResponse, SetAvatar, SetVoice],
    Field(discriminator="type"),
]


# ---- conformance helpers ----

_presence_adapter: TypeAdapter = TypeAdapter(PresenceEvent)
_control_adapter: TypeAdapter = TypeAdapter(ControlMessage)


def parse_presence_event(data: Union[str, bytes, dict[str, Any]]):
    """Validate and parse a downstream presence event (dict or JSON)."""
    if isinstance(data, (str, bytes)):
        return _presence_adapter.validate_json(data)
    return _presence_adapter.validate_python(data)


def parse_control_message(data: Union[str, bytes, dict[str, Any]]):
    """Validate and parse an upstream control message (dict or JSON)."""
    if isinstance(data, (str, bytes)):
        return _control_adapter.validate_json(data)
    return _control_adapter.validate_python(data)


def is_valid_presence_event(data: Union[str, bytes, dict[str, Any]]) -> bool:
    try:
        parse_presence_event(data)
        return True
    except Exception:
        return False


def is_valid_control_message(data: Union[str, bytes, dict[str, Any]]) -> bool:
    try:
        parse_control_message(data)
        return True
    except Exception:
        return False


def to_wire(event: BaseModel) -> dict[str, Any]:
    """Serialize an event/message to a plain dict suitable for JSON transport."""
    return event.model_dump(exclude_none=True)
