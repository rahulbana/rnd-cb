import type { Conversation } from '../../../shared/types'

interface Props {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
}

export default function Sidebar({ conversations, activeId, onSelect, onNew, onDelete }: Props): JSX.Element {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="logo">⌘ RND CB</span>
        <button className="btn-new" onClick={onNew} title="New conversation">
          + New
        </button>
      </div>
      <div className="conversation-list">
        {conversations.length === 0 && <p className="empty-hint">No conversations yet.</p>}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`conversation-item ${c.id === activeId ? 'active' : ''}`}
            onClick={() => onSelect(c.id)}
          >
            <span className="conversation-title">{c.title}</span>
            <button
              className="btn-delete"
              title="Delete"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(c.id)
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <div className="sidebar-footer">Powered by OpenAI</div>
    </aside>
  )
}
