import { useState, type KeyboardEvent } from 'react'

interface Props {
  running: boolean
  disabled?: boolean
  onSend: (prompt: string) => void
  onCancel: () => void
}

export default function Composer({ running, disabled, onSend, onCancel }: Props): JSX.Element {
  const [value, setValue] = useState('')

  const submit = (): void => {
    const text = value.trim()
    if (!text || running || disabled) return
    onSend(text)
    setValue('')
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="composer">
      <textarea
        className="composer-input"
        placeholder={disabled ? 'Set OPENAI_API_KEY to start…' : 'Ask the agent to build or change something… (Enter to send, Shift+Enter for newline)'}
        value={value}
        disabled={disabled}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={onKeyDown}
        rows={3}
      />
      {running ? (
        <button className="btn-send stop" onClick={onCancel}>
          Stop
        </button>
      ) : (
        <button className="btn-send" onClick={submit} disabled={disabled || !value.trim()}>
          Send
        </button>
      )}
    </div>
  )
}
