from pipecat.frames.frames import Frame, LLMContextFrame
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class ContextSanitizerProcessor(FrameProcessor):
    """Guards the LLM against generating from a context that ends in an
    assistant message.

    Placed immediately before the LLM service. A user-triggered completion must
    always have the user's turn as the final message; if the last message is an
    assistant message the chat-completion API treats it as a *prefill* and
    continues that text instead of responding — which is how an interrupted
    reply leaks back (often drifting language, e.g. answering in Spanish) and
    then wedges the conversation.

    This happens after a barge-in: the new user turn is appended, then the
    interrupted partial response is committed *after* it, leaving the context as
    ``[…, user_followup, assistant_partial]``. On each ``LLMContextFrame`` we
    strip any trailing assistant message(s) so generation starts cleanly from
    the user's turn. In the normal, non-interrupted flow the context already
    ends with the user's turn, so this is a no-op.
    """

    def __init__(self, context: LLMContext, **kwargs):
        super().__init__(**kwargs)
        self._context = context

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

        if isinstance(frame, LLMContextFrame):
            messages = self._context.get_messages()
            removed = 0
            # Drop trailing assistant messages, but never touch the system
            # prompt or an otherwise empty conversation.
            while len(messages) > 1 and messages[-1].get("role") == "assistant":
                messages.pop()
                removed += 1
            if removed:
                self._context.set_messages(messages)

        await self.push_frame(frame, direction)
