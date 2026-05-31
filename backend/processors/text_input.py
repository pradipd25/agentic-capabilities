import json

from fastapi import WebSocket
from pipecat.frames.frames import (
    Frame,
    InputTransportMessageFrame,
    LLMContextFrame,
)
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class TextInputProcessor(FrameProcessor):
    """
    Handles incoming JSON WebSocket messages:

    - ``text_input``  → adds user text to LLMContext and triggers LLM
    - ``set_avatar``  → looks up new avatar, sends avatar_changed event back
    """

    def __init__(self, context: LLMContext, websocket: WebSocket, avatar_registry, **kwargs):
        super().__init__(**kwargs)
        self._context = context
        self._ws = websocket
        self._avatar_registry = avatar_registry

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, InputTransportMessageFrame):
            try:
                msg = json.loads(frame.message)
                msg_type = msg.get("type")

                if msg_type == "text_input":
                    text = msg.get("text", "").strip()
                    if text:
                        self._context.add_message({"role": "user", "content": text})
                        await self.push_frame(LLMContextFrame(context=self._context))
                    return  # consumed

                if msg_type == "set_avatar":
                    avatar_id = msg.get("avatar_id", "")
                    new_avatar = self._avatar_registry.get_avatar(avatar_id)
                    if new_avatar:
                        try:
                            await self._ws.send_text(json.dumps({
                                "type": "avatar_changed",
                                "avatar": new_avatar.model_dump(),
                            }))
                        except Exception:
                            pass
                    return  # consumed

                if msg_type == "set_voice":
                    voice_id = msg.get("voice_id", "")
                    try:
                        await self._ws.send_text(json.dumps({
                            "type": "voice_change_ack",
                            "voice_id": voice_id,
                            "reconnect_required": True,
                        }))
                    except Exception:
                        pass
                    return  # consumed

            except Exception:
                pass

        await self.push_frame(frame, direction)
