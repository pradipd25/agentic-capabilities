"""Send one long question (no interruption, no mic) and verify the backend
streams audio all the way to the end of the response."""
import asyncio, json, sys, time, websockets

WS = "ws://localhost:8100/ws/long-test?voice_id=nova"

async def main():
    async with websockets.connect(WS, max_size=None) as ws:
        print("ready:", json.loads(await ws.recv()).get("type"))
        await ws.send(json.dumps({
            "type": "text_input",
            "session_id": "long-test",
            "text": "Write a detailed 8-sentence paragraph about the history of the Internet.",
        }))
        toks, audio, last_audio_t = [], 0, None
        done_text = None
        t0 = time.time()
        interruptions = []
        while time.time() - t0 < 60:
            try:
                m = await asyncio.wait_for(ws.recv(), timeout=12)
            except asyncio.TimeoutError:
                break
            if isinstance(m, bytes):
                audio += len(m); last_audio_t = time.time() - t0; continue
            d = json.loads(m); t = d.get("type")
            if t == "llm_token":
                toks.append(d["token"])
            elif t == "llm_done":
                done_text = d.get("full_text", "")
                print(f"  llm_done @ {time.time()-t0:.1f}s, {len(done_text)} chars")
            elif t == "avatar_state":
                anim = d.get("animation")
                if anim == "listening":
                    interruptions.append(time.time() - t0)
                if anim == "idle" and done_text is not None and last_audio_t and time.time()-t0 - last_audio_t > 1:
                    break
        # estimate spoken seconds: 16kHz mono s16le → 32000 bytes/sec
        spoken_s = audio / 32000
        print(f"  reply chars: {len(done_text or '')}")
        print(f"  audio: {audio}B  (~{spoken_s:.1f}s of speech), last chunk @ {last_audio_t}s")
        print(f"  false-interruption(listening) events: {interruptions}")
        # rough check: ~12 chars/sec speech; full 8-sentence para should be >>10s audio
        ok = spoken_s > 10 and not interruptions
        print("PASS ✅ full audio, no interruption" if ok else "CHECK ❌ audio short or interrupted")
        sys.exit(0 if ok else 1)

asyncio.run(main())
