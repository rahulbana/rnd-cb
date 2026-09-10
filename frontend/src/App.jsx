import { useEffect, useMemo, useState } from 'react'
import { ACTIONS, getHealth, transformText } from './api.js'

const SAMPLE =
  'I am not able to attend meeting because I have some urgent work.'

export default function App() {
  const [text, setText] = useState(SAMPLE)
  const [action, setAction] = useState('grammar')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [health, setHealth] = useState(null)

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null))
  }, [])

  const wordCount = useMemo(
    () => (text.trim() ? text.trim().split(/\s+/).length : 0),
    [text],
  )

  async function handleSubmit() {
    setError('')
    setResult(null)
    if (!text.trim()) {
      setError('Please enter some text first.')
      return
    }
    setLoading(true)
    try {
      const data = await transformText(text, action)
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function copyResult() {
    if (result?.result) navigator.clipboard.writeText(result.result)
  }

  const notConfigured = health && !health.openai_configured

  return (
    <div className="page">
      <header className="header">
        <h1>
          <span className="logo">✍️</span> AI Grammar &amp; Rewriting Assistant
        </h1>
        <p className="tagline">
          Correct, rewrite, and refine your writing with an LLM.
        </p>
      </header>

      {notConfigured && (
        <div className="banner warn">
          The server has no <code>OPENAI_API_KEY</code>. Add it to{' '}
          <code>backend/.env</code> and restart to enable transformations.
        </div>
      )}

      <section className="card">
        <label className="field-label" htmlFor="input">
          Your text
        </label>
        <textarea
          id="input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type or paste your text here…"
          rows={6}
        />
        <div className="meta-row">
          <span>{wordCount} words</span>
          <button className="link" onClick={() => setText(SAMPLE)}>
            Load example
          </button>
        </div>

        <div className="actions">
          {ACTIONS.map((a) => (
            <button
              key={a.id}
              className={`chip ${action === a.id ? 'chip-active' : ''}`}
              title={a.hint}
              onClick={() => setAction(a.id)}
            >
              {a.label}
            </button>
          ))}
        </div>

        <button
          className="primary"
          onClick={handleSubmit}
          disabled={loading}
        >
          {loading ? 'Working…' : `Apply: ${labelFor(action)}`}
        </button>

        {error && <div className="banner error">{error}</div>}
      </section>

      {result && (
        <section className="card result">
          {result.summary && (
            <p className="summary">{result.summary}</p>
          )}

          <div className="compare">
            <div className="col">
              <h3>Before</h3>
              <div className="text-box before">{result.original}</div>
            </div>
            <div className="col">
              <h3>
                After
                <button className="link copy" onClick={copyResult}>
                  Copy
                </button>
              </h3>
              <div className="text-box after">{result.result}</div>
            </div>
          </div>

          {result.changes?.length > 0 && (
            <div className="changes">
              <h3>Changes</h3>
              <ul>
                {result.changes.map((c, i) => (
                  <li key={i}>
                    <span className="orig">{c.original || '∅'}</span>
                    <span className="arrow">→</span>
                    <span className="repl">{c.replacement || '∅'}</span>
                    {c.reason && <span className="reason"> — {c.reason}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </section>
      )}

      <footer className="footer">
        {health ? (
          <span>Model: {health.model}</span>
        ) : (
          <span>Backend offline</span>
        )}
      </footer>
    </div>
  )
}

function labelFor(id) {
  return ACTIONS.find((a) => a.id === id)?.label ?? id
}
