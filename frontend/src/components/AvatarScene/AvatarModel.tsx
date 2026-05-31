import { useAnimations, useGLTF } from '@react-three/drei'
import { useEffect, useRef } from 'react'
import type { Group } from 'three'
import type { AnimationName } from '../../types/protocol'
import { ANIMATION_CLIP_MAP } from '../../hooks/useAvatarState'

interface Props {
  modelUrl: string
  animation: AnimationName
}

export function AvatarModel({ modelUrl, animation }: Props) {
  const group = useRef<Group>(null)
  const { scene, animations } = useGLTF(modelUrl)
  const { actions } = useAnimations(animations, group)
  const currentRef = useRef<string | null>(null)

  // Play the correct animation clip when animation state changes
  useEffect(() => {
    const clipName = ANIMATION_CLIP_MAP[animation] ?? 'Idle'

    // Find a case-insensitive match in case clip naming varies
    const matchedKey = Object.keys(actions).find(
      (k) => k.toLowerCase() === clipName.toLowerCase()
    ) ?? Object.keys(actions)[0]

    if (!matchedKey || matchedKey === currentRef.current) return

    const prev = currentRef.current ? actions[currentRef.current] : null
    const next = actions[matchedKey]

    prev?.fadeOut(0.3)
    next?.reset()
    next?.fadeIn(0.3)
    next?.play()

    currentRef.current = matchedKey
  }, [animation, actions])

  // Play first available animation on mount
  useEffect(() => {
    const firstKey = Object.keys(actions)[0]
    if (firstKey && !currentRef.current) {
      actions[firstKey]?.play()
      currentRef.current = firstKey
    }
  }, [actions])

  return (
    <group ref={group} position={[0, -1, 0]}>
      <primitive object={scene} />
    </group>
  )
}
