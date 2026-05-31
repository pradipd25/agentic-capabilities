# Feature Tracker

Track implemented features and planned work.

**Status legend:**
- `[x]` Implemented & working
- `[ ]` Planned / to do
- `[~]` In progress

---

## Core Conversation

- [x] Voice input via microphone (Silero VAD + Whisper STT, fully local)
- [x] Text input via chat panel
- [x] Barge-in / interrupt — speak while avatar is talking, it stops and responds
- [x] Multi-turn conversation history maintained across the session
- [x] Streaming LLM token display — response appears word-by-word in chat panel
- [x] Text-to-speech (ElevenLabs preferred, OpenAI TTS fallback)
- [ ] Streaming STT — real-time transcription as user speaks (Deepgram / AssemblyAI)
- [ ] Noise cancellation / echo suppression on mic input
- [ ] Push-to-talk mode (hold button vs toggle)

---

## Avatar

- [x] 3D animated avatar rendered with Three.js / React Three Fiber
- [x] Animation states: Idle → Listening → Thinking → Talking
- [x] Avatar selector — pick from multiple characters in the UI
- [x] Mid-session avatar swap without disconnecting
- [x] Extendable avatar registry via `avatars/manifest.json`
- [ ] Lip-sync — drive mouth animation from live TTS audio level
- [ ] Custom Ready Player Me avatar import via URL
- [ ] Avatar emotion expressions (happy, surprised, thinking)
- [ ] Multiple camera angles / zoom controls

---

## VocalPalette (Voice Selection)

- [x] ⚙ Settings drawer — VocalPalette UI accessible from chat header
- [x] Browse voice cards with name, gender icon, and description
- [x] Live voice preview — hear sample clip before applying
- [x] ElevenLabs voices — full account library shown when API key is set
- [x] OpenAI TTS voices — all 9 voices (Alloy, Ash, Coral, Echo, Fable, Nova, Onyx, Sage, Shimmer)
- [x] Persistent selection — chosen voice saved in browser localStorage
- [x] Safe fallback — invalid stored voice auto-corrected on session start
- [ ] ElevenLabs Voice Cloning — clone any voice from a short recording
- [ ] ElevenLabs Voice Design — generate a new voice from a text description
- [ ] Voice parameter tuning — stability, similarity, style sliders (ElevenLabs)
- [ ] Custom ElevenLabs voice ID entry — paste any voice ID from your account

---

## LLM

- [x] Claude (Anthropic) — claude-sonnet-4-6 default
- [x] OpenAI — gpt-4o default
- [x] Google Gemini — gemini-2.0-flash default
- [x] Groq — llama-3.1-70b-versatile default
- [x] Ollama — local models, no API key needed
- [x] Model override via `LLM_MODEL` env var
- [x] Configurable system prompt via `SYSTEM_PROMPT` env var
- [ ] Per-session LLM override from the UI
- [ ] LLM provider selector in settings panel
- [ ] Conversation summarisation for long sessions (context window management)

---

## MCP Integration

- [x] MCP SSE server at `/mcp/sse` — plug into any MCP-compatible agent
- [x] `avatar.create_session` — reserve a session, returns join URL
- [x] `avatar.speak` — make the avatar say something via TTS
- [x] `avatar.get_transcript` — read conversation history
- [x] `avatar.set_avatar` — swap the 3D character
- [x] `avatar.inject_context` — add context to LLM system prompt
- [x] `avatar.list_avatars` — list available characters
- [x] `avatar.list_sessions` — list active sessions
- [x] `avatar.close_session` — end a session
- [ ] `avatar.set_voice` — change voice via MCP tool
- [ ] `avatar.set_animation` — trigger a specific animation from an agent
- [ ] `avatar.mute` / `avatar.unmute` — control audio from agent side

---

## UI / UX

- [x] Audio unlock banner — guides user to enable browser audio
- [x] Audio status indicator — shows chunks played, errors
- [x] Connection status dot — green (connected) / yellow (reconnecting)
- [x] Scrollable chat transcript with user / assistant bubbles
- [x] Streaming token indicator with blinking cursor
- [x] Mic button with pulse animation while capturing
- [ ] Audio level visualiser / waveform on mic input
- [ ] Dark / light theme toggle
- [ ] Mobile responsive layout
- [ ] Keyboard shortcuts (e.g. Space to toggle mic, Enter to send)
- [ ] Notification sound when avatar starts speaking

---

## Developer Experience

- [x] `./start.sh` — one-command startup, installs deps, starts both servers
- [x] Port conflict handling — frees ports 8100 / 5173 automatically before starting
- [x] Backend hot reload on file changes
- [x] Frontend Vite HMR
- [x] `GET /api/health` — health check with active LLM provider
- [x] `.env.example` — documented template for all config options
- [x] `.gitignore` — excludes `.env`, `node_modules`, `.venv`, build artefacts
- [ ] Docker Compose — single `docker compose up` to run everything
- [ ] Automated end-to-end tests (pytest + Playwright)
- [ ] CI pipeline (GitHub Actions)

---

## Backlog (Unscheduled Ideas)

- [ ] Session recording — save transcript + audio to file
- [ ] Webhook support — notify external systems on turn events
- [ ] i18n / multilingual support (STT + TTS in multiple languages)

---

*Last updated: 2026-05-31*
