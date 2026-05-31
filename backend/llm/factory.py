from backend.config import LLMProvider, Settings


def create_llm_service(config: Settings):
    """Return the appropriate Pipecat LLM service based on LLM_PROVIDER."""
    provider = config.llm_provider

    if provider == LLMProvider.CLAUDE:
        from pipecat.services.anthropic.llm import AnthropicLLMService
        return AnthropicLLMService(
            api_key=config.anthropic_api_key,
            model=config.llm_model or "claude-sonnet-4-5",
        )

    if provider == LLMProvider.OPENAI:
        from pipecat.services.openai.llm import OpenAILLMService
        return OpenAILLMService(
            api_key=config.openai_api_key,
            model=config.llm_model or "gpt-4o",
        )

    if provider == LLMProvider.GEMINI:
        from pipecat.services.google.llm import GoogleLLMService
        return GoogleLLMService(
            api_key=config.google_api_key,
            model=config.llm_model or "gemini-2.0-flash",
        )

    if provider == LLMProvider.GROQ:
        from pipecat.services.groq.llm import GroqLLMService
        return GroqLLMService(
            api_key=config.groq_api_key,
            model=config.llm_model or "llama-3.1-70b-versatile",
        )

    if provider == LLMProvider.OLLAMA:
        from pipecat.services.ollama.llm import OllamaLLMService
        return OllamaLLMService(
            base_url=config.ollama_base_url,
            model=config.llm_model or "llama3",
        )

    raise ValueError(f"Unsupported LLM provider: {provider}")
