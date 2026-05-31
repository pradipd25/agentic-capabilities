import json

from pipecat.frames.frames import (
    Frame,
    InputAudioRawFrame,
    InputTransportMessageFrame,
    OutputAudioRawFrame,
    OutputTransportMessageFrame,
)
from pipecat.serializers.base_serializer import FrameSerializer

AUDIO_SAMPLE_RATE = 16000
AUDIO_CHANNELS = 1


class RawAudioSerializer(FrameSerializer):
    """
    Simple serializer for browser WebSocket clients that send:
      - Binary frames: raw PCM s16le audio at 16 kHz mono
      - Text frames:   JSON messages (text_input, set_avatar, interrupt, …)

    Outgoing audio is sent as raw PCM bytes (no protobuf, no WAV header —
    the WAV header is added by FastAPIWebsocketParams.add_wav_header).
    Outgoing text messages are sent as JSON strings.
    """

    async def serialize(self, frame: Frame) -> str | bytes | None:
        if isinstance(frame, OutputAudioRawFrame):
            return frame.audio
        if isinstance(frame, OutputTransportMessageFrame):
            return json.dumps(frame.message)
        return None

    async def deserialize(self, data: str | bytes) -> Frame | None:
        if isinstance(data, (bytes, bytearray)):
            return InputAudioRawFrame(
                audio=bytes(data),
                num_channels=AUDIO_CHANNELS,
                sample_rate=AUDIO_SAMPLE_RATE,
            )
        if isinstance(data, str):
            return InputTransportMessageFrame(message=data)
        return None
