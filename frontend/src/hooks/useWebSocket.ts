import { useCallback, useEffect, useRef } from 'react'
import { useConversationStore } from '../store/conversationStore'
import type { ServerMessage, TranscriptEntry } from '../types/protocol'

const WS_URL = `ws://localhost:8100/ws`

export function useWebSocket(sessionId: string, onAudioChunk?: (data: ArrayBuffer) => void) {
  const wsRef = useRef<WebSocket | null>(null)
  const store = useConversationStore()
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()
  const onAudioChunkRef = useRef(onAudioChunk)
  onAudioChunkRef.current = onAudioChunk

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(`${WS_URL}/${sessionId}`)
    wsRef.current = ws

    ws.onopen = () => store.setConnected(true)

    // Tell the WebSocket to deliver binary frames as ArrayBuffer (not Blob)
    ws.binaryType = 'arraybuffer'

    ws.onmessage = (event) => {
      // Binary frame = TTS audio chunk from Pipecat
      if (event.data instanceof ArrayBuffer) {
        onAudioChunkRef.current?.(event.data)
        return
      }

      if (typeof event.data === 'string') {
        const msg = JSON.parse(event.data) as ServerMessage

        switch (msg.type) {
          case 'session_ready':
            store.setSession(msg.session_id, msg.avatar, msg.available_avatars)
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
        }
      }
    }

    ws.onclose = () => {
      store.setConnected(false)
      reconnectTimer.current = setTimeout(connect, 3000)
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

  return { sendBinary, sendText }
}
