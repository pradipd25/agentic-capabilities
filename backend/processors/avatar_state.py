import json

from fastapi import WebSocket
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    TextFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class AvatarStateProcessor(FrameProcessor):
    """
    Translates Pipecat frames into WebSocket avatar-state events.

    Placed BEFORE the TTS service so it sees raw LLM TextFrames (not the
    AggregatedTextFrames that TTS emits after sentence splitting).
    BotStarted/StoppedSpeakingFrame are pushed upstream by the output
    transport so they still arrive here correctly.
    """

    def __init__(self, session_id: str, websocket: WebSocket):
        super().__init__()
        self._session_id = session_id
        self._ws = websocket
        self._llm_response_text: list[str] = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, UserStartedSpeakingFrame):
            await self._send({"type": "avatar_state", "animation": "listening", "speaking": False})

        elif isinstance(frame, UserStoppedSpeakingFrame):
            # Transition to "thinking" while Whisper transcribes
            await self._send({"type": "avatar_state", "animation": "thinking", "speaking": False})

        elif isinstance(frame, TranscriptionFrame):
            await self._send({
                "type": "transcript_final",
                "text": frame.text,
                "speaker": "user",
            })

        elif isinstance(frame, LLMFullResponseStartFrame):
            self._llm_response_text = []

        elif (
            isinstance(frame, TextFrame)
            and not isinstance(frame, TranscriptionFrame)
            and direction == FrameDirection.DOWNSTREAM
        ):
            # Raw LLM token — only seen here because avatar_processor is before TTS
            self._llm_response_text.append(frame.text)
            await self._send({"type": "llm_token", "token": frame.text})

        elif isinstance(frame, LLMFullResponseEndFrame):
            full_text = "".join(self._llm_response_text)
            self._llm_response_text = []
            if full_text:
                await self._send({"type": "llm_done", "full_text": full_text})
                await self._send({
                    "type": "transcript_final",
                    "text": full_text,
                    "speaker": "assistant",
                })

        elif isinstance(frame, BotStartedSpeakingFrame):
            await self._send({"type": "avatar_state", "animation": "talking", "speaking": True})

        elif isinstance(frame, BotStoppedSpeakingFrame):
            await self._send({"type": "avatar_state", "animation": "idle", "speaking": False})

        await self.push_frame(frame, direction)

    async def _send(self, payload: dict) -> None:
        try:
            await self._ws.send_text(json.dumps(payload))
        except Exception:
            pass
