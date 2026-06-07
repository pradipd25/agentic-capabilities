# Agentic Capabilities — Agent Face Framework

**Give any agent a face.** A reusable presence layer — a 3D avatar with voice,
barge-in, and real-time animation — that any **agentic IDE**, **agentic
application**, or **LLM application** can drive. Built on
[Pipecat](https://github.com/pipecat-ai/pipecat); the app in this repo is the
**reference implementation** of the framework.

The piece that makes it *any-agent* is a transport-agnostic **Presence Protocol**
that decouples *where the agent runs* (an **adapter**) from *the face that
represents it* (the **renderer**):

```
 agent source ──adapter──▶ [ Presence Protocol ] ──▶ renderer (the face)
   Claude Agent SDK            speak / think            3D avatar + voice
   MCP agent / IDE             action / ask             TTS + STT + barge-in
   OpenAI / raw stream         status / done            chat + action chips
```

The protocol is **bidirectional**: downstream `PresenceEvent`s (agent → face) and
upstream `ControlMessage`s (face → agent: user turn, interrupt, ask-response).

> **Build status:** Presence Protocol, renderer integration, the Claude Agent SDK
> adapter (core), and the MCP server surface are implemented and unit-tested
> (40 tests). See [`FEATURES.md`](./FEATURES.md) for the per-phase tracker; what's
> next is the embeddable `<agent-face>` web component and headless Python/TS SDKs.

---

## Framework Architecture

| Layer | What it is | Where |
|---|---|---|
| **Presence Protocol** | Versioned event schema (TS + Python) + conformance suite — the contract | `packages/presence-protocol/` |
| **Adapters (in)** | Translate an agent source into the protocol. `Adapter` SPI + `ClaudeAgentAdapter` (embeds Claude Code's loop) | `packages/adapters/python/` |
| **MCP surface (push)** | Lets any MCP agent/IDE drive the face: `avatar.show_action` / `ask` / `set_status` / `set_voice` | `backend/mcp_server/` |
| **Renderer (out)** | The 3D avatar + voice runtime that consumes the protocol | `frontend/src/` |

Two integration directions, both supported:

- **Embed** — the framework runs the agent loop (e.g. the Claude Agent SDK adapter)
  and streams its output to the face.
- **Push** — an external agent/IDE (Claude Code, Cursor, …) connects over MCP and
  drives the face with zero code.

---

## Features

### Conversation

| Feature | Details |
|---|---|
| **Voice input (mic)** | Speak naturally — Silero VAD detects when you start and stop; Whisper STT transcribes locally (no API key needed) |
| **Text input** | Type a message and press Enter or click Send |
| **Barge-in / interrupt** | Speak while the avatar is talking — it stops mid-sentence and responds to you |
| **Conversation history** | Full multi-turn context maintained across the session |
| **Streaming LLM response** | Tokens stream into the chat panel in real time as the LLM generates them |

### Avatar

| Feature | Details |
|---|---|
| **3D animated avatar** | WebGL avatar rendered with Three.js / React Three Fiber |
| **Animation states** | Idle → Listening → Thinking → Talking, driven by the conversation pipeline |
| **Avatar selector** | Pick from multiple characters in the UI; each has its own 3D model |
| **Swappable mid-session** | Change avatar during a live conversation without disconnecting |
| **Extendable** | Add new avatars by dropping a GLB file and editing `avatars/manifest.json` |

### VocalPalette — Voice Texture Selection

| Feature | Details |
|---|---|
| **Voice picker** | ⚙ settings icon opens the VocalPalette drawer — choose from all 9 OpenAI TTS voices |
| **Live preview** | Click ▶ on any voice card to hear a sample clip before applying |
| **Persistent selection** | Chosen voice saved in browser `localStorage` — remembered across page reloads |
| **Safe fallback** | If a stored voice ID becomes invalid, the backend automatically falls back to the avatar's default voice and corrects `localStorage` |

### Text-to-Speech

| Feature | Details |
|---|---|
| **OpenAI TTS** | 9 built-in voices (Alloy, Ash, Coral, Echo, Fable, Nova, Onyx, Sage, Shimmer) via the `tts-1` model |

### LLM

| Feature | Details |
|---|---|
| **Multi-provider** | Claude, OpenAI, Gemini, Groq, or Ollama — switch with one env var |
| **Configurable model** | Override the default model per provider via `LLM_MODEL` |
| **System prompt** | Customise the assistant's persona via `SYSTEM_PROMPT` in `.env` |

### MCP Integration

| Feature | Details |
|---|---|
| **MCP server** | Exposes `avatar.*` tools via SSE at `/mcp/sse` |
| **Agent-driven avatar** | Any MCP-compatible agent (Claude Code, LangGraph, etc.) can make the avatar speak, swap characters, read the transcript, and more |
| **One-line setup** | Add a single entry to `.mcp.json` to give any agent a face and voice |

### Developer Experience

| Feature | Details |
|---|---|
| **One-command startup** | `./start.sh` — installs deps, frees ports if in use, starts both servers |
| **Port conflict handling** | `start.sh` gracefully kills any process on ports 8100 / 5173 before starting |
| **Hot reload** | Backend restarts on Python file changes; frontend uses Vite HMR |
| **Health endpoint** | `GET /api/health` reports server status and active LLM provider |

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+

### 1. Clone & configure

```bash
cp .env.example .env
# Edit .env — set LLM_PROVIDER and the matching API key
```

### 2. Start everything

```bash
./start.sh
```

| Service | URL |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8100 |
| MCP SSE | http://localhost:8100/mcp/sse |

### 3. Manual start (alternative)

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn backend.main:app --port 8100 --reload

# Frontend (separate terminal)
cd frontend && npm install && npm run dev
```

---

## Repository Layout

```
packages/
  presence-protocol/        # the contract: versioned schema + TS & Python types + tests
    typescript/index.ts
    python/presence_protocol/
  adapters/python/          # agent_face_adapters: Adapter SPI + ClaudeAgentAdapter
backend/                    # FastAPI + Pipecat reference server
  mcp_server/               # MCP surface incl. presence bridge (show_action/ask/...)
  processors/               # pipeline processors (avatar_state, text_input, ...)
frontend/                   # React + Three.js renderer (the face)
```

## Agent Backend — embed Claude Code (Phase 2b)

By default the reference app answers with a single LLM completion. Set
`AGENT_BACKEND=claude_code` to instead **embed Claude Code's agent loop** via the
Claude Agent SDK — the avatar becomes a voice/3D front-end for an agent that reads
files, edits code, and runs commands, narrating its work as action chips:

```bash
pip install -e ".[agent]"        # installs claude-agent-sdk (pulls a native binary)
export ANTHROPIC_API_KEY=sk-...

# in .env:
AGENT_BACKEND=claude_code
# AGENT_ALLOWED_TOOLS=             # empty = read-only (Read,Glob,Grep,WebSearch,WebFetch)
# AGENT_ALLOWED_TOOLS=Read,Edit,Bash   # opt in to edits / shell
# AGENT_ALLOWED_TOOLS=*            # no restriction (full default toolset)
# AGENT_PERMISSION_MODE=default
```

**Tool policy (enforced).** With the read-only default the side-effecting tools
(`Bash`, `Edit`, `Write`, `NotebookEdit`) are **blocked** via the SDK's
`disallowed_tools` — verified: a blocked `Edit` leaves the file untouched even if
the model spawns a subagent to retry. The agent can still *read* files (including
`.git`), which is what read-only means. List tools in `AGENT_ALLOWED_TOOLS` to opt
each one back in, or `*` to lift the restriction entirely. (Note: the SDK's
`can_use_tool` callback is *not* consulted in this non-interactive streaming mode,
and `allowed_tools` only auto-approves — it does not restrict — so `disallowed_tools`
is the gate that actually enforces this.)

STT (voice in) and TTS (voice out) are unchanged; conversational text is spoken,
while tool steps appear as `action` chips (never spoken). When you opt into edits,
the agent edits files in the backend's working directory — run it locally pointed
at your repo.

## Framework Tests

The protocol, adapters, MCP bridge, and agent routing are unit-tested with no API
key or native SDK required:

```bash
# Python: protocol conformance + Claude mapper + MCP bridge + Python SDK + agent routing
PYTHONPATH="packages/presence-protocol/python:packages/adapters/python:packages/sdk-py:." \
  python3 -m pytest packages backend/mcp_server/tests backend/processors/tests -q

# Frontend: typecheck + build
cd frontend && npx tsc --noEmit && npx vite build
```

---

## LLM Configuration

Set `LLM_PROVIDER` in `.env`:

| Provider | Key | Default model |
|---|---|---|
| `claude` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-6` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o` |
| `gemini` | `GOOGLE_API_KEY` | `gemini-2.0-flash` |
| `groq` | `GROQ_API_KEY` | `llama-3.1-70b-versatile` |
| `ollama` | *(none — local)* | `llama3` |

Override the model: `LLM_MODEL=claude-opus-4-8`

---

## VocalPalette — Choosing a Voice

1. Open the app at http://localhost:5173
2. Click the **⚙** icon (top-right of the chat panel)
3. Browse voice cards — click **▶ Preview** to hear any voice before selecting
4. Click a voice to select it, then **Apply Voice**
5. The session reconnects with the new voice — your selection is saved for next time

> VocalPalette offers the 9 built-in OpenAI TTS voices.

---

## MCP Integration

Add to your agent's `.mcp.json`:

```json
{
  "mcpServers": {
    "video-capability": {
      "url": "http://localhost:8100/mcp/sse"
    }
  }
}
```

Available tools:

| Tool | Description |
|---|---|
| `avatar.create_session` | Create a session, returns a `join_url` for the user |
| `avatar.speak` | Make the avatar say something via TTS |
| `avatar.show_action` | Show a tool/step as an action chip (shown, never spoken) — e.g. `Read app.py` |
| `avatar.ask` | Ask the user a clarify/approve question **and wait** for their answer |
| `avatar.set_status` | Show a transient progress/heartbeat line (keeps the avatar alive during long work) |
| `avatar.set_voice` | Change the avatar's voice |
| `avatar.set_animation` | Trigger a named animation (idle/talking/thinking/greeting) |
| `avatar.get_transcript` | Read the full conversation history |
| `avatar.set_avatar` | Swap the 3D character |
| `avatar.inject_context` | Add context to the LLM system prompt |
| `avatar.list_avatars` | List available characters |
| `avatar.list_sessions` | List active sessions |
| `avatar.close_session` | End a session |

The `show_action` / `ask` / `set_status` tools map to Presence Protocol events the
renderer already understands — so an agent like Claude Code can narrate its work
(action chips) and request approvals through the avatar. See
[`packages/presence-protocol/README.md`](./packages/presence-protocol/README.md)
for the full event schema.

---

## Adding Avatars

1. Create `avatars/models/{id}/` containing:
   - `avatar.glb` — 3D model with animations (idle, talking, thinking, greeting clips)
   - `thumbnail.png` — picker thumbnail (optional)

2. Add an entry to `avatars/manifest.json` with `id`, `name`, `voice_id`, and animation URLs

3. Restart the backend — no code changes needed

---

## API Reference

| Endpoint | Description |
|---|---|
| `GET /api/health` | Server status + active LLM provider |
| `GET /api/avatars` | List available avatars |
| `GET /api/voices` | List available voices for the active TTS provider |
| `GET /api/voices/{id}/preview` | Generate and return a WAV sample for a voice |
| `GET /api/sessions` | List active sessions |
| `WS /ws/{session_id}?voice_id=` | Pipecat conversation pipeline (optional voice override) |
| `GET /mcp/sse` | MCP SSE endpoint |
| `POST /mcp/messages` | MCP message handler |

---

## Environment Variables

```env
# LLM
LLM_PROVIDER=openai            # claude | openai | gemini | groq | ollama
LLM_MODEL=                     # optional model override

# Agent backend
AGENT_BACKEND=pipeline         # pipeline (single LLM) | claude_code (Claude Agent SDK)
AGENT_ALLOWED_TOOLS=           # empty = read-only; e.g. Read,Edit,Bash to enable changes
AGENT_PERMISSION_MODE=default

# API Keys
ANTHROPIC_API_KEY=
OPENAI_API_KEY=               # always required — powers TTS regardless of LLM_PROVIDER
GOOGLE_API_KEY=
GROQ_API_KEY=

# Optional
SYSTEM_PROMPT=                 # custom assistant persona
DEFAULT_AVATAR=aria            # avatar shown on first load
OLLAMA_BASE_URL=http://localhost:11434
```
