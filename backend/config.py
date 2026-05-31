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

    # Provider keys
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # TTS
    elevenlabs_api_key: str = ""

    # Conversation
    system_prompt: str = "You are a friendly and helpful AI assistant. Keep responses concise and conversational."
    default_avatar: str = "aria"


settings = Settings()
