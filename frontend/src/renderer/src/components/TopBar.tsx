import type { AppSettings, PermissionMode } from '../../../shared/types'
import { client } from '../api/client'

interface Props {
  settings: AppSettings | null
  onSettingsChange: (s: AppSettings) => void
  onNewProject: () => void
}

const MODELS = ['gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-4.1-mini', 'o4-mini']

export default function TopBar({ settings, onSettingsChange, onNewProject }: Props): JSX.Element {
  if (!settings) return <div className="topbar">Loading…</div>

  const chooseDir = async (): Promise<void> => {
    const updated = await client.chooseProjectDir()
    if (updated) onSettingsChange(updated)
  }

  const setModel = async (model: string): Promise<void> => {
    onSettingsChange(await client.setModel(model))
  }

  const setMode = async (mode: PermissionMode): Promise<void> => {
    onSettingsChange(await client.setPermissionMode(mode))
  }

  const shortPath = settings.projectPath
    ? settings.projectPath.split(/[/\\]/).slice(-2).join('/')
    : 'none'

  return (
    <div className="topbar">
      <button className="pill" onClick={onNewProject} title="Create a new project">
        ＋ New project
      </button>

      <button className="pill" onClick={chooseDir} title={settings.projectPath ?? ''}>
        📁 {shortPath}
      </button>

      <select className="pill" value={settings.model} onChange={(e) => void setModel(e.target.value)}>
        {MODELS.map((m) => (
          <option key={m} value={m}>
            {m}
          </option>
        ))}
      </select>

      <select
        className="pill"
        value={settings.permissionMode}
        onChange={(e) => void setMode(e.target.value as PermissionMode)}
        title="Approval mode for file writes and shell commands"
      >
        <option value="ask">Ask before edits/commands</option>
        <option value="auto">Auto-approve</option>
      </select>

      <div className="status-badges">
        <span className={`badge ${settings.hasApiKey ? 'ok' : 'warn'}`}>
          {settings.hasApiKey ? 'API key ✓' : 'No API key'}
        </span>
        <span className={`badge ${settings.dbConnected ? 'ok' : 'muted'}`}>
          {settings.dbConnected ? 'Postgres ✓' : 'No DB (in-memory)'}
        </span>
      </div>
    </div>
  )
}
