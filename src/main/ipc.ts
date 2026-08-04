import { BrowserWindow, dialog, ipcMain } from 'electron'
import type {
  AgentEvent,
  ApprovalRequest,
  ApprovalResponse,
  PermissionMode,
  RunAgentRequest
} from '../shared/types'
import {
  createConversation,
  deleteConversation,
  getMessages,
  listConversations,
  addMessage
} from './db/repository'
import { AgentRunner } from './openai/agent'
import { getState, setModel, setPermissionMode, setProjectPath, toAppSettings } from './settings'

const runner = new AgentRunner()

// Pending approval requests keyed by request id.
const pendingApprovals = new Map<string, (approved: boolean) => void>()

export function registerIpc(getWindow: () => BrowserWindow | null): void {
  const send = (channel: string, payload: unknown): void => {
    getWindow()?.webContents.send(channel, payload)
  }

  ipcMain.handle('settings:get', () => toAppSettings())

  ipcMain.handle('settings:setModel', (_e, model: string) => {
    setModel(model)
    return toAppSettings()
  })

  ipcMain.handle('settings:setPermissionMode', (_e, mode: PermissionMode) => {
    setPermissionMode(mode)
    return toAppSettings()
  })

  ipcMain.handle('dialog:chooseProjectDir', async () => {
    const win = getWindow()
    const result = await dialog.showOpenDialog(win!, { properties: ['openDirectory'] })
    if (result.canceled || result.filePaths.length === 0) return getState().projectPath
    setProjectPath(result.filePaths[0])
    return result.filePaths[0]
  })

  ipcMain.handle('conversations:list', () => listConversations())
  ipcMain.handle('messages:get', (_e, conversationId: string) => getMessages(conversationId))
  ipcMain.handle('conversations:delete', (_e, conversationId: string) => deleteConversation(conversationId))

  ipcMain.handle('agent:run', async (_e, req: RunAgentRequest) => {
    let conversationId = req.conversationId
    if (!conversationId) {
      const conv = await createConversation(getState().projectPath)
      conversationId = conv.id
      send('conversation:created', conv)
    }

    // Persist the user's message before running the loop.
    await addMessage({ conversationId, role: 'user', content: req.prompt })

    // Run asynchronously; events stream back over 'agent:event'.
    void runner.run(conversationId, {
      emit: (event: AgentEvent) => send('agent:event', event),
      requestApproval: (r: ApprovalRequest) =>
        new Promise<boolean>((resolve) => {
          pendingApprovals.set(r.id, resolve)
          send('agent:approvalRequest', r)
        })
    })

    return { conversationId }
  })

  ipcMain.handle('agent:cancel', (_e, conversationId: string) => {
    runner.cancel(conversationId)
  })

  ipcMain.on('agent:approvalResponse', (_e, res: ApprovalResponse) => {
    const resolve = pendingApprovals.get(res.id)
    if (resolve) {
      pendingApprovals.delete(res.id)
      resolve(res.approved)
    }
  })
}
