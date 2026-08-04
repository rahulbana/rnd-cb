import type { AppSettings, PermissionMode } from '../shared/types'
import { isDbConnected } from './db/client'

interface MutableSettings {
  projectPath: string | null
  model: string
  permissionMode: PermissionMode
}

const state: MutableSettings = {
  projectPath: process.env.PROJECT_DIR || process.cwd(),
  model: process.env.OPENAI_MODEL || 'gpt-4o',
  permissionMode: (process.env.AGENT_PERMISSION_MODE as PermissionMode) === 'auto' ? 'auto' : 'ask'
}

export function getState(): MutableSettings {
  return state
}

export function setProjectPath(p: string | null): void {
  state.projectPath = p
}

export function setModel(m: string): void {
  state.model = m
}

export function setPermissionMode(mode: PermissionMode): void {
  state.permissionMode = mode
}

export function hasApiKey(): boolean {
  return Boolean(process.env.OPENAI_API_KEY)
}

export function toAppSettings(): AppSettings {
  return {
    projectPath: state.projectPath,
    model: state.model,
    permissionMode: state.permissionMode,
    hasApiKey: hasApiKey(),
    dbConnected: isDbConnected()
  }
}
