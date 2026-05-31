import { create } from 'zustand'
import type { AnimationName, AvatarMeta, TranscriptEntry } from '../types/protocol'

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
  isConnected: boolean

  setSession: (id: string, avatar: AvatarMeta, avatars: AvatarMeta[]) => void
  setAvatar: (avatar: AvatarMeta) => void
  setAnimation: (animation: AnimationName, speaking: boolean) => void
  setAudioLevel: (level: number) => void
  addTranscriptEntry: (entry: TranscriptEntry) => void
  appendToken: (token: string) => void
  finalizeToken: () => void
  setConnected: (v: boolean) => void
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
  isConnected: false,

  setSession: (id, avatar, avatars) =>
    set({ sessionId: id, avatar, availableAvatars: avatars, isConnected: true }),

  setAvatar: (avatar) => set({ avatar }),

  setAnimation: (animation, speaking) =>
    set({ animation, isSpeaking: speaking, isListening: animation === 'listening' }),

  setAudioLevel: (level) => set({ audioLevel: level }),

  addTranscriptEntry: (entry) =>
    set((s) => ({ transcript: [...s.transcript, entry], currentToken: '' })),

  appendToken: (token) =>
    set((s) => ({ currentToken: s.currentToken + token })),

  finalizeToken: () => set({ currentToken: '' }),

  setConnected: (v) => set({ isConnected: v }),
}))
