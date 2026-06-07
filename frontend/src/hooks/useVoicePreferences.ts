import { useState } from 'react'

const STORAGE_KEY = 'vocalpalette_voice_id'
const DEFAULT_VOICE = 'nova'

const OPENAI_VOICE_IDS = new Set(['alloy', 'ash', 'coral', 'echo', 'fable', 'nova', 'onyx', 'sage', 'shimmer'])

function loadVoice(): string {
  const stored = localStorage.getItem(STORAGE_KEY) ?? DEFAULT_VOICE
  // Discard any stored ID that isn't a known OpenAI voice
  if (!OPENAI_VOICE_IDS.has(stored)) {
    localStorage.setItem(STORAGE_KEY, DEFAULT_VOICE)
    return DEFAULT_VOICE
  }
  return stored
}

export function useVoicePreferences() {
  const [voiceId, setVoiceIdState] = useState<string>(loadVoice)

  const saveVoice = (id: string) => {
    localStorage.setItem(STORAGE_KEY, id)
    setVoiceIdState(id)
  }

  return { voiceId, saveVoice }
}
