/**
 * Presence Protocol — the transport-agnostic contract between an agent adapter
 * and a face renderer. See ../README.md for the full spec.
 *
 * Version 0.1.0 (alpha).
 */

export const PROTOCOL_VERSION = '0.1.0'

// ---- shared vocabulary ----

export type AnimationName = 'idle' | 'listening' | 'thinking' | 'talking' | 'greeting'
export type Speaker = 'user' | 'assistant'
export type ActionStatus = 'start' | 'success' | 'error'
export type AskKind = 'clarify' | 'approve'

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

// ---- downstream: agent -> face (presence events) ----

export type PresenceEvent =
  | { type: 'session_ready'; session_id: string; protocol_version?: string; avatar?: AvatarMeta; available_avatars?: AvatarMeta[]; voice_id?: string }
  | { type: 'avatar_state'; animation: AnimationName; speaking?: boolean; audio_level?: number }
  | { type: 'speak_delta'; text: string }
  | { type: 'transcript'; speaker: Speaker; text: string }
  | { type: 'think'; text?: string }
  | { type: 'action'; name: string; detail?: string; input?: Record<string, unknown>; status?: ActionStatus; id?: string }
  | { type: 'ask'; id: string; question: string; kind?: AskKind; options?: string[] }
  | { type: 'status'; text?: string; progress?: number }
  | { type: 'avatar_changed'; avatar: AvatarMeta }
  | { type: 'voice_changed'; voice_id: string; reconnect_required?: boolean }
  | { type: 'error'; message: string; code?: string }
  | { type: 'done'; full_text?: string; cost_usd?: number; duration_ms?: number; turns?: number }

export type PresenceEventType = PresenceEvent['type']

// ---- upstream: face -> agent (control messages) ----

export type ControlMessage =
  | { type: 'user_turn'; text: string }
  | { type: 'interrupt' }
  | { type: 'ask_response'; id: string; value: string }
  | { type: 'set_avatar'; avatar_id: string }
  | { type: 'set_voice'; voice_id: string }

export type ControlMessageType = ControlMessage['type']

// ---- conformance helpers ----

const PRESENCE_TYPES: ReadonlySet<string> = new Set<PresenceEventType>([
  'session_ready', 'avatar_state', 'speak_delta', 'transcript', 'think',
  'action', 'ask', 'status', 'avatar_changed', 'voice_changed', 'error', 'done',
])

const CONTROL_TYPES: ReadonlySet<string> = new Set<ControlMessageType>([
  'user_turn', 'interrupt', 'ask_response', 'set_avatar', 'set_voice',
])

export function isPresenceEvent(value: unknown): value is PresenceEvent {
  return !!value && typeof value === 'object' && PRESENCE_TYPES.has((value as { type?: string }).type ?? '')
}

export function isControlMessage(value: unknown): value is ControlMessage {
  return !!value && typeof value === 'object' && CONTROL_TYPES.has((value as { type?: string }).type ?? '')
}

// ---- UI helper type (renderer-side, not on the wire) ----

export interface TranscriptEntry {
  id: string
  speaker: Speaker
  text: string
  timestamp: number
}
