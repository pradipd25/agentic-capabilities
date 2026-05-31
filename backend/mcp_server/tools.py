import uuid

import mcp.types as types
from mcp.server import Server

mcp_server = Server("agentic-capabilities-video")


def get_deps(ctx):
    """Extract shared dependencies from MCP request context."""
    return ctx.request_context.lifespan_context


@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="avatar.list_avatars",
            description="List all available avatar characters.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="avatar.create_session",
            description="Create a new avatar conversation session. Returns session_id and a join_url for the user to open in their browser.",
            inputSchema={
                "type": "object",
                "properties": {
                    "avatar_id": {"type": "string", "description": "Avatar ID from list_avatars"},
                    "system_prompt": {"type": "string", "description": "System prompt for the LLM"},
                    "llm_provider": {"type": "string", "description": "Override LLM provider (claude|openai|gemini|groq|ollama)"},
                    "llm_model": {"type": "string", "description": "Override LLM model name"},
                },
                "required": ["avatar_id"],
            },
        ),
        types.Tool(
            name="avatar.speak",
            description="Make the avatar speak a message aloud in the active session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "text": {"type": "string"},
                    "interrupt": {"type": "boolean", "default": False},
                },
                "required": ["session_id", "text"],
            },
        ),
        types.Tool(
            name="avatar.set_avatar",
            description="Swap the avatar character mid-conversation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "avatar_id": {"type": "string"},
                },
                "required": ["session_id", "avatar_id"],
            },
        ),
        types.Tool(
            name="avatar.set_animation",
            description="Trigger a named animation on the avatar (idle|talking|thinking|greeting).",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "animation": {"type": "string"},
                },
                "required": ["session_id", "animation"],
            },
        ),
        types.Tool(
            name="avatar.get_transcript",
            description="Retrieve recent conversation turns.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "last_n": {"type": "integer", "default": 50},
                },
                "required": ["session_id"],
            },
        ),
        types.Tool(
            name="avatar.list_sessions",
            description="List all active conversation sessions.",
            inputSchema={"type": "object", "properties": {}},
        ),
        types.Tool(
            name="avatar.close_session",
            description="Gracefully close a conversation session.",
            inputSchema={
                "type": "object",
                "properties": {"session_id": {"type": "string"}},
                "required": ["session_id"],
            },
        ),
        types.Tool(
            name="avatar.inject_context",
            description="Inject additional context into the LLM system prompt for a session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "session_id": {"type": "string"},
                    "context": {"type": "string"},
                },
                "required": ["session_id", "context"],
            },
        ),
    ]


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    import json
    from pipecat.frames.frames import TextFrame

    deps = get_deps(mcp_server)
    session_manager = deps["session_manager"]
    avatar_registry = deps["avatar_registry"]
    config = deps["config"]
    host = deps["host"]

    def ok(data: dict) -> list[types.TextContent]:
        return [types.TextContent(type="text", text=json.dumps(data))]

    if name == "avatar.list_avatars":
        avatars = [a.model_dump() for a in avatar_registry.list_avatars()]
        return ok({"avatars": avatars})

    if name == "avatar.create_session":
        session_id = str(uuid.uuid4())[:8]
        await session_manager.create(
            session_id=session_id,
            avatar_id=arguments.get("avatar_id", config.default_avatar),
            system_prompt=arguments.get("system_prompt", config.system_prompt),
            llm_provider=arguments.get("llm_provider", config.llm_provider.value),
            llm_model=arguments.get("llm_model", config.llm_model),
        )
        join_url = f"http://{host}:5173?session={session_id}"
        return ok({"session_id": session_id, "join_url": join_url})

    if name == "avatar.list_sessions":
        return ok({"sessions": session_manager.list_sessions()})

    if name == "avatar.close_session":
        closed = await session_manager.close_session(arguments["session_id"])
        return ok({"closed": closed})

    # Tools that require an active session with a pipeline task
    session_id = arguments.get("session_id")
    info = session_manager.get(session_id)

    if info is None:
        return ok({"error": f"Session '{session_id}' not found"})

    if name == "avatar.speak":
        if info.task:
            text = arguments["text"]
            await info.task.queue_frame(TextFrame(text=text))
            return ok({"spoken": True})
        return ok({"spoken": False, "reason": "session not yet connected"})

    if name == "avatar.set_animation":
        if info.task:
            # Send avatar_state directly via the websocket stored in session
            ws = deps.get("websockets", {}).get(session_id)
            if ws:
                import json as _json
                await ws.send_text(_json.dumps({
                    "type": "avatar_state",
                    "animation": arguments["animation"],
                }))
            return ok({"ok": True})
        return ok({"ok": False})

    if name == "avatar.get_transcript":
        last_n = arguments.get("last_n", 50)
        ctx_store = deps.get("contexts", {})
        context = ctx_store.get(session_id)
        if context:
            messages = context.messages[-last_n:]
            return ok({"entries": messages})
        return ok({"entries": []})

    if name == "avatar.inject_context":
        ctx_store = deps.get("contexts", {})
        context = ctx_store.get(session_id)
        if context:
            existing = context.system or ""
            context.system = existing + "\n" + arguments["context"]
            return ok({"injected": True})
        return ok({"injected": False})

    if name == "avatar.set_avatar":
        new_avatar = avatar_registry.get_avatar(arguments["avatar_id"])
        if new_avatar is None:
            return ok({"changed": False, "reason": "avatar not found"})
        info.avatar_id = arguments["avatar_id"]
        ws = deps.get("websockets", {}).get(session_id)
        if ws:
            import json as _json
            await ws.send_text(_json.dumps({
                "type": "avatar_changed",
                "avatar": new_avatar.model_dump(),
            }))
        return ok({"changed": True, "avatar": new_avatar.model_dump()})

    return ok({"error": f"Unknown tool: {name}"})
