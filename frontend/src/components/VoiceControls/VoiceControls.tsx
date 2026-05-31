import { useConversationStore } from '../../store/conversationStore'

interface Props {
  isCapturing: boolean
  onToggle: () => void
}

export function VoiceControls({ isCapturing, onToggle }: Props) {
  const { isConnected, animation } = useConversationStore()

  const statusText = !isConnected
    ? 'Connecting...'
    : isCapturing
    ? animation === 'talking'
      ? 'Avatar is speaking...'
      : 'Listening...'
    : 'Click mic to speak'

  return (
    <div className="flex flex-col items-center gap-4 py-4">
      {/* Mic button */}
      <button
        onClick={onToggle}
        disabled={!isConnected}
        className={`relative w-16 h-16 rounded-full flex items-center justify-center transition-all
          ${isCapturing
            ? 'bg-red-500 hover:bg-red-600 shadow-lg shadow-red-500/30'
            : 'bg-accent hover:bg-accent/90 shadow-lg shadow-accent/30'
          }
          disabled:opacity-40 disabled:cursor-not-allowed`}
      >
        {/* Pulse ring while capturing */}
        {isCapturing && (
          <span className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-30" />
        )}
        <MicIcon active={isCapturing} />
      </button>

      <p className="text-xs text-gray-400">{statusText}</p>
    </div>
  )
}

function MicIcon({ active }: { active: boolean }) {
  return (
    <svg
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="white"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {active ? (
        // Stop icon
        <rect x="6" y="6" width="12" height="12" rx="2" fill="white" stroke="none" />
      ) : (
        // Mic icon
        <>
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </>
      )}
    </svg>
  )
}
