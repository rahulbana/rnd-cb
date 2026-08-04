import { useCallback, useEffect, useRef, useState } from 'react'
import type {
  AgentEvent,
  AppSettings,
  ApprovalRequest,
  ChatMessage,
  Conversation
} from '../../shared/types'
import Sidebar from './components/Sidebar'
import TopBar from './components/TopBar'
import ChatView from './components/ChatView'
import Composer from './components/Composer'
import ApprovalModal from './components/ApprovalModal'
import FileViewer from './components/FileViewer'
import NewProjectModal from './components/NewProjectModal'
import { client } from './api/client'

let localSeq = 0
const localId = (): string => `local-${Date.now()}-${localSeq++}`

export default function App(): JSX.Element {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [running, setRunning] = useState(false)
  const [approval, setApproval] = useState<ApprovalRequest | null>(null)
  const [openFilePath, setOpenFilePath] = useState<string | null>(null)
  const [filesReloadToken, setFilesReloadToken] = useState('0')
  const [newProjectOpen, setNewProjectOpen] = useState(false)

  const activeIdRef = useRef<string | null>(null)
  activeIdRef.current = activeId

  const refreshConversations = useCallback(async () => {
    setConversations(await client.listConversations())
  }, [])

  // Initial load + event subscriptions (registered once).
  useEffect(() => {
    void client.getSettings().then(setSettings)
    void refreshConversations()

    const offEvent = client.onAgentEvent((e: AgentEvent) => {
      if (e.conversationId !== activeIdRef.current) return
      handleAgentEvent(e)
    })
    const offApproval = client.onApprovalRequest((r) => setApproval(r))
    const offCreated = client.onConversationCreated((c) => {
      setConversations((prev) => [c, ...prev])
      // A new conversation is only created when we started fresh; adopt it so
      // subsequent agent events (filtered by active id) are accepted.
      if (activeIdRef.current === null) {
        activeIdRef.current = c.id
        setActiveId(c.id)
      }
    })

    return () => {
      offEvent()
      offApproval()
      offCreated()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleAgentEvent(e: AgentEvent): void {
    switch (e.type) {
      case 'assistant_text':
        if (!e.content.trim()) break
        setMessages((prev) => [
          ...prev,
          { id: localId(), conversationId: e.conversationId, role: 'assistant', content: e.content, createdAt: new Date().toISOString() }
        ])
        break
      case 'tool_call':
        setMessages((prev) => [
          ...prev,
          {
            id: localId(),
            conversationId: e.conversationId,
            role: 'assistant',
            content: '',
            toolCalls: [e.call],
            createdAt: new Date().toISOString()
          }
        ])
        break
      case 'tool_result':
        setMessages((prev) => [
          ...prev,
          {
            id: localId(),
            conversationId: e.conversationId,
            role: 'tool',
            content: e.content,
            name: e.name,
            toolCallId: e.toolCallId,
            createdAt: new Date().toISOString()
          }
        ])
        break
      case 'error':
        setMessages((prev) => [
          ...prev,
          { id: localId(), conversationId: e.conversationId, role: 'assistant', content: `⚠️ Error: ${e.message}`, createdAt: new Date().toISOString() }
        ])
        break
      case 'done':
        setRunning(false)
        // Reload canonical history + refresh titles.
        if (activeIdRef.current) {
          void client.getMessages(activeIdRef.current).then(setMessages)
        }
        void refreshConversations()
        // The agent may have created or edited files — refresh the tree.
        setFilesReloadToken(String(Date.now()))
        break
    }
  }

  const selectConversation = useCallback(async (id: string) => {
    setActiveId(id)
    setMessages(await client.getMessages(id))
  }, [])

  const newConversation = useCallback(() => {
    setActiveId(null)
    setMessages([])
  }, [])

  const deleteConversation = useCallback(
    async (id: string) => {
      await client.deleteConversation(id)
      if (activeIdRef.current === id) newConversation()
      await refreshConversations()
    },
    [newConversation, refreshConversations]
  )

  const send = useCallback(
    async (prompt: string) => {
      const optimistic: ChatMessage = {
        id: localId(),
        conversationId: activeId ?? 'pending',
        role: 'user',
        content: prompt,
        createdAt: new Date().toISOString()
      }
      setMessages((prev) => [...prev, optimistic])
      setRunning(true)
      // For an existing conversation the active id is already correct; for a
      // new one, the backend emits `conversation_created` which we adopt.
      await client.run(activeId, prompt)
    },
    [activeId]
  )

  const cancel = useCallback(() => {
    if (activeId) client.cancel(activeId)
    setRunning(false)
  }, [activeId])

  const respondApproval = useCallback(
    (approved: boolean) => {
      if (approval) client.respondApproval({ id: approval.id, approved })
      setApproval(null)
    },
    [approval]
  )

  const refreshFiles = useCallback(() => setFilesReloadToken(String(Date.now())), [])

  const updateSettings = useCallback(
    (s: AppSettings) => {
      setSettings((prev) => {
        // If the project directory changed, reset the file explorer/viewer.
        if (prev && prev.projectPath !== s.projectPath) {
          setOpenFilePath(null)
          setFilesReloadToken(String(Date.now()))
        }
        return s
      })
    },
    []
  )

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNew={newConversation}
        onDelete={deleteConversation}
        onOpenFile={setOpenFilePath}
        selectedFilePath={openFilePath}
        filesReloadToken={filesReloadToken}
        onRefreshFiles={refreshFiles}
      />
      <div className="main">
        <TopBar
          settings={settings}
          onSettingsChange={updateSettings}
          onNewProject={() => setNewProjectOpen(true)}
        />
        {openFilePath ? (
          <FileViewer path={openFilePath} onClose={() => setOpenFilePath(null)} />
        ) : (
          <>
            <ChatView messages={messages} running={running} hasApiKey={settings?.hasApiKey ?? true} />
            <Composer running={running} disabled={!settings?.hasApiKey} onSend={send} onCancel={cancel} />
          </>
        )}
      </div>
      {approval && <ApprovalModal request={approval} onRespond={respondApproval} />}
      {newProjectOpen && (
        <NewProjectModal
          defaultParent={
            settings?.projectPath
              ? settings.projectPath.replace(/[/\\][^/\\]+[/\\]?$/, '') || settings.projectPath
              : null
          }
          onClose={() => setNewProjectOpen(false)}
          onCreated={updateSettings}
        />
      )}
    </div>
  )
}
