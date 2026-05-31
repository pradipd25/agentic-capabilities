import { useEffect, useRef, useState } from 'react'
import { useConversationStore } from '../../store/conversationStore'

interface Props {
  onSendText: (text: string) => void
}

export function ChatPanel({ onSendText }: Props) {
  const { transcript, currentToken, isSpeaking } = useConversationStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [transcript, currentToken])

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
