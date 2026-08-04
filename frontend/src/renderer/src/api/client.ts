import type {
  AgentEvent,
  AppSettings,
  ApprovalRequest,
  ApprovalResponse,
  ChatMessage,
  Conversation,
  CreateProjectResult,
  FileEntry,
  PermissionMode
} from '../../../shared/types'

const httpBase = window.desktop?.backendUrl || 'http://127.0.0.1:8000'
const wsUrl = httpBase.replace(/^http/, 'ws') + '/ws/agent'

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${httpBase}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${path}`)
  return res.json() as Promise<T>
}

type EventHandler = (e: AgentEvent) => void
type ApprovalHandler = (r: ApprovalRequest) => void
type CreatedHandler = (c: Conversation) => void

class BackendClient {
  private ws: WebSocket | null = null
  private connecting: Promise<void> | null = null
  private queue: string[] = []

  private eventHandlers = new Set<EventHandler>()
  private approvalHandlers = new Set<ApprovalHandler>()
  private createdHandlers = new Set<CreatedHandler>()

  // ---------------- REST ----------------
  getSettings(): Promise<AppSettings> {
    return req<AppSettings>('/api/settings')
  }

  setModel(model: string): Promise<AppSettings> {
    return req<AppSettings>('/api/settings/model', { method: 'POST', body: JSON.stringify({ model }) })
  }

  setPermissionMode(mode: PermissionMode): Promise<AppSettings> {
    return req<AppSettings>('/api/settings/permission-mode', {
      method: 'POST',
      body: JSON.stringify({ mode })
    })
  }

  async chooseProjectDir(): Promise<AppSettings | null> {
    const path = await window.desktop.chooseDirectory()
    if (!path) return null
    return req<AppSettings>('/api/settings/project-path', {
      method: 'POST',
      body: JSON.stringify({ path })
    })
  }

  chooseDirectory(): Promise<string | null> {
    return window.desktop.chooseDirectory()
  }

  createProject(parentPath: string, name: string, createVenv: boolean): Promise<CreateProjectResult> {
    return req<CreateProjectResult>('/api/projects/create', {
      method: 'POST',
      body: JSON.stringify({ parentPath, name, createVenv })
    })
  }

  listFiles(path = '.'): Promise<FileEntry[]> {
    return req<FileEntry[]>(`/api/files?path=${encodeURIComponent(path)}`)
  }

  readFile(path: string): Promise<{ path: string; content: string }> {
    return req<{ path: string; content: string }>(`/api/file?path=${encodeURIComponent(path)}`)
  }

  listConversations(): Promise<Conversation[]> {
    return req<Conversation[]>('/api/conversations')
  }

  getMessages(conversationId: string): Promise<ChatMessage[]> {
    return req<ChatMessage[]>(`/api/conversations/${conversationId}/messages`)
  }

  async deleteConversation(conversationId: string): Promise<void> {
    await req(`/api/conversations/${conversationId}`, { method: 'DELETE' })
  }

  // ---------------- WebSocket ----------------
  private ensureSocket(): Promise<void> {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) return Promise.resolve()
    if (this.connecting) return this.connecting

    this.connecting = new Promise<void>((resolve) => {
      const socket = new WebSocket(wsUrl)
      this.ws = socket

      socket.onopen = () => {
        this.connecting = null
        for (const msg of this.queue) socket.send(msg)
        this.queue = []
        resolve()
      }
      socket.onmessage = (ev) => this.dispatch(JSON.parse(ev.data))
      socket.onclose = () => {
        this.ws = null
        this.connecting = null
      }
      socket.onerror = () => {
        // onclose will follow; nothing else to do.
      }
    })
    return this.connecting
  }

  private dispatch(data: Record<string, unknown>): void {
    const type = data.type as string
    if (type === 'approval_request') {
      this.approvalHandlers.forEach((h) => h(data as unknown as ApprovalRequest))
    } else if (type === 'conversation_created') {
      this.createdHandlers.forEach((h) => h(data.conversation as Conversation))
    } else {
      this.eventHandlers.forEach((h) => h(data as unknown as AgentEvent))
    }
  }

  private send(payload: object): void {
    const msg = JSON.stringify(payload)
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(msg)
    } else {
      this.queue.push(msg)
      void this.ensureSocket()
    }
  }

  async run(conversationId: string | null, prompt: string): Promise<void> {
    await this.ensureSocket()
    this.send({ type: 'run', conversationId, prompt })
  }

  cancel(conversationId: string): void {
    this.send({ type: 'cancel', conversationId })
  }

  respondApproval(res: ApprovalResponse): void {
    this.send({ type: 'approval', id: res.id, approved: res.approved })
  }

  onAgentEvent(cb: EventHandler): () => void {
    this.eventHandlers.add(cb)
    void this.ensureSocket()
    return () => this.eventHandlers.delete(cb)
  }

  onApprovalRequest(cb: ApprovalHandler): () => void {
    this.approvalHandlers.add(cb)
    return () => this.approvalHandlers.delete(cb)
  }

  onConversationCreated(cb: CreatedHandler): () => void {
    this.createdHandlers.add(cb)
    return () => this.createdHandlers.delete(cb)
  }
}

export const client = new BackendClient()
