"""
Reproduces the interruption bug: send a long question, interrupt mid-response
with a text follow-up, and verify (a) the follow-up is answered coherently
instead of the model continuing the first response, and (b) the pipeline keeps
responding on later turns.

Run the server first:  uvicorn backend.main:app --port 8100
Then:                  python test_interruption.py
"""
import asyncio
import json
import sys

import websockets

WS = "ws://localhost:8100/ws/interrupt-test?voice_id=nova"


async def collect_tokens(ws, idle_timeout=8.0):
    """Read until avatar goes idle (turn complete) or we time out on silence."""
    tokens = []
    audio_bytes = 0
    while True:
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=idle_timeout)
        except asyncio.TimeoutError:
            break
        if isinstance(msg, bytes):
            audio_bytes += len(msg)
            continue
        data = json.loads(msg)
        t = data.get("type")
        if t == "llm_token":
            tokens.append(data.get("token", ""))
        elif t == "avatar_state" and data.get("animation") == "idle":
            # turn finished
            if tokens:
                break
    return "".join(tokens), audio_bytes


async def main():
    async with websockets.connect(WS, max_size=None) as ws:
        # session_ready handshake
        ready = json.loads(await ws.recv())
        print(f"[handshake] {ready.get('type')} voice={ready.get('voice_id')}")

        # Turn 1 — long question
        print("\n[turn 1] sending long question...")
        await ws.send(json.dumps({
            "type": "text_input",
            "text": "Explain what Python is and list 5 key features in detail.",
            "session_id": "interrupt-test",
        }))

        # Let a few tokens stream, then INTERRUPT with a follow-up
        first_tokens = []
        while len("".join(first_tokens)) < 40:
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            if isinstance(msg, bytes):
                continue
            d = json.loads(msg)
            if d.get("type") == "llm_token":
                first_tokens.append(d["token"])
        print(f"[turn 1] got partial: {''.join(first_tokens)[:60]!r} — interrupting now")

        # Turn 2 — follow-up while bot is mid-response
        await ws.send(json.dumps({
            "type": "text_input",
            "text": "What is the very first feature you mentioned? Answer in one short sentence.",
            "session_id": "interrupt-test",
        }))
        answer2, audio2 = await collect_tokens(ws)
        print(f"[turn 2] answer ({audio2}B audio): {answer2!r}")

        # Turn 3 — confirm pipeline still alive
        print("\n[turn 3] sending 'Are you still there?'...")
        await ws.send(json.dumps({
            "type": "text_input",
            "text": "Are you still there? Reply with a short yes.",
            "session_id": "interrupt-test",
        }))
        answer3, audio3 = await collect_tokens(ws)
        print(f"[turn 3] answer ({audio3}B audio): {answer3!r}")

        # ── Assertions ──
        ok = True
        if not answer2.strip():
            print("FAIL: turn 2 produced no answer"); ok = False
        if not answer3.strip():
            print("FAIL: turn 3 produced no answer (pipeline wedged)"); ok = False
        # crude language drift check: the follow-ups were English; a Spanish
        # continuation would contain these common tokens
        spanish_markers = (" características", " ideal", " tanto", " desarrolladores", "Aquí")
        if any(m in answer2 for m in spanish_markers):
            print("FAIL: turn 2 looks like a Spanish continuation of turn 1"); ok = False

        print("\n" + ("PASS ✅ interruption handled cleanly" if ok else "FAIL ❌"))
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
