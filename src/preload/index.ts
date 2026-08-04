import { contextBridge, ipcRenderer } from 'electron'
import type {
  AgentEvent,
  ApprovalRequest,
  ApprovalResponse,
  AppSettings,
  ChatMessage,
  Conversation,
  PermissionMode,
  RendererApi,
  RunAgentRequest
} from '../shared/types'

const api: RendererApi = {
  getSettings: () => ipcRenderer.invoke('settings:get') as Promise<AppSettings>,
  setModel: (model) => ipcRenderer.invoke('settings:setModel', model) as Promise<AppSettings>,
  setPermissionMode: (mode: PermissionMode) =>
    ipcRenderer.invoke('settings:setPermissionMode', mode) as Promise<AppSettings>,
  chooseProjectDir: () => ipcRenderer.invoke('dialog:chooseProjectDir') as Promise<string | null>,

  listConversations: () => ipcRenderer.invoke('conversations:list') as Promise<Conversation[]>,
  getMessages: (id) => ipcRenderer.invoke('messages:get', id) as Promise<ChatMessage[]>,
  deleteConversation: (id) => ipcRenderer.invoke('conversations:delete', id) as Promise<void>,

  runAgent: (req: RunAgentRequest) =>
    ipcRenderer.invoke('agent:run', req) as Promise<{ conversationId: string }>,
  cancelAgent: (id) => ipcRenderer.invoke('agent:cancel', id) as Promise<void>,
  respondApproval: (res: ApprovalResponse) => ipcRenderer.send('agent:approvalResponse', res),

  onAgentEvent: (cb: (e: AgentEvent) => void) => {
    const listener = (_e: unknown, payload: AgentEvent): void => cb(payload)
    ipcRenderer.on('agent:event', listener)
    return () => ipcRenderer.removeListener('agent:event', listener)
  },
  onApprovalRequest: (cb: (r: ApprovalRequest) => void) => {
    const listener = (_e: unknown, payload: ApprovalRequest): void => cb(payload)
    ipcRenderer.on('agent:approvalRequest', listener)
    return () => ipcRenderer.removeListener('agent:approvalRequest', listener)
  },
  onConversationCreated: (cb: (c: Conversation) => void) => {
    const listener = (_e: unknown, payload: Conversation): void => cb(payload)
    ipcRenderer.on('conversation:created', listener)
    return () => ipcRenderer.removeListener('conversation:created', listener)
  }
}

contextBridge.exposeInMainWorld('api', api)
