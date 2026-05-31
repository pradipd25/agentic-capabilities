export interface AvatarAnimations {
  idle: string
  talking: string
  thinking: string
  greeting: string
}

export interface AvatarMeta {
  id: string
  name: string
  description: string
  thumbnail_url: string
  model_url: string
  animations: AvatarAnimations
  voice_id: string
  style: string
}

export interface VoiceMeta {
  id: string
  name: string
  description: string
  gender: 'male' | 'female' | 'neutral'
}

export type AnimationName = 'idle' | 'listening' | 'thinking' | 'talking' | 'greeting'

// Server → Client messages
export type ServerMessage =
  | { type: 'session_ready'; session_id: string; avatar: AvatarMeta; available_avatars: AvatarMeta[]; voice_id: string }
  | { type: 'avatar_state'; animation: AnimationName; speaking: boolean; audio_level?: number }
  | { type: 'transcript_final'; text: string; speaker: 'user' | 'assistant' }
  | { type: 'llm_token'; token: string }
  | { type: 'llm_done'; full_text: string }
  | { type: 'tts_start'; turn_id?: string }
  | { type: 'tts_done'; turn_id?: string; duration_ms?: number }
  | { type: 'avatar_changed'; avatar: AvatarMeta }
  | { type: 'voice_change_ack'; voice_id: string; reconnect_required: boolean }
  | { type: 'error'; message: string; code?: string }

// Transcript entry for display
export interface TranscriptEntry {
  id: string
  speaker: 'user' | 'assistant'
  text: string
  timestamp: number
}
