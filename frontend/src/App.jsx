import { useEffect, useMemo, useState } from 'react'
import { fetchQuestionTypes, generate } from './api.js'
import Results from './Results.jsx'

const ACCEPTED = '.pdf,.doc,.docx,.ppt,.pptx,.txt,.md,.csv'

export default function App() {
  const [types, setTypes] = useState([])
  const [selected, setSelected] = useState({})
  const [openaiConfigured, setOpenaiConfigured] = useState(true)
  const [file, setFile] = useState(null)
  const [gradeLevel, setGradeLevel] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [dragging, setDragging] = useState(false)

  useEffect(() => {
    fetchQuestionTypes()
      .then(({ types, openaiConfigured }) => {
        setTypes(types)
        setOpenaiConfigured(openaiConfigured)
        // Everything selected by default.
        setSelected(Object.fromEntries(types.map((t) => [t.id, true])))
      })
      .catch((e) => setError(e.message))
  }, [])

  const selectedIds = useMemo(
    () => Object.entries(selected).filter(([, v]) => v).map(([k]) => k),
    [selected],
  )

  function toggle(id) {
    setSelected((s) => ({ ...s, [id]: !s[id] }))
  }

  function onDrop(e) {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files?.[0]
    if (f) setFile(f)
  }

  async function onGenerate() {
    setError('')
    if (!file) return setError('Please choose a document first.')
    if (selectedIds.length === 0) return setError('Select at least one question type.')
    setLoading(true)
    setResult(null)
    try {
      const data = await generate({ file, questionTypes: selectedIds, gradeLevel })
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function reset() {
    setResult(null)
    setError('')
  }

  return (
    <div className="app">
      <header className="hero">
        <h1>📚 Study Notes &amp; Question Generator</h1>
        <p>
          Upload a chapter, worksheet or slide deck. Get clear revision notes and
          ready-to-practice questions — with answers — for students and parents.
        </p>
      </header>

      {!openaiConfigured && (
        <div className="banner warn">
          ⚠️ The server has no OpenAI API key configured. Set <code>OPENAI_API_KEY</code>{' '}
          in the backend before generating.
        </div>
      )}

      {!result && (
        <main className="panel">
          <section
            className={`dropzone ${dragging ? 'drag' : ''} ${file ? 'has-file' : ''}`}
            onDragOver={(e) => {
              e.preventDefault()
              setDragging(true)
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
          >
            <input
              id="file"
              type="file"
              accept={ACCEPTED}
              onChange={(e) => setFile(e.target.files?.[0] || null)}
            />
            <label htmlFor="file" className="drop-label">
              {file ? (
                <>
                  <span className="file-name">📄 {file.name}</span>
                  <span className="file-hint">Click to choose a different file</span>
                </>
              ) : (
                <>
                  <span className="big">Drop a document here or click to browse</span>
                  <span className="file-hint">PDF, DOCX, PPTX, or text files</span>
                </>
              )}
            </label>
          </section>

          <section className="field">
            <label htmlFor="grade">Grade / level (optional)</label>
            <input
              id="grade"
              type="text"
              placeholder="e.g. Class 8, High School Biology"
              value={gradeLevel}
              onChange={(e) => setGradeLevel(e.target.value)}
            />
          </section>

          <section className="field">
            <label>Question types</label>
            <div className="chips">
              {types.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  className={`chip ${selected[t.id] ? 'on' : ''}`}
                  onClick={() => toggle(t.id)}
                >
                  {selected[t.id] ? '✓ ' : ''}
                  {t.label}
                </button>
              ))}
            </div>
          </section>

          {error && <div className="banner error">{error}</div>}

          <button className="generate" onClick={onGenerate} disabled={loading}>
            {loading ? 'Generating… this can take a moment' : '✨ Generate Notes & Questions'}
          </button>
          {loading && <div className="progress"><div className="bar" /></div>}
        </main>
      )}

      {result && <Results result={result} onReset={reset} />}

      <footer className="site-footer">
        Powered by OpenAI · No documents are stored — everything is processed in memory.
      </footer>
    </div>
  )
}
