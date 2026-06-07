import { useCallback, useRef, useState } from 'react'
import { AvatarScene } from './components/AvatarScene/AvatarScene'
import { AvatarSelector } from './components/AvatarSelector/AvatarSelector'
import { ChatPanel } from './components/ChatPanel/ChatPanel'
import { VocalPalette } from './components/VocalPalette/VocalPalette'
import { VoiceControls } from './components/VoiceControls/VoiceControls'
import { useAudioCapture } from './hooks/useAudioCapture'
import { useAudioPlayer } from './hooks/useAudioPlayer'
import { useVoicePreferences } from './hooks/useVoicePreferences'
import { useWebSocket } from './hooks/useWebSocket'
import { useConversationStore } from './store/conversationStore'
import type { AvatarMeta } from './types/protocol'

const params = new URLSearchParams(window.location.search)
const SESSION_ID = params.get('session') ?? crypto.randomUUID().slice(0, 8)

// Barge-in tuning. While the avatar is speaking the mic is energy-gated so its
// own echo (low level, after AEC) doesn't trigger the server VAD, but real
// speech (loud, close to the mic) passes through and interrupts it.
//
// Robust gate: a barge-in is only declared after BARGE_IN_MIN_CHUNKS *consecutive*
// chunks exceed BARGE_IN_RMS. Speaker echo is bursty (loud consonants separated
// by gaps), so any single quiet chunk resets the streak — transient echo never
// sustains. Real speech (loud, close, continuous) does. Until the streak is
// confirmed the chunks are buffered, then replayed to the server so the onset of
// the utterance isn't lost. Once confirmed, BARGE_IN_HOLD_MS keeps the mic open
// (refreshed while speech continues) so the whole utterance streams smoothly.
//
// Tuning: lower BARGE_IN_RMS / BARGE_IN_MIN_CHUNKS if you must speak too loudly
// or too long to interrupt; raise them if echo still cuts the avatar off.
const BARGE_IN_RMS = 0.08          // loudness threshold (0–1), above the post-AEC echo floor
const BARGE_IN_MIN_CHUNKS = 3      // consecutive loud 64 ms chunks (~256 ms) to confirm real speech
const BARGE_IN_HOLD_MS = 800       // keep mic open this long after the last loud chunk

function rmsFromInt16(buf: ArrayBuffer): number {
  const samples = new Int16Array(buf)
  if (samples.length === 0) return 0
  let sum = 0
  for (let i = 0; i < samples.length; i++) {
    const v = samples[i] / 32768
    sum += v * v
  }
  return Math.sqrt(sum / samples.length)
}

function App() {
  const { voiceId, saveVoice } = useVoicePreferences()
  const { playChunk, initAudio, flush, audioReady, lastError, chunksPlayed, isBotAudioPlaying } = useAudioPlayer()
  const { sendBinary, sendText, reconnectWithVoice } = useWebSocket(SESSION_ID, voiceId, playChunk, saveVoice)
  const { isConnected, avatar } = useConversationStore()

  const [showPalette, setShowPalette] = useState(false)

  // Timestamp (performance.now) until which the mic stays open after detecting
  // barge-in speech, so an utterance streams continuously through brief pauses.
  const bargeInUntilRef = useRef(0)
  // Count of consecutive loud chunks while building toward a confirmed barge-in.
  const loudStreakRef = useRef(0)
  // Onset chunks captured during the streak, replayed once barge-in is confirmed
  // so the start of the utterance reaches the server STT.
  const onsetRef = useRef<ArrayBuffer[]>([])

  // Mic routing:
  //  - When the avatar is silent, send everything (normal listening).
  //  - While the avatar is speaking, only forward audio that is *sustained* real
  //    speech. The avatar's own echo (low level after AEC, and bursty) can't
  //    sustain a loud streak, so it never falsely interrupts a long response;
  //    but when the user actually talks over the avatar the streak confirms, the
  //    avatar is silenced immediately, and the audio (onset included) is streamed
  //    to the server VAD — giving robust voice barge-in.
  const handleChunk = useCallback((data: ArrayBuffer) => {
    if (!isBotAudioPlaying()) {
      // Normal listening between turns — reset any half-built barge-in state.
      loudStreakRef.current = 0
      onsetRef.current = []
      sendBinary(data)
      return
    }

    const now = performance.now()
    const loud = rmsFromInt16(data) > BARGE_IN_RMS

    // Already in a confirmed barge-in window: keep streaming, and extend the
    // hold while the user is still speaking so words don't get chopped.
    if (now < bargeInUntilRef.current) {
      if (loud) bargeInUntilRef.current = now + BARGE_IN_HOLD_MS
      sendBinary(data)
      return
    }

    if (!loud) {
      // A quiet chunk breaks the streak — transient echo, not sustained speech.
      loudStreakRef.current = 0
      onsetRef.current = []
      return
    }

    // Building a streak of consecutive loud chunks; buffer the onset audio.
    loudStreakRef.current += 1
    onsetRef.current.push(data)
    if (loudStreakRef.current >= BARGE_IN_MIN_CHUNKS) {
      flush()                                       // silence the avatar at once
      onsetRef.current.forEach((c) => sendBinary(c)) // replay the captured onset
      onsetRef.current = []
      bargeInUntilRef.current = now + BARGE_IN_HOLD_MS
    }
  }, [sendBinary, isBotAudioPlaying, flush])

  const { isCapturing, start, stop } = useAudioCapture(handleChunk)

  const toggleMic = () => {
    initAudio()
    if (isCapturing) {
      stop()
    } else {
      start()
    }
  }

  const handleSendText = (text: string) => {
    initAudio()
    useConversationStore.getState().clearTurn()
    sendText({ type: 'text_input', text, session_id: SESSION_ID })
  }

  const handleAnswerAsk = (id: string, value: string) => {
    useConversationStore.getState().clearAsk()
    sendText({ type: 'ask_response', id, value, session_id: SESSION_ID })
  }

  const handleSelectAvatar = (a: AvatarMeta) => {
    sendText({ type: 'set_avatar', avatar_id: a.id, session_id: SESSION_ID })
  }

  const handleApplyVoice = (newVoiceId: string) => {
    initAudio()           // ensure shared AudioContext is unlocked from this click
    saveVoice(newVoiceId)
    reconnectWithVoice(newVoiceId)
  }

  return (
    <div className="flex flex-col h-screen bg-surface text-white overflow-hidden">

      {/* ── Audio status banner ─────────────────────────────────────────── */}
      {!audioReady && (
        <div className="flex items-center justify-between px-4 py-2 bg-yellow-900/60 border-b border-yellow-700 text-yellow-200 text-xs">
          <span>🔇 Audio not enabled — click below to unlock speaker output</span>
          <button
            onClick={initAudio}
            className="ml-4 px-3 py-1 rounded-lg bg-yellow-600 hover:bg-yellow-500 text-white font-medium transition-colors"
          >
            Enable Audio
          </button>
        </div>
      )}
      {audioReady && (
        <div className="flex items-center px-4 py-1 bg-green-900/40 border-b border-green-800 text-green-300 text-xs">
          🔊 Audio ready — {chunksPlayed} chunk{chunksPlayed !== 1 ? 's' : ''} played
        </div>
      )}
      {lastError && (
        <div className="px-4 py-1 bg-red-900/50 border-b border-red-800 text-red-300 text-xs">
          Audio error: {lastError}
        </div>
      )}

      {/* ── Main layout ─────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden min-h-0">
        {/* Left — Avatar + controls */}
        <div className="flex flex-col w-1/2 border-r border-border">
          <div className="flex-1 p-4 min-h-0">
            <AvatarScene />
          </div>

          <div className="px-4 py-2 border-t border-border flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold">{avatar?.name ?? '...'}</p>
              <p className="text-xs text-gray-500">{avatar?.description ?? ''}</p>
            </div>
            <span
              className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-400' : 'bg-yellow-400 animate-pulse'}`}
            />
          </div>

          <div className="border-t border-border">
            <AvatarSelector onSelect={handleSelectAvatar} />
          </div>

          <div className="border-t border-border">
            <VoiceControls isCapturing={isCapturing} onToggle={toggleMic} />
          </div>
        </div>

        {/* Right — Chat */}
        <div className="flex flex-col w-1/2 min-h-0">
          {/* Header with settings icon */}
          <div className="p-4 border-b border-border flex items-center justify-between">
            <div>
              <h1 className="text-sm font-semibold text-gray-300">Conversation</h1>
              <p className="text-xs text-gray-500">Session: {SESSION_ID}</p>
            </div>
            <button
              onClick={() => setShowPalette(true)}
              className="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-panel border border-transparent hover:border-border transition-all"
              title="VocalPalette — choose voice texture"
            >
              <SettingsIcon />
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel onSendText={handleSendText} onAnswerAsk={handleAnswerAsk} />
          </div>
        </div>
      </div>

      {/* VocalPalette drawer */}
      {showPalette && (
        <VocalPalette
          onClose={() => setShowPalette(false)}
          onApply={handleApplyVoice}
          onInitAudio={initAudio}
        />
      )}
    </div>
  )
}

function SettingsIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  )
}

export default App
