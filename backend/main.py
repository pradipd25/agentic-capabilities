import json
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from mcp.server.sse import SseServerTransport

from backend.avatar.registry import AvatarRegistry
from backend.config import settings
from backend.llm.factory import create_llm_service
from backend.mcp_server.tools import mcp_server
from backend.mcp_server.presence import AskRegistry
from backend.processors.avatar_state import AvatarStateProcessor
from backend.processors.context_sanitizer import ContextSanitizerProcessor
from backend.processors.text_input import TextInputProcessor
from backend.serializers import RawAudioSerializer
from backend.session.manager import SessionManager
from backend.voice_registry import OPENAI_VOICES, PREVIEW_PHRASE, is_valid_openai_voice

log = structlog.get_logger()

_PROJECT_ROOT = Path(__file__).parent.parent

_session_manager = SessionManager()
_avatar_registry = AvatarRegistry(_PROJECT_ROOT / "avatars" / "manifest.json")
_websockets: dict[str, WebSocket] = {}
_contexts: dict = {}
_voice_preview_cache: dict[str, bytes] = {}
_ask_registry = AskRegistry()


@asynccontextmanager
async def lifespan(app: FastAPI):
    mcp_server._lifespan_context = {
        "session_manager": _session_manager,
        "avatar_registry": _avatar_registry,
        "websockets": _websockets,
        "contexts": _contexts,
        "config": settings,
        "host": settings.host if settings.host != "0.0.0.0" else "localhost",
        "ask_registry": _ask_registry,
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


@app.get("/api/voices")
async def get_voices():
    return {"voices": OPENAI_VOICES, "provider": "openai"}


@app.get("/api/voices/{voice_id}/preview")
async def get_voice_preview(voice_id: str):
    if not is_valid_openai_voice(voice_id):
        return JSONResponse(status_code=404, content={"error": f"Unknown voice: {voice_id}"})

    if voice_id in _voice_preview_cache:
        return Response(content=_voice_preview_cache[voice_id], media_type="audio/wav")

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.audio.speech.create(
            model="tts-1",
            voice=voice_id,  # type: ignore[arg-type]
            input=PREVIEW_PHRASE,
            response_format="wav",
        )
        audio_bytes = response.content
        _voice_preview_cache[voice_id] = audio_bytes
        return Response(content=audio_bytes, media_type="audio/wav")
    except Exception as e:
        log.error("voice_preview.error", voice_id=voice_id, error=str(e))
        return JSONResponse(status_code=500, content={"error": str(e)})


# ── WebSocket conversation endpoint ───────────────────────────────────────────

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()
    _websockets[session_id] = websocket

    selected_voice_id: str | None = websocket.query_params.get("voice_id")

    info = _session_manager.get(session_id)
    if info is None:
        info = await _session_manager.create(
            session_id=session_id,
            avatar_id=settings.default_avatar,
            system_prompt=settings.system_prompt,
            llm_provider=settings.llm_provider.value,
            llm_model=settings.llm_model,
        )

    avatar = _avatar_registry.get_avatar(info.avatar_id) or _avatar_registry.list_avatars()[0]

    # Voice precedence: query param > avatar default > "nova"
    # Only accept valid OpenAI voice names.
    if selected_voice_id and not is_valid_openai_voice(selected_voice_id):
        log.warning("session.invalid_openai_voice", voice_id=selected_voice_id)
        selected_voice_id = None

    active_voice_id = selected_voice_id or "nova"
    log.info("session.connected", session_id=session_id, avatar=avatar.id, voice=active_voice_id)

    try:
        from pipecat.audio.vad.silero import SileroVADAnalyzer
        from pipecat.pipeline.pipeline import Pipeline
        from pipecat.pipeline.runner import PipelineRunner
        from pipecat.pipeline.task import PipelineParams, PipelineTask
        from pipecat.processors.aggregators.llm_context import LLMContext
        from pipecat.processors.aggregators.llm_response_universal import (
            LLMAssistantAggregator,
            LLMUserAggregator,
        )
        from pipecat.processors.audio.vad_processor import VADProcessor
        from pipecat.services.openai.tts import OpenAITTSService
        from pipecat.transports.websocket.fastapi import (
            FastAPIWebsocketParams,
            FastAPIWebsocketTransport,
        )

        await websocket.send_text(json.dumps({
            "type": "session_ready",
            "session_id": session_id,
            "avatar": avatar.model_dump(),
            "available_avatars": [a.model_dump() for a in _avatar_registry.list_avatars()],
            "voice_id": active_voice_id,
        }))

        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                audio_in_passthrough=True,
                add_wav_header=True,
                serializer=RawAudioSerializer(),
            ),
        )

        context = LLMContext()
        # Always prepend the language-mirroring instruction so it can't be overridden
        # by a custom SYSTEM_PROMPT, then append the persona prompt.
        base = settings._BASE_INSTRUCTION
        persona = info.system_prompt or ""
        full_system = f"{base}\n\n{persona}".strip()
        context.add_message({"role": "system", "content": full_system})
        _contexts[session_id] = context

        user_aggregator = LLMUserAggregator(context)
        text_input_processor = TextInputProcessor(
            context, websocket, _avatar_registry, ask_registry=_ask_registry
        )

        tts = OpenAITTSService(
            api_key=settings.openai_api_key,
            voice=active_voice_id,  # type: ignore[arg-type]
            model="tts-1",          # tts-1 supports speed param; gpt-4o-mini-tts ignores it
            speed=settings.tts_speed,
        )

        from pipecat.services.whisper.stt import WhisperSTTService
        # language=None → Whisper auto-detects the spoken language instead of
        # forcing English, which caused Hindi/other languages to be mis-transcribed.
        stt = WhisperSTTService(
            model="small",
            device="cpu",
            settings=WhisperSTTService.Settings(language=None),
        )

        avatar_processor = AvatarStateProcessor(session_id, websocket)
        vad_processor = VADProcessor(vad_analyzer=SileroVADAnalyzer())

        if settings.agent_backend == "claude_code":
            # Embed Claude Code's agent loop. The Agent SDK owns conversation state,
            # so the context aggregator/sanitizer + LLM service are not on this path;
            # STT in and TTS out are unchanged.
            from backend.processors.claude_agent import (
                ClaudeAgentProcessor,
                build_claude_adapter,
            )

            claude_agent_processor = ClaudeAgentProcessor(
                build_claude_adapter(settings), websocket
            )
            pipeline = Pipeline([
                transport.input(),
                text_input_processor,
                vad_processor,
                stt,
                user_aggregator,
                claude_agent_processor,
                avatar_processor,
                tts,
                transport.output(),
            ])
        else:
            llm = create_llm_service(settings)
            assistant_aggregator = LLMAssistantAggregator(context)
            context_sanitizer = ContextSanitizerProcessor(context)
            pipeline = Pipeline([
                transport.input(),
                text_input_processor,
                vad_processor,
                stt,
                user_aggregator,
                context_sanitizer,
                llm,
                avatar_processor,
                tts,
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
