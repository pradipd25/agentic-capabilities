/**
 * `<agent-face>` — an embeddable custom element that gives any agent a face.
 *
 * Drop-in usage:
 *   <agent-face url="ws://localhost:8100/ws" session="abc123" voice="nova" controls></agent-face>
 *
 * It connects via the Agent Face SDK, plays TTS audio, and renders the protocol's
 * presence layer: speaking state, streamed speech, action chips (shown, never
 * spoken), status line, and clarify/approve prompts. This is the lightweight
 * embeddable surface; the full 3D renderer is the reference `frontend/` app. Host
 * apps can also listen for `agentface:event` CustomEvents and call `sendUserTurn`.
 *
 * NOTE: the SDK import is a relative path into the in-repo package; the monorepo
 * build will replace it with the published name `@agent-face/sdk`.
 */

import { AgentFaceClient, type PresenceEvent } from '../../sdk-ts/src/index'

const TEMPLATE = `
  <style>
    :host { display: block; font-family: system-ui, sans-serif; color: #e5e7eb; }
    .wrap { display: flex; flex-direction: column; gap: 8px; background: #0b0e14;
      border: 1px solid #1f2733; border-radius: 16px; padding: 16px; height: 100%; box-sizing: border-box; }
    .face { display: flex; align-items: center; gap: 10px; }
    .orb { width: 40px; height: 40px; border-radius: 50%;
      background: radial-gradient(circle at 35% 30%, #7dd3fc, #2563eb);
      box-shadow: 0 0 0 0 rgba(37,99,235,.5); transition: transform .2s; }
    .orb.speaking { animation: pulse 1s ease-in-out infinite; }
    .orb.thinking { animation: breathe 1.6s ease-in-out infinite; }
    @keyframes pulse { 0%,100%{transform:scale(1)} 50%{transform:scale(1.15); box-shadow:0 0 18px 4px rgba(37,99,235,.45)} }
    @keyframes breathe { 0%,100%{opacity:.6} 50%{opacity:1} }
    .state { font-size: 12px; color: #94a3b8; }
    .log { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 6px; min-height: 60px; }
    .line { font-size: 13px; line-height: 1.4; }
    .line.user { color: #93c5fd; text-align: right; }
    .stream { font-size: 13px; color: #e5e7eb; }
    .chip { display: inline-flex; align-items: center; gap: 6px; font: 11px/1.2 ui-monospace, monospace;
      padding: 4px 8px; border-radius: 8px; border: 1px solid #1f2733; background: #111827; width: fit-content; }
    .chip.success { border-color: #10b98155; color: #6ee7b7; }
    .chip.error { border-color: #ef444455; color: #fca5a5; }
    .status { font-size: 11px; color: #64748b; font-style: italic; }
    .ask { display: flex; flex-direction: column; gap: 6px; padding: 8px 10px;
      border: 1px solid #f59e0b66; background: #f59e0b14; border-radius: 10px; }
    .ask button { font-size: 12px; padding: 4px 10px; border-radius: 8px; cursor: pointer;
      border: 1px solid #f59e0b80; background: #f59e0b22; color: #fde68a; }
    .bar { display: flex; gap: 6px; }
    .bar input { flex: 1; background: #0f1622; border: 1px solid #1f2733; border-radius: 10px;
      padding: 6px 10px; color: #e5e7eb; outline: none; }
    .bar button { padding: 6px 12px; border-radius: 10px; border: none; background: #2563eb; color: white; cursor: pointer; }
    [hidden] { display: none !important; }
  </style>
  <div class="wrap">
    <div class="face"><div class="orb" part="orb"></div><div class="state">idle</div></div>
    <div class="log"></div>
    <div class="status" hidden></div>
    <div class="ask" hidden></div>
    <div class="bar" hidden><input type="text" placeholder="Type a message…"/><button>Send</button></div>
  </div>
`

export class AgentFaceElement extends HTMLElement {
  static get observedAttributes() {
    return ['url', 'session', 'voice', 'controls']
  }

  private client: AgentFaceClient | null = null
  private audioCtx: AudioContext | null = null
  private nextTime = 0
  private streamEl: HTMLDivElement | null = null

  private get root(): ShadowRoot {
    return this.shadowRoot as ShadowRoot
  }

  connectedCallback(): void {
    if (!this.shadowRoot) {
      this.attachShadow({ mode: 'open' })
      this.root.innerHTML = TEMPLATE
      this.wireControls()
    }
    if (this.hasAttribute('controls')) this.q('.bar')!.hidden = false
    this.start()
  }

  disconnectedCallback(): void {
    this.client?.close()
    this.client = null
  }

  /** Public API: send a user turn (e.g. from your own input). */
  sendUserTurn(text: string): void {
    this.client?.userTurn(text)
    this.addLine(text, 'user')
  }

  interrupt(): void {
    this.client?.interrupt()
  }

  private start(): void {
    const url = this.getAttribute('url') ?? 'ws://localhost:8100/ws'
    const session = this.getAttribute('session') ?? `web-${Math.random().toString(36).slice(2, 8)}`
    const voice = this.getAttribute('voice') ?? undefined

    this.client?.close()
    this.client = new AgentFaceClient({
      url,
      sessionId: session,
      voiceId: voice,
      onEvent: (e) => this.handleEvent(e),
      onAudio: (chunk) => void this.playChunk(chunk),
    })
    this.client.connect()
  }

  /** Normalize legacy v0 wire names to canonical Presence Protocol events. */
  private normalizeEvent(raw: PresenceEvent): PresenceEvent {
    const any = raw as { type: string; [k: string]: unknown }
    switch (any.type) {
      case 'llm_token':
        return { type: 'speak_delta', text: String(any.token ?? '') }
      case 'llm_done':
        return { type: 'done', full_text: any.full_text as string | undefined }
      case 'transcript_final':
        return { type: 'transcript', speaker: any.speaker as 'user' | 'assistant', text: String(any.text ?? '') }
      case 'voice_change_ack':
        return { type: 'voice_changed', voice_id: String(any.voice_id ?? ''), reconnect_required: Boolean(any.reconnect_required) }
      default:
        return raw
    }
  }

  private handleEvent(raw: PresenceEvent): void {
    this.dispatchEvent(new CustomEvent('agentface:event', { detail: raw, bubbles: true }))
    const e = this.normalizeEvent(raw)

    switch (e.type) {
      case 'avatar_state':
        this.setState(e.animation, e.speaking ?? false)
        break
      case 'speak_delta':
        this.appendStream(e.text)
        break
      case 'transcript':
        if (e.speaker === 'assistant') this.commitStream(e.text)
        else this.addLine(e.text, 'user')
        break
      case 'done':
        this.commitStream()
        this.setStatus('')
        break
      case 'think':
        this.setState('thinking', false)
        if (e.text) this.setStatus(e.text)
        break
      case 'status':
        this.setStatus(e.text ?? '')
        break
      case 'action':
        this.showAction(e.id ?? crypto.randomUUID(), e.name, e.detail, e.status ?? 'start')
        break
      case 'ask':
        this.showAsk(e.id, e.question, e.kind ?? 'clarify', e.options)
        break
    }
  }

  // ---- rendering helpers ----

  private q<T extends HTMLElement = HTMLElement>(sel: string): T | null {
    return this.root.querySelector<T>(sel)
  }

  private setState(animation: string, speaking: boolean): void {
    const orb = this.q('.orb')!
    orb.classList.toggle('speaking', speaking || animation === 'talking')
    orb.classList.toggle('thinking', animation === 'thinking')
    this.q('.state')!.textContent = animation
  }

  private addLine(text: string, who: 'user' | 'assistant'): void {
    const el = document.createElement('div')
    el.className = `line ${who}`
    el.textContent = text
    this.q('.log')!.appendChild(el)
    this.scrollLog()
  }

  private appendStream(text: string): void {
    if (!this.streamEl) {
      this.streamEl = document.createElement('div')
      this.streamEl.className = 'stream'
      this.q('.log')!.appendChild(this.streamEl)
    }
    this.streamEl.textContent = (this.streamEl.textContent ?? '') + text
    this.scrollLog()
  }

  private commitStream(finalText?: string): void {
    if (finalText) {
      if (!this.streamEl) this.appendStream('')
      this.streamEl!.textContent = finalText
    }
    if (this.streamEl) {
      this.streamEl.className = 'line assistant'
      this.streamEl = null
    }
  }

  private showAction(id: string, name: string, detail: string | undefined, status: string): void {
    let chip = this.q<HTMLDivElement>(`.chip[data-id="${id}"]`)
    if (!chip) {
      chip = document.createElement('div')
      chip.className = 'chip'
      chip.dataset.id = id
      this.q('.log')!.appendChild(chip)
    }
    chip.className = `chip ${status}`
    const mark = status === 'success' ? ' ✓' : status === 'error' ? ' ✗' : ''
    chip.textContent = `🛠️ ${name}${detail ? ' ' + detail : ''}${mark}`
    this.scrollLog()
  }

  private setStatus(text: string): void {
    const el = this.q('.status')!
    el.textContent = text
    el.hidden = !text
  }

  private showAsk(id: string, question: string, _kind: string, options?: string[]): void {
    const box = this.q('.ask')!
    box.hidden = false
    box.innerHTML = ''
    const q = document.createElement('div')
    q.textContent = question
    box.appendChild(q)
    const row = document.createElement('div')
    const opts = options && options.length ? options : ['Yes', 'No']
    for (const opt of opts) {
      const b = document.createElement('button')
      b.textContent = opt
      b.onclick = () => {
        this.client?.answerAsk(id, opt)
        box.hidden = true
        box.innerHTML = ''
      }
      row.appendChild(b)
    }
    box.appendChild(row)
  }

  private wireControls(): void {
    const input = this.q<HTMLInputElement>('.bar input')!
    const btn = this.q<HTMLButtonElement>('.bar button')!
    const send = () => {
      const t = input.value.trim()
      if (!t) return
      this.ensureAudio()
      this.sendUserTurn(t)
      input.value = ''
    }
    btn.onclick = send
    input.onkeydown = (e) => {
      if (e.key === 'Enter') send()
    }
  }

  private scrollLog(): void {
    const log = this.q('.log')!
    log.scrollTop = log.scrollHeight
  }

  // ---- audio ----

  private ensureAudio(): void {
    if (!this.audioCtx) this.audioCtx = new AudioContext()
    if (this.audioCtx.state === 'suspended') void this.audioCtx.resume()
  }

  private async playChunk(buf: ArrayBuffer): Promise<void> {
    this.ensureAudio()
    const ctx = this.audioCtx!
    try {
      const audio = await ctx.decodeAudioData(buf.slice(0))
      const src = ctx.createBufferSource()
      src.buffer = audio
      src.connect(ctx.destination)
      const t = Math.max(ctx.currentTime + 0.02, this.nextTime)
      src.start(t)
      this.nextTime = t + audio.duration
    } catch {
      // non-decodable chunk — ignore
    }
  }
}

if (typeof customElements !== 'undefined' && !customElements.get('agent-face')) {
  customElements.define('agent-face', AgentFaceElement)
}
