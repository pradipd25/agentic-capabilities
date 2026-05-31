# Agentic Capabilities — Avatar Conversation Framework

A plug-and-play video/avatar conversation capability for AI agents. Built on [Pipecat](https://github.com/pipecat-ai/pipecat), exposing avatar conversations as MCP tools so any agent can acquire a face and a voice with a single config line.

## What it does

- **Live avatar conversation UI** — animated 3D character the user talks to
- **Voice + text input** — speak or type; voice is transcribed locally via Whisper
- **Configurable LLM** — Claude, OpenAI, Gemini, Groq, or Ollama via one env var
- **MCP server** — any MCP-compatible agent (Claude Code, LangGraph, etc.) can drive the avatar programmatically

---

## Quick Start (Local)

### 1. Prerequisites
- Python 3.11+
- Node.js 18+

### 2. Clone & configure

```bash
cp .env.example .env
# Edit .env — set LLM_PROVIDER and the matching API key
```

### 3. Start everything

```bash
./start.sh
```

Opens:
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8100
- **MCP SSE endpoint:** http://localhost:8100/mcp/sse

### 4. Manual start (alternative)

**Backend:**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn backend.main:app --port 8100 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## LLM Configuration

Set in `.env`:

| `LLM_PROVIDER` | Required key | Default model |
|---|---|---|
| `claude` | `ANTHROPIC_API_KEY` | `claude-sonnet-4-5` |
| `openai` | `OPENAI_API_KEY` | `gpt-4o` |
| `gemini` | `GOOGLE_API_KEY` | `gemini-2.0-flash` |
| `groq` | `GROQ_API_KEY` | `llama-3.1-70b-versatile` |
| `ollama` | *(none)* | `llama3` |

Override the model: `LLM_MODEL=claude-opus-4-8`

---

## Integrating an Agent via MCP

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

Your agent now has these tools:

| Tool | Description |
|---|---|
| `avatar.create_session` | Create a session, get a `join_url` for the user |
| `avatar.speak` | Make the avatar say something |
| `avatar.get_transcript` | Read the conversation history |
| `avatar.set_avatar` | Swap the character |
| `avatar.inject_context` | Add context to the LLM system prompt |
| `avatar.list_avatars` | List available characters |
| `avatar.list_sessions` | List active sessions |
| `avatar.close_session` | End a session |

---

## Adding Avatars

1. Drop a folder in `avatars/models/{your-avatar-id}/` with:
   - `avatar.glb` — the 3D model
   - `idle.glb`, `talking.glb`, `thinking.glb`, `greeting.glb` — animation clips
   - `thumbnail.png` — picker thumbnail

2. Add an entry to `avatars/manifest.json`

3. Restart the backend — no code changes needed.

---

## API

| Endpoint | Description |
|---|---|
| `GET /api/health` | Server health + current LLM provider |
| `GET /api/avatars` | List available avatars |
| `GET /api/sessions` | List active sessions |
| `WS /ws/{session_id}` | Pipecat conversation pipeline |
| `GET /mcp/sse` | MCP SSE endpoint for agents |
| `POST /mcp/messages` | MCP message endpoint |