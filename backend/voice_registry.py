"""VocalPalette — voice definitions for each supported TTS provider."""

from typing import Literal

OPENAI_VOICES: list[dict] = [
    {"id": "alloy",   "name": "Alloy",   "description": "Neutral and balanced",      "gender": "neutral"},
    {"id": "ash",     "name": "Ash",     "description": "Direct and confident",       "gender": "male"},
    {"id": "coral",   "name": "Coral",   "description": "Warm and friendly",          "gender": "female"},
    {"id": "echo",    "name": "Echo",    "description": "Smooth and clear",           "gender": "male"},
    {"id": "fable",   "name": "Fable",   "description": "Expressive and dynamic",     "gender": "neutral"},
    {"id": "nova",    "name": "Nova",    "description": "Energetic and bright",       "gender": "female"},
    {"id": "onyx",    "name": "Onyx",    "description": "Deep and authoritative",     "gender": "male"},
    {"id": "sage",    "name": "Sage",    "description": "Calm and thoughtful",        "gender": "neutral"},
    {"id": "shimmer", "name": "Shimmer", "description": "Gentle and soothing",        "gender": "female"},
]

OPENAI_VOICE_IDS = {v["id"] for v in OPENAI_VOICES}

PREVIEW_PHRASE = "Hello! I'm your AI assistant. How can I help you today?"


def get_voices_for_provider(provider: str) -> list[dict]:
    if provider == "openai":
        return OPENAI_VOICES
    return []


def is_valid_openai_voice(voice_id: str) -> bool:
    return voice_id in OPENAI_VOICE_IDS
