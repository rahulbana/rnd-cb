import { useEffect, useRef } from 'react'
import type { ChatMessage, ToolCallRecord } from '../../../shared/types'

interface Props {
  messages: ChatMessage[]
  running: boolean
  hasApiKey: boolean
}

export default function ChatView({ messages, running, hasApiKey }: Props): JSX.Element {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, running])

  return (
    <div className="chat-view">
      {!hasApiKey && (
        <div className="notice">
          <strong>OpenAI API key not detected.</strong> Set <code>OPENAI_API_KEY</code> in a{' '}
          <code>.env</code> file at the project root and restart the app.
        </div>
      )}

      {messages.length === 0 && hasApiKey && (
        <div className="welcome">
          <h2>What are we building?</h2>
          <p>
            Ask me to explore your codebase, write features, fix bugs, or run tests. I can read and
            edit files and run shell commands in your selected project directory.
          </p>
        </div>
      )}

      {messages.map((m) => (
        <MessageItem key={m.id} message={m} />
      ))}

      {running && (
        <div className="message assistant">
          <div className="bubble thinking">
            <span className="dot" />
            <span className="dot" />
            <span className="dot" />
          </div>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  )
}

function MessageItem({ message }: { message: ChatMessage }): JSX.Element | null {
  if (message.role === 'user') {
    return (
      <div className="message user">
        <div className="bubble">{message.content}</div>
      </div>
    )
  }

  if (message.role === 'tool') {
    return (
      <details className="tool-result">
        <summary>
          🛠 {message.name} result
        </summary>
        <pre>{message.content}</pre>
      </details>
    )
  }

  // assistant
  const hasText = message.content.trim().length > 0
  return (
    <div className="message assistant">
      {message.toolCalls?.map((tc) => <ToolCallChip key={tc.id} call={tc} />)}
      {hasText && <div className="bubble">{renderContent(message.content)}</div>}
    </div>
  )
}

function ToolCallChip({ call }: { call: ToolCallRecord }): JSX.Element {
  let label = call.name
  try {
    const args = JSON.parse(call.arguments || '{}')
    if (call.name === 'run_command') label = `run: ${args.command}`
    else if (call.name === 'read_file') label = `read: ${args.path}`
    else if (call.name === 'write_file') label = `write: ${args.path}`
    else if (call.name === 'list_files') label = `list: ${args.dir ?? '.'}`
  } catch {
    /* ignore */
  }
  return <div className="tool-call-chip">⚙️ {label}</div>
}

// Lightweight rendering: preserve whitespace and highlight fenced code blocks.
function renderContent(content: string): JSX.Element[] {
  const parts = content.split(/(```[\s\S]*?```)/g)
  return parts.map((part, i) => {
    if (part.startsWith('```')) {
      const body = part.replace(/^```[a-zA-Z0-9]*\n?/, '').replace(/```$/, '')
      return (
        <pre className="code-block" key={i}>
          <code>{body}</code>
        </pre>
      )
    }
    return (
      <span className="prose" key={i}>
        {part}
      </span>
    )
  })
}
