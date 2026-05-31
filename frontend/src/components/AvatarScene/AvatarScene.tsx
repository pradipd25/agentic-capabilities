import { Canvas } from '@react-three/fiber'
import { Environment, OrbitControls } from '@react-three/drei'
import { Suspense } from 'react'
import { AvatarModel } from './AvatarModel'
import { useConversationStore } from '../../store/conversationStore'

export function AvatarScene() {
  const animation = useConversationStore((s) => s.animation)
  const avatar = useConversationStore((s) => s.avatar)

  return (
    <div className="w-full h-full rounded-2xl overflow-hidden bg-gradient-to-b from-panel to-surface">
      <Canvas
        camera={{ position: [0, 1.5, 7], fov: 50 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.6} />
        <directionalLight position={[2, 4, 2]} intensity={1.2} castShadow />
        <pointLight position={[-2, 2, -2]} intensity={0.4} color="#6366f1" />

        <Suspense fallback={null}>
          {avatar && (
            <AvatarModel
              modelUrl={`http://localhost:8100${avatar.model_url}`}
              animation={animation}
            />
          )}
          <Environment preset="city" />
        </Suspense>

        <OrbitControls
          enablePan={false}
          enableZoom={false}
          minPolarAngle={Math.PI / 4}
          maxPolarAngle={Math.PI / 2}
          target={[0, 1.5, 0]}
        />
      </Canvas>
    </div>
  )
}
