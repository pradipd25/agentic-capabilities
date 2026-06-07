from enum import Enum
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Server
    host: str = "0.0.0.0"
    port: int = 8100

    # LLM
    llm_provider: LLMProvider = LLMProvider.CLAUDE
    llm_model: str = ""

    # Agent backend: "pipeline" = single LLM completion via Pipecat (default);
    # "claude_code" = embed Claude Code's agent loop via the Claude Agent SDK
    # (tools, action chips, ask/approve). Requires claude-agent-sdk + ANTHROPIC_API_KEY.
    agent_backend: str = "pipeline"
    # Comma-separated tool allowlist for the agent backend; empty = read-only default
    # (Read, Glob, Grep, WebSearch, WebFetch). Add Edit/Write/Bash to enable changes.
    agent_allowed_tools: str = ""
    agent_permission_mode: str = "default"
    # System prompt for the claude_code agent path. The agent's output is read aloud
    # by TTS, so the default steers Claude away from its verbose markdown IDE style
    # toward short spoken prose. Override via AGENT_SYSTEM_PROMPT.
    agent_system_prompt: str = (
        "CRITICAL OUTPUT RULE: your text is converted to speech and read aloud verbatim — "
        "any formatting characters are spoken as literal symbols (a list dash is spoken as "
        "'dash', double asterisks as 'asterisk asterisk'). NEVER use markdown: no **bold**, "
        "no `backticks`, no # headings, no - or * bullet lists, no numbered lists, no code "
        "fences, no emoji. Write only plain spoken sentences, the way a person talks out loud. "
        "Say names naturally — 'the config file', not a literal file path or `code` span. "
        "Keep replies short and conversational: usually one to three sentences, never more "
        "than a short paragraph. For a broad question, give a brief spoken summary first and "
        "offer to go deeper, instead of explaining everything at once."
    )

    # Provider keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # Conversation
    system_prompt: str = "You are a friendly and helpful AI assistant. Keep responses concise and conversational."
    tts_speed: float = 1.25  # 0.25–4.0; 1.0 = normal OpenAI pace, 1.25 = natural conversation speed

    # Base instruction always prepended to system_prompt — not user-overridable
    _BASE_INSTRUCTION: str = (
        "Always reply in the same language the user writes or speaks in. "
        "If the user's message contains a mix of languages, reply in English."
    )
    default_avatar: str = "aria"


settings = Settings()
