import { useState } from 'react'

const STORAGE_KEY = 'vocalpalette_voice_id'
const DEFAULT_VOICE = 'nova'

export function useVoicePreferences() {
  const [voiceId, setVoiceIdState] = useState<string>(
    () => localStorage.getItem(STORAGE_KEY) ?? DEFAULT_VOICE
  )

  const saveVoice = (id: string) => {
    localStorage.setItem(STORAGE_KEY, id)
    setVoiceIdState(id)
  }

  return { voiceId, saveVoice }
}
