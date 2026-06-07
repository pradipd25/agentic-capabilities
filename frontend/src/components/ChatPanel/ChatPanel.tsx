import { useEffect, useRef, useState } from 'react'
import { useConversationStore } from '../../store/conversationStore'

interface Props {
  onSendText: (text: string) => void
  onAnswerAsk?: (id: string, value: string) => void
}

const ACTION_ICON: Record<string, string> = {
  Read: '📖', Glob: '🔎', Grep: '🔎', Edit: '✏️', Write: '📝',
  Bash: '▶️', WebSearch: '🌐', WebFetch: '🌐',
}

export function ChatPanel({ onSendText, onAnswerAsk }: Props) {
  const { transcript, currentToken, isSpeaking, actions, pendingAsk, statusText } =
    useConversationStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript, currentToken, actions, pendingAsk, statusText])

  const handleSend = () => {
    const text = input.trim()
    if (!text) return
    onSendText(text)
    setInput('')
  }

  return (
    <div className="flex flex-col h-full">
      {/* Transcript */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">
        {transcript.map((entry) => (
          <div
            key={entry.id}
            className={`flex ${entry.speaker === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2 rounded-2xl text-sm leading-relaxed
                ${entry.speaker === 'user'
                  ? 'bg-accent text-white rounded-br-sm'
                  : 'bg-panel border border-border text-gray-200 rounded-bl-sm'
                }`}
            >
              {entry.text}
            </div>
          </div>
        ))}

        {/* Agent activity — action chips (shown, never spoken) */}
        {actions.length > 0 && (
          <div className="flex flex-col gap-1.5">
            {actions.map((a) => (
              <div
                key={a.id}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-mono border w-fit max-w-[90%]
                  ${a.status === 'error'
                    ? 'bg-red-500/10 border-red-500/40 text-red-300'
                    : a.status === 'success'
                      ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                      : 'bg-surface border-border text-gray-300'
                  }`}
              >
                <span>{ACTION_ICON[a.name] ?? '🛠️'}</span>
                <span className="font-semibold">{a.name}</span>
                {a.detail && <span className="text-gray-400 truncate">{a.detail}</span>}
                {a.status === 'start' && (
                  <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse ml-1" />
                )}
                {a.status === 'success' && <span className="ml-1">✓</span>}
                {a.status === 'error' && <span className="ml-1">✗</span>}
              </div>
            ))}
          </div>
        )}

        {/* Status / heartbeat line */}
        {statusText && !currentToken && (
          <div className="text-xs text-gray-500 italic px-1">{statusText}</div>
        )}

        {/* Streaming assistant response */}
        {currentToken && (
          <div className="flex justify-start">
            <div className="max-w-[80%] px-4 py-2 rounded-2xl rounded-bl-sm text-sm leading-relaxed bg-panel border border-border text-gray-200">
              {currentToken}
              <span className="inline-block w-1 h-4 ml-1 bg-accent animate-pulse align-middle" />
            </div>
          </div>
        )}

        {/* Thinking indicator */}
        {isSpeaking && !currentToken && (
          <div className="flex justify-start">
            <div className="px-4 py-2 rounded-2xl rounded-bl-sm bg-panel border border-border">
              <span className="flex gap-1">
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className="w-2 h-2 rounded-full bg-accent animate-bounce"
                    style={{ animationDelay: `${i * 0.15}s` }}
                  />
                ))}
              </span>
            </div>
          </div>
        )}

        {/* Clarification / approval request from the agent */}
        {pendingAsk && (
          <div className="flex flex-col gap-2 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/40">
            <div className="text-sm text-amber-100">{pendingAsk.question}</div>
            <div className="flex flex-wrap gap-2">
              {(pendingAsk.options ?? (pendingAsk.kind === 'approve' ? ['Yes', 'No'] : [])).map(
                (opt) => (
                  <button
                    key={opt}
                    onClick={() => onAnswerAsk?.(pendingAsk.id, opt)}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-amber-500/20 border border-amber-500/50 text-amber-100 hover:bg-amber-500/30 transition-colors"
                  >
                    {opt}
                  </button>
                ),
              )}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Type a message..."
            className="flex-1 bg-surface border border-border rounded-xl px-4 py-2 text-sm text-gray-200 placeholder-gray-500 outline-none focus:border-accent transition-colors"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim()}
            className="px-4 py-2 bg-accent text-white rounded-xl text-sm font-medium disabled:opacity-40 hover:bg-accent/90 transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}
