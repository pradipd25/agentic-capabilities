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
- [x] Text-to-speech (OpenAI TTS)
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
- [ ] Ready Player Me (RPM) — paste any `models.readyplayer.me/*.glb` URL to load a personalised avatar instantly
- [ ] RPM iframe creator — embedded avatar builder so users can create/customise an RPM avatar without leaving the app
- [ ] RPM animation pack — shared idle/talking/thinking/greeting clips that work across all RPM avatars (no per-model animation setup)
- [ ] RPM avatar as default — set `RPM_AVATAR_URL=` in `.env` to use a personal RPM avatar as the startup avatar
- [ ] Avatar emotion expressions (happy, surprised, thinking)
- [ ] Multiple camera angles / zoom controls

---

## VocalPalette (Voice Selection)

- [x] ⚙ Settings drawer — VocalPalette UI accessible from chat header
- [x] Browse voice cards with name, gender icon, and description
- [x] Live voice preview — hear sample clip before applying
- [x] OpenAI TTS voices — all 9 voices (Alloy, Ash, Coral, Echo, Fable, Nova, Onyx, Sage, Shimmer)
- [x] Persistent selection — chosen voice saved in browser localStorage
- [x] Safe fallback — invalid stored voice auto-corrected on session start
- [ ] Voice speed control in the UI — adjust TTS pace from the drawer

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
- [x] `avatar.set_voice` — change voice via MCP tool (emits `voice_changed`)
- [x] `avatar.show_action` — render an action chip (tool/step) on the avatar
- [x] `avatar.ask` — ask the user a clarify/approve question and await the answer
- [x] `avatar.set_status` — show a transient progress/heartbeat line
- [x] `avatar.set_animation` — trigger a specific animation from an agent
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

## Framework: Presence Protocol & Adapters

Evolve this app into a reusable "give any agent a face" framework. The current
app becomes the reference implementation. See the full plan in
`~/.claude/plans/what-is-the-mechanism-shimmying-quill.md`.

**Build progress (55 unit tests passing; frontend `tsc` + `vite build` clean):**

| Phase | Status | What landed |
|---|---|---|
| 0 — Presence Protocol | ✅ done | `packages/presence-protocol/` — spec + TS + Python types + 24 conformance tests |
| 1 — Renderer consumes protocol | ✅ done | action chips / status / ask-prompt in `conversationStore`, `useWebSocket`, `ChatPanel`, `App` (back-compatible) |
| 2 — Adapter SPI + Claude adapter | ✅ core | `agent_face_adapters` SPI + `ClaudeAgentAdapter` + pure `map_sdk_message` (9 tests) |
| 2b — Claude adapter → backend | ✅ live | `AGENT_BACKEND=claude_code` swaps in `ClaudeAgentProcessor`; E2E-verified locally (action chips + spoken summary + TTS audio). Read-only tool sandbox enforced via `disallowed_tools`. Reuses logged-in `claude` CLI auth |
| 3 — MCP server surface | ✅ done | `mcp_server/presence.py` bridge + `show_action`/`ask`/`set_status`/`set_voice` tools (7 tests) |
| 4 — web component + headless SDKs | ✅ done | `<agent-face>` web component + `@agent-face/sdk` (TS) + `agent_face_sdk` (Py, 5 tests) |
| 5 — OpenAI / raw-stream adapters | ⬜ todo | validate protocol on non-Claude sources |

> Note: this dev environment lacks `mcp` + `pipecat` + the Claude SDK, so the live
> server isn't bootable here — pure logic is unit-tested and backend files are
> `py_compile`-clean. Full E2E needs `pip install -e .`.

- [x] Presence Protocol — versioned event schema (`speak_delta`, `think`, `action`, `ask`, `status`, `done`), `packages/presence-protocol` (TS + Python)
- [x] Bidirectional contract — downstream presence events + upstream user turn / interrupt / ask-response
- [x] Protocol conformance test suite (Python pytest, 24 cases)
- [x] Adapter SPI — single interface any agent source implements (`agent_face_adapters.base.Adapter`)
- [x] Claude Agent SDK adapter — `map_sdk_message` + `ClaudeAgentAdapter` + backend `ClaudeAgentProcessor` (`AGENT_BACKEND=claude_code`); routing unit-tested
- [ ] Generic MCP adapter — push from any MCP agent / agentic IDE
- [ ] OpenAI / Responses adapter
- [ ] Raw stream / LangChain adapter

---

## Framework: Renderer & Surfaces

- [~] Renderer extracted as a standalone reusable lib (made protocol-aware in place; package extraction pending)
- [x] Action chips in chat panel — render tool activity (speech-vs-action split), plus think/status/ask handling
- [ ] Optional diff / file view alongside the face
- [x] MCP server surface — `show_action` / `ask` (round-trip) / `set_status` / `set_voice` added; bridge unit-tested
- [x] Embeddable web component `<agent-face>` (`packages/agent-face-web`, shadow DOM, TTS playback, action chips / ask)
- [x] Headless SDK — Python (`packages/sdk-py` — `PresenceSender` + `drive_adapter`, 5 tests)
- [x] Headless SDK — TypeScript (`packages/sdk-ts` — `AgentFaceClient`, typechecked)
- [ ] Desktop / IDE overlay (later phase)

---

## Framework: Distribution & Launch (Planned)

- [ ] Monorepo split — `packages/*` (protocol, renderer, adapters, sdk) + `apps/reference`
- [ ] Open-core, local-first distribution
- [ ] Publish to npm + PyPI
- [ ] MCP plugin marketplace listing (launch wedge)
- [ ] 5-minute quickstart + reference-app demo video
- [ ] Versioned protocol with a 1.0 compatibility guarantee
- [ ] Branding compliance — "Powered by Claude" (not "Claude Code")

---

## Backlog (Unscheduled Ideas)

- [ ] Session recording — save transcript + audio to file
- [ ] Webhook support — notify external systems on turn events
- [ ] i18n / multilingual support (STT + TTS in multiple languages)

---

*Last updated: 2026-06-07*
