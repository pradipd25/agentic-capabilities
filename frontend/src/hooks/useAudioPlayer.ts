import { useCallback, useRef, useState } from 'react'

// ── WAV / raw PCM decoder ───────────────────────────────────────────────────

function decodePCM(ctx: AudioContext, data: ArrayBuffer): AudioBuffer | null {
  if (data.byteLength === 0) return null
  const view = new DataView(data)

  let numChannels = 1
  let sampleRate = 24000
  let bitsPerSample = 16
  let pcmOffset = 0

  // Detect RIFF/WAV ("RIFF" = 0x52494646)
  if (data.byteLength >= 44 && view.getUint32(0, false) === 0x52494646) {
    try {
      numChannels   = view.getUint16(22, true)
      sampleRate    = view.getUint32(24, true)
      bitsPerSample = view.getUint16(34, true)
      pcmOffset     = 44
    } catch { pcmOffset = 0 }
  }

  const bytesPerSample = Math.max(1, bitsPerSample / 8)
  const pcmBytes = data.byteLength - pcmOffset
  const samplesPerChannel = Math.floor(pcmBytes / bytesPerSample / numChannels)
  if (samplesPerChannel <= 0) return null

  const buf = ctx.createBuffer(numChannels, samplesPerChannel, sampleRate)
  for (let ch = 0; ch < numChannels; ch++) {
    const channel = buf.getChannelData(ch)
    for (let i = 0; i < samplesPerChannel; i++) {
      const offset = pcmOffset + (i * numChannels + ch) * bytesPerSample
      if (bitsPerSample === 16)       channel[i] = view.getInt16(offset, true) / 32768
      else if (bitsPerSample === 32)  channel[i] = view.getInt32(offset, true) / 2147483648
      else                            channel[i] = (view.getUint8(offset) - 128) / 128
    }
  }
  return buf
}

// ── Hook ────────────────────────────────────────────────────────────────────

export function useAudioPlayer() {
  const ctxRef      = useRef<AudioContext | null>(null)
  const nextTimeRef = useRef(0)
  const [audioReady, setAudioReady] = useState(false)
  const [lastError, setLastError] = useState<string | null>(null)
  const [chunksPlayed, setChunksPlayed] = useState(0)

  /**
   * MUST be called inside a click/keydown handler.
   * Creates (or resumes) the AudioContext while we're in a user-gesture frame.
   */
  const initAudio = useCallback(async () => {
    try {
      if (!ctxRef.current || ctxRef.current.state === 'closed') {
        ctxRef.current = new AudioContext()
        nextTimeRef.current = 0
      }
      if (ctxRef.current.state === 'suspended') {
        await ctxRef.current.resume()
      }
      setAudioReady(ctxRef.current.state === 'running')
      setLastError(null)
      console.log('[Audio] context ready, state =', ctxRef.current.state)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setLastError(msg)
      console.error('[Audio] initAudio failed:', e)
    }
  }, [])

  const scheduleBuffer = useCallback((ctx: AudioContext, audioBuf: AudioBuffer) => {
    const source = ctx.createBufferSource()
    source.buffer = audioBuf
    source.connect(ctx.destination)
    const startAt = Math.max(ctx.currentTime + 0.04, nextTimeRef.current)
    source.start(startAt)
    nextTimeRef.current = startAt + audioBuf.duration
  }, [])

  const playChunk = useCallback(async (data: ArrayBuffer) => {
    if (!ctxRef.current || ctxRef.current.state === 'closed') {
      console.warn('[Audio] no AudioContext yet — call initAudio() on user gesture first')
      return
    }
    const ctx = ctxRef.current

    if (ctx.state === 'suspended') {
      console.warn('[Audio] context suspended at playChunk time — attempting resume')
      try { await ctx.resume() } catch (e) { console.error('[Audio] resume failed:', e); return }
    }

    if (ctx.state !== 'running') {
      console.warn('[Audio] context not running, state =', ctx.state)
      return
    }

    if (data.byteLength === 0) return

    // Try native decode (handles WAV, MP3, OGG, etc.)
    try {
      const decoded = await ctx.decodeAudioData(data.slice(0))
      scheduleBuffer(ctx, decoded)
      setChunksPlayed(c => c + 1)
      return
    } catch (nativeErr) {
      console.warn('[Audio] decodeAudioData failed, falling back to manual PCM decode:', nativeErr)
    }

    // Manual s16le / WAV fallback
    const decoded = decodePCM(ctx, data)
    if (decoded) {
      scheduleBuffer(ctx, decoded)
      setChunksPlayed(c => c + 1)
    } else {
      const msg = `Could not decode ${data.byteLength}-byte chunk`
      setLastError(msg)
      console.error('[Audio]', msg)
    }
  }, [scheduleBuffer])

  const stop = useCallback(() => {
    ctxRef.current?.close()
    ctxRef.current = null
    nextTimeRef.current = 0
    setAudioReady(false)
    setChunksPlayed(0)
  }, [])

  return { playChunk, initAudio, stop, audioReady, lastError, chunksPlayed }
}
