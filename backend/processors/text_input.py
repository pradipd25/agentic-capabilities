import json

from fastapi import WebSocket
from pipecat.frames.frames import (
    Frame,
    InputTransportMessageFrame,
    InterruptionFrame,
    LLMContextFrame,
)
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class TextInputProcessor(FrameProcessor):
    """
    Handles incoming JSON WebSocket messages:

    - ``text_input`` / ``user_turn``  → adds user text to LLMContext and triggers LLM
    - ``set_avatar``  → looks up new avatar, sends avatar_changed event back
    - ``set_voice``   → acks voice change (client reconnects)
    - ``ask_response``→ resolves a pending ``avatar.ask`` (MCP surface)
    """

    def __init__(
        self,
        context: LLMContext,
        websocket: WebSocket,
        avatar_registry,
        ask_registry=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._context = context
        self._ws = websocket
        self._avatar_registry = avatar_registry
        self._ask_registry = ask_registry

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, InputTransportMessageFrame):
            try:
                msg = json.loads(frame.message)
                msg_type = msg.get("type")

                # ``user_turn`` is the Presence Protocol name for ``text_input``.
                if msg_type in ("text_input", "user_turn"):
                    text = msg.get("text", "").strip()
                    if text:
                        # Barge-in handling for a text follow-up that arrives while
                        # the avatar is still mid-response (LLM streaming / TTS
                        # speaking):
                        #
                        # Push an InterruptionFrame DOWNSTREAM first. Because it
                        # travels the same direction as the LLMContextFrame we push
                        # right after, the two stay FIFO-ordered: the interruption
                        # reaches the LLM first (cancelling the in-flight completion,
                        # flushing TTS, and making the assistant aggregator commit
                        # whatever was spoken so far), then our context frame triggers
                        # a fresh completion. Routing the interruption upstream
                        # instead (InterruptionTaskFrame) makes the task re-inject it
                        # at the pipeline source, where it can overtake and cancel the
                        # brand-new generation — wedging the pipeline.
                        #
                        # The interrupted partial response is committed AFTER this new
                        # user turn, leaving the context ending in a stale assistant
                        # message. ContextSanitizerProcessor (just before the LLM)
                        # drops that trailing assistant message so the model answers
                        # the follow-up instead of continuing the abandoned reply.
                        await self.push_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
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

                if msg_type == "ask_response":
                    # Resolve a pending avatar.ask so the MCP tool call returns.
                    if self._ask_registry is not None:
                        ask_id = msg.get("id", "")
                        value = msg.get("value", "")
                        if ask_id:
                            self._ask_registry.resolve(ask_id, value)
                    return  # consumed

                if msg_type == "interrupt":
                    # Barge-in / cancel from the client (Presence Protocol control).
                    await self.push_frame(InterruptionFrame(), FrameDirection.DOWNSTREAM)
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
