import { useCallback, useEffect, useState } from 'react'
import type { FileEntry } from '../../../shared/types'
import { client } from '../api/client'

interface Props {
  reloadToken: string
  selectedPath: string | null
  onOpenFile: (path: string) => void
}

export default function FileTree({ reloadToken, selectedPath, onOpenFile }: Props): JSX.Element {
  const [roots, setRoots] = useState<FileEntry[]>([])
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    client
      .listFiles('.')
      .then((entries) => {
        if (!cancelled) setRoots(entries)
      })
      .catch((e) => {
        if (!cancelled) setError(String(e.message ?? e))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [reloadToken])

  if (loading) return <p className="empty-hint">Loading files…</p>
  if (error) return <p className="empty-hint">⚠️ {error}</p>
  if (roots.length === 0) return <p className="empty-hint">(empty directory)</p>

  return (
    <div className="file-tree">
      {roots.map((entry) => (
        <TreeNode
          key={`${reloadToken}:${entry.path}`}
          entry={entry}
          depth={0}
          selectedPath={selectedPath}
          onOpenFile={onOpenFile}
        />
      ))}
    </div>
  )
}

interface NodeProps {
  entry: FileEntry
  depth: number
  selectedPath: string | null
  onOpenFile: (path: string) => void
}

function TreeNode({ entry, depth, selectedPath, onOpenFile }: NodeProps): JSX.Element {
  const [expanded, setExpanded] = useState(false)
  const [children, setChildren] = useState<FileEntry[] | null>(null)
  const [loading, setLoading] = useState(false)

  const toggle = useCallback(async () => {
    if (entry.type === 'file') {
      onOpenFile(entry.path)
      return
    }
    const next = !expanded
    setExpanded(next)
    if (next && children === null) {
      setLoading(true)
      try {
        setChildren(await client.listFiles(entry.path))
      } catch {
        setChildren([])
      } finally {
        setLoading(false)
      }
    }
  }, [entry, expanded, children, onOpenFile])

  const isSelected = entry.type === 'file' && entry.path === selectedPath
  const icon = entry.type === 'dir' ? (expanded ? '📂' : '📁') : '📄'

  return (
    <div>
      <div
        className={`tree-row ${isSelected ? 'selected' : ''}`}
        style={{ paddingLeft: 8 + depth * 14 }}
        onClick={toggle}
        title={entry.path}
      >
        <span className="tree-icon">{icon}</span>
        <span className="tree-name">{entry.name}</span>
      </div>
      {expanded && loading && (
        <div className="empty-hint" style={{ paddingLeft: 8 + (depth + 1) * 14 }}>
          …
        </div>
      )}
      {expanded &&
        children?.map((child) => (
          <TreeNode
            key={child.path}
            entry={child}
            depth={depth + 1}
            selectedPath={selectedPath}
            onOpenFile={onOpenFile}
          />
        ))}
    </div>
  )
}
