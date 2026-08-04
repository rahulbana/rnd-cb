import { useState } from 'react'
import type { Conversation } from '../../../shared/types'
import FileTree from './FileTree'

interface Props {
  conversations: Conversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
  onDelete: (id: string) => void
  // File explorer
  onOpenFile: (path: string) => void
  selectedFilePath: string | null
  filesReloadToken: string
  onRefreshFiles: () => void
}

type Tab = 'chats' | 'files'

export default function Sidebar(props: Props): JSX.Element {
  const [tab, setTab] = useState<Tab>('chats')

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <span className="logo">⌘ RND CB</span>
      </div>

      <div className="sidebar-tabs">
        <button className={`tab ${tab === 'chats' ? 'active' : ''}`} onClick={() => setTab('chats')}>
          💬 Chats
        </button>
        <button className={`tab ${tab === 'files' ? 'active' : ''}`} onClick={() => setTab('files')}>
          📁 Files
        </button>
      </div>

      {tab === 'chats' ? (
        <ChatsPanel {...props} />
      ) : (
        <FilesPanel
          onOpenFile={props.onOpenFile}
          selectedFilePath={props.selectedFilePath}
          filesReloadToken={props.filesReloadToken}
          onRefreshFiles={props.onRefreshFiles}
        />
      )}

      <div className="sidebar-footer">Powered by OpenAI</div>
    </aside>
  )
}

function ChatsPanel({ conversations, activeId, onSelect, onNew, onDelete }: Props): JSX.Element {
  return (
    <>
      <div className="panel-actions">
        <button className="btn-new" onClick={onNew} title="New conversation">
          + New chat
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
    </>
  )
}

function FilesPanel({
  onOpenFile,
  selectedFilePath,
  filesReloadToken,
  onRefreshFiles
}: Pick<Props, 'onOpenFile' | 'selectedFilePath' | 'filesReloadToken' | 'onRefreshFiles'>): JSX.Element {
  return (
    <>
      <div className="panel-actions">
        <button className="btn-new subtle" onClick={onRefreshFiles} title="Refresh file tree">
          ↻ Refresh
        </button>
      </div>
      <div className="conversation-list">
        <FileTree reloadToken={filesReloadToken} selectedPath={selectedFilePath} onOpenFile={onOpenFile} />
      </div>
    </>
  )
}
