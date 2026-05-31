import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from mcp.server.sse import SseServerTransport

from backend.avatar.registry import AvatarRegistry
from backend.config import settings
from backend.llm.factory import create_llm_service
from backend.mcp_server.tools import mcp_server
from backend.processors.avatar_state import AvatarStateProcessor
from backend.processors.text_input import TextInputProcessor
from backend.serializers import RawAudioSerializer
from backend.session.manager import SessionManager

log = structlog.get_logger()

# Project root is one level up from this file's directory
_PROJECT_ROOT = Path(__file__).parent.parent

# Shared state injected into MCP tools via lifespan context
_session_manager = SessionManager()
_avatar_registry = AvatarRegistry(_PROJECT_ROOT / "avatars" / "manifest.json")
_websockets: dict[str, WebSocket] = {}   # session_id → active WebSocket
_contexts: dict = {}                      # session_id → OpenAILLMContext


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Wire shared deps into the MCP server so tools can access them
    mcp_server._lifespan_context = {
        "session_manager": _session_manager,
        "avatar_registry": _avatar_registry,
        "websockets": _websockets,
        "contexts": _contexts,
        "config": settings,
        "host": settings.host if settings.host != "0.0.0.0" else "localhost",
    }
    log.info("server.started", provider=settings.llm_provider, port=settings.port)
    yield
    log.info("server.stopped")


app = FastAPI(title="Agentic Capabilities — Video", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve avatar GLB models and thumbnails
app.mount("/static/avatars", StaticFiles(directory=str(_PROJECT_ROOT / "avatars" / "models")), name="avatar-static")


# ── REST endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health():
    return {"status": "ok", "provider": settings.llm_provider}


@app.get("/api/avatars")
async def get_avatars():
    return {"avatars": [a.model_dump() for a in _avatar_registry.list_avatars()]}


@app.get("/api/sessions")
async def get_sessions():
    return {"sessions": _session_manager.list_sessions()}


# ── WebSocket conversation endpoint ───────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    _websockets[session_id] = websocket

    # Resolve session info — may have been pre-created via MCP avatar.create_session
    info = _session_manager.get(session_id)
    if info is None:
        # Auto-create a session with defaults if connected directly
        info = await _session_manager.create(
            session_id=session_id,
            avatar_id=settings.default_avatar,
            system_prompt=settings.system_prompt,
            llm_provider=settings.llm_provider.value,
            llm_model=settings.llm_model,
        )

    avatar = _avatar_registry.get_avatar(info.avatar_id) or _avatar_registry.list_avatars()[0]

    log.info("session.connected", session_id=session_id, avatar=avatar.id)

    try:
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.frames.frames import TextFrame
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.processors.aggregators.llm_context import LLMContext
        from pipecat.processors.aggregators.llm_response_universal import (
            LLMAssistantAggregator,
            LLMUserAggregator,
        )
        from pipecat.processors.audio.vad_processor import VADProcessor
        from pipecat.transports.websocket.fastapi import (
            FastAPIWebsocketParams,
            FastAPIWebsocketTransport,
        )

        # Send session_ready before the Pipecat transport takes over
        await websocket.send_text(json.dumps({
            "type": "session_ready",
            "session_id": session_id,
            "avatar": avatar.model_dump(),
            "available_avatars": [a.model_dump() for a in _avatar_registry.list_avatars()],
        }))

        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                audio_in_passthrough=True,   # required: pushes audio frames into the pipeline
                add_wav_header=True,
                serializer=RawAudioSerializer(),
            ),
        )

        llm = create_llm_service(settings)

        # Build context with system prompt as first message
        context = LLMContext()
        if info.system_prompt:
            context.add_message({"role": "system", "content": info.system_prompt})
        _contexts[session_id] = context

        user_aggregator = LLMUserAggregator(context)
        assistant_aggregator = LLMAssistantAggregator(context)
        text_input_processor = TextInputProcessor(context, websocket, _avatar_registry)

        # TTS — ElevenLabs if key present, else OpenAI TTS fallback
        if settings.elevenlabs_api_key and settings.elevenlabs_api_key != "...":
            from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
            tts = ElevenLabsTTSService(
                api_key=settings.elevenlabs_api_key,
                voice_id=avatar.voice_id,
            )
        else:
            from pipecat.services.openai.tts import OpenAITTSService
            tts = OpenAITTSService(
                api_key=settings.openai_api_key,
                voice="nova",
            )

        # STT — Whisper (local, no API key needed)
        from pipecat.services.whisper.stt import WhisperSTTService
        stt = WhisperSTTService(model="base", device="cpu")

        avatar_processor = AvatarStateProcessor(session_id, websocket)

        # VADProcessor must be explicit in Pipecat 1.3 — the transport's
        # vad_analyzer param is not used for WebSocket transports.
        vad_processor = VADProcessor(vad_analyzer=SileroVADAnalyzer())

        pipeline = Pipeline([
            transport.input(),
            text_input_processor,   # converts text_input JSON → LLMContextFrame
            vad_processor,          # runs Silero VAD, emits VADUserStarted/StoppedSpeakingFrame
            stt,                    # WhisperSTT: accumulates audio, transcribes on VAD stop
            user_aggregator,        # collects transcription, triggers LLM
            llm,
            avatar_processor,       # sees raw LLM TextFrames (before TTS aggregates them)
            tts,                    # BotStarted/StoppedSpeakingFrame pushed upstream to avatar_processor
            assistant_aggregator,
            transport.output(),
        ])

        task = PipelineTask(
            pipeline,
            enable_rtvi=False,
            params=PipelineParams(allow_interruptions=True),
        )
        await _session_manager.register_task(session_id, task)

        runner = PipelineRunner(handle_sigint=False)
        await runner.run(task)

    except WebSocketDisconnect:
        log.info("session.disconnected", session_id=session_id)
    except Exception as e:
        log.error("session.error", session_id=session_id, error=str(e))
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except Exception:
            pass
    finally:
        _websockets.pop(session_id, None)
        _contexts.pop(session_id, None)
        await _session_manager.remove(session_id)
        log.info("session.cleaned_up", session_id=session_id)


# ── MCP server (SSE transport) ─────────────────────────────────────────────────

sse_transport = SseServerTransport("/mcp/messages")


@app.get("/mcp/sse")
async def mcp_sse_endpoint(request):
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        # Inject lifespan context so tools can access shared state
        mcp_server.request_context = type("ctx", (), {
            "lifespan_context": mcp_server._lifespan_context
        })()
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )


@app.post("/mcp/messages")
async def mcp_messages_endpoint(request):
    return await sse_transport.handle_post_message(
        request.scope, request.receive, request._send
    )
