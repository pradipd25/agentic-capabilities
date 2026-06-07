/**
 * Agent Face — TypeScript client SDK.
 *
 * A framework-agnostic client for the Presence Protocol over a WebSocket
 * transport. It sends `ControlMessage`s (user turns, interrupt, ask-response,
 * avatar/voice changes) and dispatches incoming `PresenceEvent`s plus binary TTS
 * audio. The `<agent-face>` web component and custom web apps build on this.
 *
 * NOTE: the protocol import is a relative path into the in-repo package; the
 * monorepo build will replace it with the published name `@agent-face/presence-protocol`.
 */

import type { ControlMessage, PresenceEvent } from '../../presence-protocol/typescript/index'

export type { ControlMessage, PresenceEvent } from '../../presence-protocol/typescript/index'

export type PresenceHandler = (event: PresenceEvent) => void
export type AudioHandler = (chunk: ArrayBuffer) => void

export interface AgentFaceClientOptions {
  /** WebSocket base, e.g. `ws://localhost:8100/ws` */
  url: string
  sessionId: string
  voiceId?: string
  /** Auto-reconnect on close (default true). */
  reconnect?: boolean
  /** Reconnect delay in ms (default 1000). */
  reconnectDelayMs?: number
  onEvent?: PresenceHandler
  onAudio?: AudioHandler
  onOpen?: () => void
  onClose?: () => void
}

/**
 * Connects to a Presence Protocol transport and exposes typed send helpers.
 */
export class AgentFaceClient {
  private ws: WebSocket | null = null
  private handlers = new Set<PresenceHandler>()
  private reconnectTimer: ReturnType<typeof setTimeout> | undefined
  private closedByUser = false
  private voiceId: string | undefined

  constructor(private readonly opts: AgentFaceClientOptions) {
    this.voiceId = opts.voiceId
    if (opts.onEvent) this.handlers.add(opts.onEvent)
  }

  /** Open the connection. Safe to call once. */
  connect(): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return
    this.closedByUser = false

    const q = this.voiceId ? `?voice_id=${encodeURIComponent(this.voiceId)}` : ''
    const url = `${this.opts.url}/${this.opts.sessionId}${q}`
    const ws = new WebSocket(url)
    ws.binaryType = 'arraybuffer'
    this.ws = ws

    ws.onopen = () => this.opts.onOpen?.()

    ws.onmessage = (ev: MessageEvent) => {
      if (ev.data instanceof ArrayBuffer) {
        this.opts.onAudio?.(ev.data)
        return
      }
      if (typeof ev.data === 'string') {
        let parsed: unknown
        try {
          parsed = JSON.parse(ev.data)
        } catch {
          return
        }
        const event = parsed as PresenceEvent
        // track voice changes so reconnects keep the latest voice
        if (event.type === 'voice_changed' && event.voice_id) {
          this.voiceId = event.voice_id
        }
        this.handlers.forEach((h) => h(event))
      }
    }

    ws.onclose = () => {
      this.opts.onClose?.()
      const shouldReconnect = (this.opts.reconnect ?? true) && !this.closedByUser
      if (shouldReconnect) {
        this.reconnectTimer = setTimeout(() => this.connect(), this.opts.reconnectDelayMs ?? 1000)
      }
    }

    ws.onerror = () => ws.close()
  }

  /** Subscribe to presence events. Returns an unsubscribe function. */
  on(handler: PresenceHandler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  /** Send a raw upstream control message. */
  send(message: ControlMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ session_id: this.opts.sessionId, ...message }))
    }
  }

  /** Send raw binary (e.g. mic PCM) to the transport. */
  sendBinary(data: ArrayBuffer): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data)
    }
  }

  userTurn(text: string): void {
    this.send({ type: 'user_turn', text })
  }

  interrupt(): void {
    this.send({ type: 'interrupt' })
  }

  answerAsk(id: string, value: string): void {
    this.send({ type: 'ask_response', id, value })
  }

  setAvatar(avatarId: string): void {
    this.send({ type: 'set_avatar', avatar_id: avatarId })
  }

  setVoice(voiceId: string): void {
    this.voiceId = voiceId
    this.send({ type: 'set_voice', voice_id: voiceId })
  }

  /** Close the connection and stop reconnecting. */
  close(): void {
    this.closedByUser = true
    clearTimeout(this.reconnectTimer)
    this.ws?.close()
    this.ws = null
  }
}
