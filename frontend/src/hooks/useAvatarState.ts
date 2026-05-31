import { useEffect, useRef } from 'react'
import type { AnimationName } from '../types/protocol'

/**
 * Maps animation names to the clip names expected inside the GLB files.
 * Adjust these strings to match the actual animation track names in your GLB assets.
 */
export const ANIMATION_CLIP_MAP: Record<AnimationName, string> = {
  idle: 'Idle',
  listening: 'Standing',
  thinking: 'Sitting',
  talking: 'Wave',
  greeting: 'Wave',
}

export function useAvatarState(
  animationName: AnimationName,
  actionsRef: React.MutableRefObject<Record<string, { play: () => void; stop: () => void; fadeIn: (d: number) => void; fadeOut: (d: number) => void } | undefined>>,
) {
  const currentRef = useRef<string | null>(null)

  useEffect(() => {
    const clipName = ANIMATION_CLIP_MAP[animationName] ?? 'Idle'
    if (clipName === currentRef.current) return

    const prev = currentRef.current ? actionsRef.current[currentRef.current] : null
    const next = actionsRef.current[clipName]

    prev?.fadeOut(0.3)
    next?.fadeIn(0.3)
    next?.play()

    currentRef.current = clipName
  }, [animationName, actionsRef])
}
