import { useEffect, useState } from 'react'
import { client } from '../api/client'

interface Props {
  path: string
  onClose: () => void
}

export default function FileViewer({ path, onClose }: Props): JSX.Element {
  const [content, setContent] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    client
      .readFile(path)
      .then((res) => {
        if (!cancelled) setContent(res.content)
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
  }, [path])

  const lines = content.split('\n')

  return (
    <div className="file-viewer">
      <div className="file-viewer-header">
        <span className="file-viewer-path" title={path}>
          📄 {path}
        </span>
        <button className="pill" onClick={onClose} title="Close viewer">
          ✕ Close
        </button>
      </div>
      <div className="file-viewer-body">
        {loading && <p className="empty-hint">Loading…</p>}
        {error && <p className="empty-hint">⚠️ {error}</p>}
        {!loading && !error && (
          <pre className="code-viewer">
            <div className="gutter" aria-hidden="true">
              {lines.map((_, i) => (
                <span key={i}>{i + 1}</span>
              ))}
            </div>
            <code className="code-lines">{content}</code>
          </pre>
        )}
      </div>
    </div>
  )
}
