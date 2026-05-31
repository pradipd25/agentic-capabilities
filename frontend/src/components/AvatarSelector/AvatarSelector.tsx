import { useConversationStore } from '../../store/conversationStore'
import type { AvatarMeta } from '../../types/protocol'

interface Props {
  onSelect: (avatar: AvatarMeta) => void
}

export function AvatarSelector({ onSelect }: Props) {
  const { availableAvatars, avatar: current } = useConversationStore()

  return (
    <div className="flex gap-3 p-4 overflow-x-auto">
      {availableAvatars.map((a) => (
        <button
          key={a.id}
          onClick={() => onSelect(a)}
          className={`flex-shrink-0 flex flex-col items-center gap-1 p-2 rounded-xl border transition-all
            ${current?.id === a.id
              ? 'border-accent bg-accent/10'
              : 'border-border bg-panel hover:border-accent/50'
            }`}
        >
          <div className="w-14 h-14 rounded-full bg-surface overflow-hidden flex items-center justify-center">
            <img
              src={`http://localhost:8100${a.thumbnail_url}`}
              alt={a.name}
              className="w-full h-full object-cover"
              onError={(e) => {
                // Show initials if thumbnail missing
                const el = e.currentTarget
                el.style.display = 'none'
                const parent = el.parentElement
                if (parent && !parent.querySelector('span')) {
                  const span = document.createElement('span')
                  span.textContent = a.name[0]
                  span.className = 'text-xl font-bold text-accent'
                  parent.appendChild(span)
                }
              }}
            />
          </div>
          <span className="text-xs text-gray-300 font-medium">{a.name}</span>
        </button>
      ))}
    </div>
  )
}
