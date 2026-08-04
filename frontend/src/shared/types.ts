// Shared types used by the main process, preload bridge, and renderer.

export type Role = 'system' | 'user' | 'assistant' | 'tool'

export interface ChatMessage {
  id: string
  conversationId: string
  role: Role
  content: string
  // Present on assistant messages that requested tool calls.
  toolCalls?: ToolCallRecord[]
  // Present on tool-result messages.
  toolCallId?: string
  name?: string
  createdAt: string
}

export interface ToolCallRecord {
  id: string
  name: string
  arguments: string // raw JSON string as returned by the model
}

export interface Conversation {
  id: string
  title: string
  projectPath: string | null
  createdAt: string
  updatedAt: string
}

// Events streamed from the agent loop to the renderer while it works.
export type AgentEvent =
  | { type: 'assistant_text'; conversationId: string; content: string }
  | { type: 'tool_call'; conversationId: string; call: ToolCallRecord }
  | { type: 'tool_result'; conversationId: string; toolCallId: string; name: string; content: string }
  | { type: 'error'; conversationId: string; message: string }
  | { type: 'done'; conversationId: string }

// Approval requests emitted for side-effecting tools when permission mode is "ask".
export interface ApprovalRequest {
  id: string
  tool: string
  summary: string
  details: string
}

export interface ApprovalResponse {
  id: string
  approved: boolean
}

export type PermissionMode = 'ask' | 'auto'

export interface AppSettings {
  projectPath: string | null
  model: string
  permissionMode: PermissionMode
  hasApiKey: boolean
  dbConnected: boolean
}

export interface FileEntry {
  name: string
  path: string
  type: 'dir' | 'file'
}

export interface CreateProjectResult {
  settings: AppSettings
  projectPath: string
  venvCreated: boolean
  venvMessage: string
}

// Bridge exposed by the Electron preload (window.desktop).
export interface DesktopBridge {
  backendUrl: string
  chooseDirectory(): Promise<string | null>
}
