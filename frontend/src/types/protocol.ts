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
export type ActionStatus = 'start' | 'success' | 'error'

// Agent action (tool/step) surfaced as a chip — never spoken aloud.
export interface AgentAction {
  id: string
  name: string
  detail?: string
  status: ActionStatus
}

// A clarification / approval request from the agent.
export interface AskPrompt {
  id: string
  question: string
  kind: 'clarify' | 'approve'
  options?: string[]
}

// Server → Client messages.
// Aligned with the Presence Protocol (packages/presence-protocol). Both the
// legacy v0 names (llm_token/llm_done/transcript_final/voice_change_ack) and the
// v0.1 names (speak_delta/done/transcript/voice_changed + think/action/ask/status)
// are accepted so the renderer works with any adapter.
export type ServerMessage =
  | { type: 'session_ready'; session_id: string; avatar: AvatarMeta; available_avatars: AvatarMeta[]; voice_id: string }
  | { type: 'avatar_state'; animation: AnimationName; speaking: boolean; audio_level?: number }
  // conversational text (spoken)
  | { type: 'transcript_final'; text: string; speaker: 'user' | 'assistant' }
  | { type: 'transcript'; text: string; speaker: 'user' | 'assistant' }
  | { type: 'llm_token'; token: string }
  | { type: 'speak_delta'; text: string }
  | { type: 'llm_done'; full_text: string }
  | { type: 'done'; full_text?: string; cost_usd?: number; duration_ms?: number; turns?: number }
  // agent activity (shown, not spoken)
  | { type: 'think'; text?: string }
  | { type: 'action'; id?: string; name: string; detail?: string; input?: Record<string, unknown>; status?: ActionStatus }
  | { type: 'ask'; id: string; question: string; kind?: 'clarify' | 'approve'; options?: string[] }
  | { type: 'status'; text?: string; progress?: number }
  // lifecycle
  | { type: 'tts_start'; turn_id?: string }
  | { type: 'tts_done'; turn_id?: string; duration_ms?: number }
  | { type: 'avatar_changed'; avatar: AvatarMeta }
  | { type: 'voice_change_ack'; voice_id: string; reconnect_required: boolean }
  | { type: 'voice_changed'; voice_id: string; reconnect_required?: boolean }
  | { type: 'error'; message: string; code?: string }

// Client → Server messages (upstream control).
export type ClientMessage =
  | { type: 'text_input'; text: string; session_id?: string }
  | { type: 'user_turn'; text: string; session_id?: string }
  | { type: 'interrupt'; session_id?: string }
  | { type: 'ask_response'; id: string; value: string; session_id?: string }
  | { type: 'set_avatar'; avatar_id: string; session_id?: string }
  | { type: 'set_voice'; voice_id: string; session_id?: string }

// Transcript entry for display
export interface TranscriptEntry {
  id: string
  speaker: 'user' | 'assistant'
  text: string
  timestamp: number
}
