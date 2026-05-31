# Agentic Capabilities — Avatar Conversation Framework

A plug-and-play video/avatar conversation capability for AI agents. Built on [Pipecat](https://github.com/pipecat-ai/pipecat), exposing avatar conversations as MCP tools so any compatible agent can acquire a face and a voice with a single config line.

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
| **Voice picker** | ⚙ settings icon opens the VocalPalette drawer — choose from your full ElevenLabs voice library or all 9 OpenAI TTS voices |
| **Live preview** | Click ▶ on any voice card to hear a sample clip before applying |
| **Provider-aware** | Automatically shows ElevenLabs voices when an ElevenLabs API key is set, OpenAI voices otherwise |
| **Persistent selection** | Chosen voice saved in browser `localStorage` — remembered across page reloads |
| **Safe fallback** | If a stored voice ID becomes invalid (e.g. switching TTS providers), the backend automatically falls back to the avatar's default voice and corrects `localStorage` |

### Text-to-Speech

| Feature | Details |
|---|---|
| **ElevenLabs** (preferred) | High-quality, realistic voices; uses your ElevenLabs account's voice library |
| **OpenAI TTS** (fallback) | 9 built-in voices (Alloy, Ash, Coral, Echo, Fable, Nova, Onyx, Sage, Shimmer) — used when no ElevenLabs key is set |

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

> With an `ELEVENLABS_API_KEY` set, VocalPalette shows your full ElevenLabs voice library.
> Without it, the 9 built-in OpenAI TTS voices are shown.

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
| `avatar.get_transcript` | Read the full conversation history |
| `avatar.set_avatar` | Swap the 3D character |
| `avatar.inject_context` | Add context to the LLM system prompt |
| `avatar.list_avatars` | List available characters |
| `avatar.list_sessions` | List active sessions |
| `avatar.close_session` | End a session |

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

# API Keys
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
GROQ_API_KEY=
ELEVENLABS_API_KEY=            # if set, ElevenLabs is used for TTS

# Optional
SYSTEM_PROMPT=                 # custom assistant persona
DEFAULT_AVATAR=aria            # avatar shown on first load
OLLAMA_BASE_URL=http://localhost:11434
```
