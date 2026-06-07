"""
End-to-end VOICE path test. Synthesizes speech with OpenAI TTS, replays it to
the backend as mic input (raw PCM s16le 16 kHz mono, the format the browser
sends), and checks whether VAD triggers, Whisper transcribes, and the LLM
responds. Runs an English utterance then a Hindi one to reproduce the
"no response after switching to Hindi" report.

Server must be running:  uvicorn backend.main:app --port 8100
"""
import asyncio
import json
import sys

import numpy as np
from scipy.signal import resample_poly
from openai import AsyncOpenAI

from backend.config import settings

import os
WS = f"ws://localhost:{os.environ.get('PORT', '8100')}/ws/voice-test?voice_id=nova"
FRAME_MS = 20
IN_RATE = 16000
SAMPLES_PER_FRAME = IN_RATE * FRAME_MS // 1000  # 320 samples = 640 bytes


async def synth_pcm16k(text: str) -> bytes:
    """OpenAI TTS → 24 kHz PCM → resample to 16 kHz s16le mono."""
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.audio.speech.create(
        model="tts-1", voice="nova", input=text, response_format="pcm",
    )
    pcm24 = np.frombuffer(resp.content, dtype=np.int16)
    pcm16 = resample_poly(pcm24.astype(np.float32), up=2, down=3)  # 24k -> 16k
    return np.clip(pcm16, -32768, 32767).astype(np.int16).tobytes()


async def stream_utterance(ws, pcm: bytes, lead_silence_ms=300, tail_silence_ms=700):
    """Send leading silence, the speech, then trailing silence so VAD can mark
    start/stop. Pace at real-time (20 ms/frame)."""
    silence = b"\x00\x00" * SAMPLES_PER_FRAME

    async def send_silence(ms):
        for _ in range(ms // FRAME_MS):
            await ws.send(silence)
            await asyncio.sleep(FRAME_MS / 1000)

    await send_silence(lead_silence_ms)
    frame_bytes = SAMPLES_PER_FRAME * 2
    for i in range(0, len(pcm), frame_bytes):
        chunk = pcm[i:i + frame_bytes]
        if len(chunk) < frame_bytes:
            chunk = chunk + b"\x00" * (frame_bytes - len(chunk))
        await ws.send(chunk)
        await asyncio.sleep(FRAME_MS / 1000)
    await send_silence(tail_silence_ms)


async def drain(ws, idle_timeout=10.0):
    """Collect transcript/tokens/audio until idle or silence."""
    transcript_user = []
    tokens = []
    audio = 0
    events = []
    while True:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=idle_timeout)
        except asyncio.TimeoutError:
            break
        if isinstance(msg, bytes):
            audio += len(msg)
            continue
        d = json.loads(msg)
        t = d.get("type")
        events.append(t)
        if t in ("transcript_final", "transcript", "transcription"):
            transcript_user.append(d.get("text", ""))
        elif t == "llm_token":
            tokens.append(d.get("token", ""))
        elif t == "avatar_state" and d.get("animation") == "idle" and tokens:
            break
    return "".join(transcript_user), "".join(tokens), audio, events


async def main():
    print("synthesizing speech...")
    en = await synth_pcm16k("Hello, can you hear me? Please say yes.")
    hi = await synth_pcm16k("नमस्ते, क्या आप मुझे सुन सकते हैं? कृपया हाँ कहें।")
    print(f"  english {len(en)}B, hindi {len(hi)}B (16kHz pcm)")

    import websockets
    async with websockets.connect(WS, max_size=None) as ws:
        print("ready:", json.loads(await ws.recv()).get("type"))

        print("\n[ENGLISH] streaming speech...")
        await stream_utterance(ws, en)
        tr, toks, audio, ev = await drain(ws, idle_timeout=15.0)
        print(f"  transcript={tr!r}")
        print(f"  reply={toks!r} ({audio}B audio)")
        print(f"  events={ev[:12]}")

        # Let turn 1 fully settle so turn 2 is a clean sequential turn rather than
        # an overlap that interrupts turn 1 while Whisper is still busy.
        await asyncio.sleep(3.0)
        await drain(ws, idle_timeout=0.5)  # discard any trailing turn-1 events

        print("\n[HINDI] streaming speech...")
        await stream_utterance(ws, hi)
        tr2, toks2, audio2, ev2 = await drain(ws, idle_timeout=15.0)
        print(f"  transcript={tr2!r}")
        print(f"  reply={toks2!r} ({audio2}B audio)")
        print(f"  events={ev2[:12]}")

    ok = bool(toks.strip()) and bool(toks2.strip())
    print("\n" + ("PASS ✅ both turns answered" if ok else "FAIL ❌ a turn got no reply"))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
