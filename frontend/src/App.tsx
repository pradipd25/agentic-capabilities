import { useCallback } from 'react'
import { AvatarScene } from './components/AvatarScene/AvatarScene'
import { AvatarSelector } from './components/AvatarSelector/AvatarSelector'
import { ChatPanel } from './components/ChatPanel/ChatPanel'
import { VoiceControls } from './components/VoiceControls/VoiceControls'
import { useAudioCapture } from './hooks/useAudioCapture'
import { useAudioPlayer } from './hooks/useAudioPlayer'
import { useWebSocket } from './hooks/useWebSocket'
import { useConversationStore } from './store/conversationStore'
import type { AvatarMeta } from './types/protocol'

const params = new URLSearchParams(window.location.search)
const SESSION_ID = params.get('session') ?? crypto.randomUUID().slice(0, 8)

function App() {
  const { playChunk, initAudio, audioReady, lastError, chunksPlayed } = useAudioPlayer()
  const { sendBinary, sendText } = useWebSocket(SESSION_ID, playChunk)
  const { isConnected, avatar } = useConversationStore()

  const handleChunk = useCallback((data: ArrayBuffer) => {
    sendBinary(data)
  }, [sendBinary])

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
    sendText({ type: 'text_input', text, session_id: SESSION_ID })
  }

  const handleSelectAvatar = (a: AvatarMeta) => {
    sendText({ type: 'set_avatar', avatar_id: a.id, session_id: SESSION_ID })
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
          <div className="p-4 border-b border-border">
            <h1 className="text-sm font-semibold text-gray-300">Conversation</h1>
            <p className="text-xs text-gray-500">Session: {SESSION_ID}</p>
          </div>
          <div className="flex-1 min-h-0">
            <ChatPanel onSendText={handleSendText} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
