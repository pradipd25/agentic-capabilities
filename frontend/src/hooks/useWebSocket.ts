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

          case 'transcript_final': {
            const entry: TranscriptEntry = {
              id: crypto.randomUUID(),
              speaker: msg.speaker,
              text: msg.text,
              timestamp: Date.now(),
            }
            store.addTranscriptEntry(entry)
            break
          }

          case 'llm_token':
            store.appendToken(msg.token)
            break

          case 'llm_done':
            store.finalizeToken()
            break

          case 'avatar_changed':
            store.setAvatar(msg.avatar)
            break

          case 'voice_change_ack':
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
