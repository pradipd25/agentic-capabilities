import { useCallback, useRef, useState } from 'react'

const SAMPLE_RATE = 16000

export function useAudioCapture(onChunk: (data: ArrayBuffer) => void) {
  const [isCapturing, setIsCapturing] = useState(false)
  const contextRef = useRef<AudioContext | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)

  const start = useCallback(async () => {
    if (isCapturing) return
    // Enable the browser's built-in acoustic echo cancellation so the avatar's
    // TTS coming out of the speakers is removed from the mic input. This is what
    // lets the mic stay open while the avatar talks (for voice barge-in /
    // language switching) without the bot's own voice triggering the VAD.
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
      video: false,
    })
    streamRef.current = stream

    const ctx = new AudioContext({ sampleRate: SAMPLE_RATE })
    contextRef.current = ctx

    const source = ctx.createMediaStreamSource(stream)
    // ScriptProcessorNode works everywhere without a separate worklet file.
    // 1024 samples @ 16 kHz = 64 ms/chunk. Finer than the old 4096 (256 ms) so
    // the barge-in energy gate can require several *consecutive* loud chunks of
    // real speech before interrupting, instead of tripping on a single loud TTS
    // syllable's echo averaged over a long window.
    const processor = ctx.createScriptProcessor(1024, 1, 1)
    processorRef.current = processor

    processor.onaudioprocess = (e) => {
      const float32 = e.inputBuffer.getChannelData(0)
      // Convert float32 → int16 PCM
      const int16 = new Int16Array(float32.length)
      for (let i = 0; i < float32.length; i++) {
        const s = Math.max(-1, Math.min(1, float32[i]))
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
      }
      onChunk(int16.buffer)
    }

    source.connect(processor)
    processor.connect(ctx.destination)
    setIsCapturing(true)
  }, [isCapturing, onChunk])

  const stop = useCallback(() => {
    processorRef.current?.disconnect()
    processorRef.current = null
    contextRef.current?.close()
    contextRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    setIsCapturing(false)
  }, [])

  return { isCapturing, start, stop }
}
