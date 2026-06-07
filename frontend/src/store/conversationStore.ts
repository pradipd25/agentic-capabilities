import { create } from 'zustand'
import type { AgentAction, AnimationName, AskPrompt, AvatarMeta, TranscriptEntry } from '../types/protocol'

interface ConversationState {
  sessionId: string | null
  avatar: AvatarMeta | null
  availableAvatars: AvatarMeta[]
  animation: AnimationName
  isSpeaking: boolean
  isListening: boolean
  audioLevel: number
  transcript: TranscriptEntry[]
  currentToken: string
  actions: AgentAction[]
  pendingAsk: AskPrompt | null
  statusText: string
  isConnected: boolean
  voiceId: string

  setSession: (id: string, avatar: AvatarMeta, avatars: AvatarMeta[], voiceId: string) => void
  setAvatar: (avatar: AvatarMeta) => void
  setAnimation: (animation: AnimationName, speaking: boolean) => void
  setAudioLevel: (level: number) => void
  addTranscriptEntry: (entry: TranscriptEntry) => void
  appendToken: (token: string) => void
  finalizeToken: () => void
  upsertAction: (action: AgentAction) => void
  setAsk: (ask: AskPrompt) => void
  clearAsk: () => void
  setStatus: (text: string) => void
  clearTurn: () => void
  setConnected: (v: boolean) => void
  setVoiceId: (id: string) => void
}

export const useConversationStore = create<ConversationState>((set) => ({
  sessionId: null,
  avatar: null,
  availableAvatars: [],
  animation: 'idle',
  isSpeaking: false,
  isListening: false,
  audioLevel: 0,
  transcript: [],
  currentToken: '',
  actions: [],
  pendingAsk: null,
  statusText: '',
  isConnected: false,
  voiceId: 'nova',

  setSession: (id, avatar, avatars, voiceId) =>
    set({ sessionId: id, avatar, availableAvatars: avatars, isConnected: true, voiceId }),

  setAvatar: (avatar) => set({ avatar }),

  setAnimation: (animation, speaking) =>
    set({ animation, isSpeaking: speaking, isListening: animation === 'listening' }),

  setAudioLevel: (level) => set({ audioLevel: level }),

  addTranscriptEntry: (entry) =>
    set((s) => ({
      transcript: [...s.transcript, entry],
      currentToken: '',
      // a new user turn resets the previous turn's activity
      ...(entry.speaker === 'user' ? { actions: [], pendingAsk: null, statusText: '' } : {}),
    })),

  appendToken: (token) =>
    set((s) => ({ currentToken: s.currentToken + token })),

  finalizeToken: () => set({ currentToken: '', statusText: '' }),

  // add a new action, or update the status of an existing one (matched by id)
  upsertAction: (action) =>
    set((s) => {
      const i = action.id ? s.actions.findIndex((a) => a.id === action.id) : -1
      if (i >= 0) {
        const next = s.actions.slice()
        next[i] = { ...next[i], ...action }
        return { actions: next }
      }
      return { actions: [...s.actions, action] }
    }),

  setAsk: (ask) => set({ pendingAsk: ask }),

  clearAsk: () => set({ pendingAsk: null }),

  setStatus: (text) => set({ statusText: text }),

  clearTurn: () => set({ actions: [], pendingAsk: null, statusText: '' }),

  setConnected: (v) => set({ isConnected: v }),

  setVoiceId: (id) => set({ voiceId: id }),
}))
