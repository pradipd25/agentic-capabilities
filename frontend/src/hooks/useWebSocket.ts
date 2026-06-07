import { useCallback, useEffect, useRef } from 'react'
import { useConversationStore } from '../store/conversationStore'
import type { ServerMessage, TranscriptEntry } from '../types/protocol'

const WS_BASE = `ws://localhost:8100/ws`

export function useWebSocket(
  sessionId: string,
  voiceId: string,
  onAudioChunk?: (data: ArrayBuffer) => void,
  onVoiceConfirmed?: (confirmedVoiceId: string) => void,
) {
  const wsRef = useRef<WebSocket | null>(null)
  const store = useConversationStore()
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  const onAudioChunkRef = useRef(onAudioChunk)
  onAudioChunkRef.current = onAudioChunk
  const onVoiceConfirmedRef = useRef(onVoiceConfirmed)
  onVoiceConfirmedRef.current = onVoiceConfirmed

  // Keep latest voiceId accessible inside the stable connect closure
  const voiceIdRef = useRef(voiceId)
  voiceIdRef.current = voiceId

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const url = `${WS_BASE}/${sessionId}?voice_id=${encodeURIComponent(voiceIdRef.current)}`
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.binaryType = 'arraybuffer'

    ws.onopen = () => store.setConnected(true)

    ws.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        onAudioChunkRef.current?.(event.data)
        return
      }

      if (typeof event.data === 'string') {
        const msg = JSON.parse(event.data) as ServerMessage

        switch (msg.type) {
          case 'session_ready':
            store.setSession(
              msg.session_id,
              msg.avatar,
              msg.available_avatars,
              msg.voice_id,
            )
            // Sync localStorage if the server corrected the voice (e.g. invalid ID fallback)
            onVoiceConfirmedRef.current?.(msg.voice_id)
            break

          case 'avatar_state':
            store.setAnimation(msg.animation, msg.speaking)
            if (msg.audio_level !== undefined) store.setAudioLevel(msg.audio_level)
            break

          // finalized conversational line (v0 + v0.1 names)
          case 'transcript_final':
          case 'transcript': {
            const entry: TranscriptEntry = {
              id: crypto.randomUUID(),
              speaker: msg.speaker,
              text: msg.text,
              timestamp: Date.now(),
            }
            store.addTranscriptEntry(entry)
            break
          }

          // streamed conversational text (v0 llm_token / v0.1 speak_delta)
          case 'llm_token':
            store.appendToken(msg.token)
            break

          case 'speak_delta':
            store.appendToken(msg.text)
            break

          // end of turn (v0 llm_done / v0.1 done)
          case 'llm_done':
          case 'done':
            store.finalizeToken()
            break

          // agent activity — shown, never spoken
          case 'think':
            store.setAnimation('thinking', false)
            if (msg.text) store.setStatus(msg.text)
            break

          case 'action':
            store.upsertAction({
              id: msg.id ?? crypto.randomUUID(),
              name: msg.name,
              detail: msg.detail,
              status: msg.status ?? 'start',
            })
            break

          case 'ask':
            store.setAsk({
              id: msg.id,
              question: msg.question,
              kind: msg.kind ?? 'clarify',
              options: msg.options,
            })
            break

          case 'status':
            store.setStatus(msg.text ?? '')
            break

          case 'avatar_changed':
            store.setAvatar(msg.avatar)
            break

          // voice swap (v0 voice_change_ack / v0.1 voice_changed)
          case 'voice_change_ack':
          case 'voice_changed':
            if (msg.reconnect_required) {
              // Close and reconnect — connect() will pick up the new voiceId from the ref
              ws.close()
            }
            break
        }
      }
    }

    ws.onclose = () => {
      store.setConnected(false)
      reconnectTimer.current = setTimeout(connect, 1000)
    }

    ws.onerror = () => ws.close()
  }, [sessionId])

  useEffect(() => {
    connect()
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [connect])

  const sendBinary = useCallback((data: ArrayBuffer) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(data)
    }
  }, [])

  const sendText = useCallback((payload: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    }
  }, [])

  const reconnectWithVoice = useCallback((newVoiceId: string) => {
    voiceIdRef.current = newVoiceId
    wsRef.current?.close()
  }, [])

  return { sendBinary, sendText, reconnectWithVoice }
}
