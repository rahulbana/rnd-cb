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

let localSeq = 0
const localId = (): string => `local-${Date.now()}-${localSeq++}`

export default function App(): JSX.Element {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [running, setRunning] = useState(false)
  const [approval, setApproval] = useState<ApprovalRequest | null>(null)

  const activeIdRef = useRef<string | null>(null)
  activeIdRef.current = activeId

  const refreshConversations = useCallback(async () => {
    setConversations(await window.api.listConversations())
  }, [])

  // Initial load + event subscriptions (registered once).
  useEffect(() => {
    void window.api.getSettings().then(setSettings)
    void refreshConversations()

    const offEvent = window.api.onAgentEvent((e: AgentEvent) => {
      if (e.conversationId !== activeIdRef.current) return
      handleAgentEvent(e)
    })
    const offApproval = window.api.onApprovalRequest((r) => setApproval(r))
    const offCreated = window.api.onConversationCreated((c) => {
      setConversations((prev) => [c, ...prev])
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
          void window.api.getMessages(activeIdRef.current).then(setMessages)
        }
        void refreshConversations()
        break
    }
  }

  const selectConversation = useCallback(async (id: string) => {
    setActiveId(id)
    setMessages(await window.api.getMessages(id))
  }, [])

  const newConversation = useCallback(() => {
    setActiveId(null)
    setMessages([])
  }, [])

  const deleteConversation = useCallback(
    async (id: string) => {
      await window.api.deleteConversation(id)
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
      const { conversationId } = await window.api.runAgent({ conversationId: activeId, prompt })
      setActiveId(conversationId)
    },
    [activeId]
  )

  const cancel = useCallback(async () => {
    if (activeId) await window.api.cancelAgent(activeId)
    setRunning(false)
  }, [activeId])

  const respondApproval = useCallback(
    (approved: boolean) => {
      if (approval) window.api.respondApproval({ id: approval.id, approved })
      setApproval(null)
    },
    [approval]
  )

  const updateSettings = useCallback((s: AppSettings) => setSettings(s), [])

  return (
    <div className="app">
      <Sidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={selectConversation}
        onNew={newConversation}
        onDelete={deleteConversation}
      />
      <div className="main">
        <TopBar settings={settings} onSettingsChange={updateSettings} />
        <ChatView messages={messages} running={running} hasApiKey={settings?.hasApiKey ?? true} />
        <Composer running={running} disabled={!settings?.hasApiKey} onSend={send} onCancel={cancel} />
      </div>
      {approval && <ApprovalModal request={approval} onRespond={respondApproval} />}
    </div>
  )
}
