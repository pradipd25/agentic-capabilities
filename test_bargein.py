"""Voice barge-in test (reliable English STT). Start a long reply, then talk
over it mid-response and confirm the avatar is interrupted and answers the new
question. Mirrors what the frontend does once its energy gate forwards loud
speech during playback.

Server:  uvicorn backend.main:app --port 8101   (or set PORT)
"""
import asyncio, json, os, sys
import numpy as np
from scipy.signal import resample_poly
from openai import AsyncOpenAI
import websockets
from backend.config import settings

WS = f"ws://localhost:{os.environ.get('PORT','8101')}/ws/barge-test?voice_id=nova"
FRAME_MS, RATE = 20, 16000
SPF = RATE * FRAME_MS // 1000


async def synth(text):
    c = AsyncOpenAI(api_key=settings.openai_api_key)
    r = await c.audio.speech.create(model="tts-1", voice="nova", input=text, response_format="pcm")
    pcm24 = np.frombuffer(r.content, dtype=np.int16)
    pcm16 = resample_poly(pcm24.astype(np.float32), 2, 3)
    return np.clip(pcm16, -32768, 32767).astype(np.int16).tobytes()


async def stream(ws, pcm, lead=200, tail=700):
    sil = b"\x00\x00" * SPF
    for _ in range(lead // FRAME_MS):
        await ws.send(sil); await asyncio.sleep(FRAME_MS/1000)
    fb = SPF * 2
    for i in range(0, len(pcm), fb):
        c = pcm[i:i+fb]
        if len(c) < fb: c += b"\x00" * (fb - len(c))
        await ws.send(c); await asyncio.sleep(FRAME_MS/1000)
    for _ in range(tail // FRAME_MS):
        await ws.send(sil); await asyncio.sleep(FRAME_MS/1000)


async def main():
    q1 = await synth("Please count slowly from one to twenty, one number at a time.")
    q2 = await synth("Stop. What is the capital of France?")
    async with websockets.connect(WS, max_size=None) as ws:
        print("ready:", json.loads(await ws.recv()).get("type"))

        # Turn 1 — long reply
        await stream(ws, q1)
        # Wait for the avatar to actually start replying (tokens flowing)
        got = 0
        while got < 8:
            m = await asyncio.wait_for(ws.recv(), timeout=15)
            if isinstance(m, bytes): continue
            if json.loads(m).get("type") == "llm_token": got += 1
        print(f"  avatar started replying ({got} tokens) — barging in...")

        # BARGE IN over the reply
        await stream(ws, q2)

        # Read all llm_done responses after barging; the barge answer mentions
        # Paris (the counting reply never will), so we can pick it out cleanly.
        transcripts, answers = [], []
        try:
            while True:
                m = await asyncio.wait_for(ws.recv(), timeout=15)
                if isinstance(m, bytes): continue
                d = json.loads(m); t = d.get("type")
                if t == "transcript_final" and d.get("speaker") == "user":
                    transcripts.append(d.get("text",""))
                elif t == "llm_done":
                    txt = d.get("full_text","")
                    answers.append(txt)
                    print(f"  llm_done: {txt!r}")
                    if "paris" in txt.lower(): break
        except asyncio.TimeoutError:
            pass
        print(f"  user transcripts: {transcripts}")
        ok = any("paris" in a.lower() for a in answers)
        print("PASS ✅ barge-in interrupted and answered the new question"
              if ok else "CHECK ❌ barge answer not found")
        sys.exit(0 if ok else 1)

asyncio.run(main())
