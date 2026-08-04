import { useState } from 'react'
import type { AppSettings, CreateProjectResult } from '../../../shared/types'
import { client } from '../api/client'

interface Props {
  defaultParent: string | null
  onClose: () => void
  onCreated: (settings: AppSettings) => void
}

export default function NewProjectModal({ defaultParent, onClose, onCreated }: Props): JSX.Element {
  const [parent, setParent] = useState(defaultParent ?? '')
  const [name, setName] = useState('')
  const [createVenv, setCreateVenv] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<CreateProjectResult | null>(null)

  const browse = async (): Promise<void> => {
    const dir = await client.chooseDirectory()
    if (dir) setParent(dir)
  }

  const canCreate = parent.trim().length > 0 && name.trim().length > 0 && !busy

  const create = async (): Promise<void> => {
    setBusy(true)
    setError(null)
    try {
      const res = await client.createProject(parent.trim(), name.trim(), createVenv)
      setResult(res)
      onCreated(res.settings)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  // Success screen.
  if (result) {
    return (
      <div className="modal-overlay">
        <div className="modal">
          <h3>Project created 🎉</h3>
          <p className="modal-summary">{result.projectPath}</p>
          <p className={result.venvCreated ? 'venv-ok' : 'venv-warn'}>
            {createVenv ? result.venvMessage : 'No virtual environment was created.'}
          </p>
          <div className="modal-actions">
            <button className="btn-primary" onClick={onClose}>
              Done
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="modal-overlay">
      <div className="modal">
        <h3>New project</h3>

        <label className="field-label">Location</label>
        <div className="field-row">
          <input
            className="text-input"
            placeholder="/path/to/parent/folder"
            value={parent}
            onChange={(e) => setParent(e.target.value)}
          />
          <button className="btn-secondary" onClick={browse} disabled={busy}>
            Browse…
          </button>
        </div>

        <label className="field-label">Project name</label>
        <input
          className="text-input"
          placeholder="my-awesome-app"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />

        <label className="checkbox-row">
          <input type="checkbox" checked={createVenv} onChange={(e) => setCreateVenv(e.target.checked)} />
          <span>
            Create a Python virtual environment (<code>.venv</code>) with <code>python3.12</code>
          </span>
        </label>

        {parent && name && (
          <p className="path-preview">
            Will create: <code>{parent.replace(/\/+$/, '')}/{name}</code>
          </p>
        )}
        {error && <p className="venv-warn">⚠️ {error}</p>}

        <div className="modal-actions">
          <button className="btn-secondary" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button className="btn-primary" onClick={create} disabled={!canCreate}>
            {busy ? 'Creating…' : 'Create project'}
          </button>
        </div>
      </div>
    </div>
  )
}
