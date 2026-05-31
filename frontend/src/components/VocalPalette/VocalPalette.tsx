import { useCallback, useEffect, useRef, useState } from 'react'
import { useConversationStore } from '../../store/conversationStore'
import type { VoiceMeta } from '../../types/protocol'

interface Props {
  onClose: () => void
  onApply: (voiceId: string) => void
  onInitAudio: () => void  // unlocks the shared AudioContext on user gesture
}

const GENDER_ICON: Record<VoiceMeta['gender'], string> = {
  male: '♂',
  female: '♀',
  neutral: '◈',
}

const GENDER_COLOR: Record<VoiceMeta['gender'], string> = {
  male: 'text-blue-400',
  female: 'text-pink-400',
  neutral: 'text-purple-400',
}

export function VocalPalette({ onClose, onApply, onInitAudio }: Props) {
  const { voiceId: activeVoiceId } = useConversationStore()
  const [voices, setVoices] = useState<VoiceMeta[]>([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(activeVoiceId)

  // Fetch voices from the backend — always gets the correct provider's list
  useEffect(() => {
    fetch('http://localhost:8100/api/voices')
      .then((r) => r.json())
      .then((d) => { setVoices(d.voices ?? []); setLoading(false) })
      .catch(() => setLoading(false))
  }, [])
  const [previewing, setPreviewing] = useState<string | null>(null)
  const previewCache = useRef<Record<string, AudioBuffer>>({})
  const audioCtxRef = useRef<AudioContext | null>(null)

  const getAudioCtx = () => {
    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      audioCtxRef.current = new AudioContext()
    }
    return audioCtxRef.current
  }

  const playPreview = useCallback(async (voice: VoiceMeta) => {
    onInitAudio()  // unlock shared AudioContext from this user gesture
    setPreviewing(voice.id)
    try {
      const ctx = getAudioCtx()
      if (ctx.state === 'suspended') await ctx.resume()

      if (previewCache.current[voice.id]) {
        const src = ctx.createBufferSource()
        src.buffer = previewCache.current[voice.id]
        src.connect(ctx.destination)
        src.start()
        src.onended = () => setPreviewing(null)
        return
      }

      const res = await fetch(`http://localhost:8100/api/voices/${voice.id}/preview`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const bytes = await res.arrayBuffer()
      const buf = await ctx.decodeAudioData(bytes)
      previewCache.current[voice.id] = buf

      const src = ctx.createBufferSource()
      src.buffer = buf
      src.connect(ctx.destination)
      src.start()
      src.onended = () => setPreviewing(null)
    } catch (err) {
      console.error('[VocalPalette] preview error:', err)
      setPreviewing(null)
    }
  }, [])

  const handleApply = () => {
    onApply(selected)
    onClose()
  }

  return (
    /* Backdrop */
    <div className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      {/* Drawer */}
      <div
        className="relative h-full w-96 bg-panel border-l border-border flex flex-col shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-border">
          <div>
            <h2 className="text-base font-bold text-white tracking-wide">VocalPalette</h2>
            <p className="text-xs text-gray-400 mt-0.5">Choose the voice texture for your avatar</p>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-surface transition-colors"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {/* Voice grid */}
        <div className="flex-1 overflow-y-auto p-4 grid grid-cols-1 gap-2">
          {loading && (
            <div className="flex items-center justify-center py-8 text-gray-400 text-sm">
              Loading voices...
            </div>
          )}
          {!loading && voices.length === 0 && (
            <div className="flex items-center justify-center py-8 text-gray-400 text-sm">
              No voices available
            </div>
          )}
          {voices.map((voice) => {
            const isSelected = voice.id === selected
            const isPlaying = previewing === voice.id

            return (
              <button
                key={voice.id}
                onClick={() => setSelected(voice.id)}
                className={`flex items-center gap-3 p-3 rounded-xl border text-left transition-all
                  ${isSelected
                    ? 'border-accent bg-accent/10'
                    : 'border-border bg-surface hover:border-accent/40'
                  }`}
              >
                {/* Gender icon */}
                <span className={`text-lg font-bold w-6 text-center flex-shrink-0 ${GENDER_COLOR[voice.gender]}`}>
                  {GENDER_ICON[voice.gender]}
                </span>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">{voice.name}</span>
                    {isSelected && (
                      <span className="text-accent text-xs">✓</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-400 truncate">{voice.description}</p>
                </div>

                {/* Preview button */}
                <button
                  onClick={(e) => { e.stopPropagation(); playPreview(voice) }}
                  disabled={isPlaying}
                  className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center transition-colors
                    ${isPlaying
                      ? 'bg-accent text-white cursor-wait'
                      : 'bg-surface border border-border text-gray-400 hover:border-accent hover:text-accent'
                    }`}
                  title={`Preview ${voice.name}`}
                >
                  {isPlaying ? (
                    <svg className="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M21 12a9 9 0 11-6.219-8.56" />
                    </svg>
                  ) : (
                    <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
                      <polygon points="5,3 19,12 5,21" />
                    </svg>
                  )}
                </button>
              </button>
            )
          })}
        </div>

        {/* Footer */}
        <div className="px-4 py-3 border-t border-border flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 py-2 rounded-xl border border-border text-sm text-gray-300 hover:bg-surface transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleApply}
            disabled={selected === activeVoiceId}
            className="flex-1 py-2 rounded-xl bg-accent text-white text-sm font-medium disabled:opacity-40 hover:bg-accent/90 transition-colors"
          >
            Apply Voice
          </button>
        </div>
      </div>
    </div>
  )
}
