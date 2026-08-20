import { useState } from 'react'

const TYPE_LABELS = {
  true_false: 'True / False',
  mcq: 'Multiple Choice (MCQ)',
  fill_blanks: 'Fill in the Blanks',
  very_short: 'Very Short Answer',
  short: 'Short Answer',
  long: 'Long Answer',
  case_based: 'Case-Based',
}

const ORDER = ['true_false', 'mcq', 'fill_blanks', 'very_short', 'short', 'long', 'case_based']

function Answer({ children }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="answer">
      <button className="answer-toggle" onClick={() => setOpen((o) => !o)}>
        {open ? 'Hide answer' : 'Show answer'}
      </button>
      {open && <div className="answer-body">{children}</div>}
    </div>
  )
}

export default function Results({ result, onReset }) {
  const { material, source_filename, grade_level, html, ocr_used } = result
  const { notes, questions } = material

  function download() {
    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    const base = (notes.title || source_filename || 'study-notes').replace(/[^\w\-]+/g, '_')
    a.href = url
    a.download = `${base}.html`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  function openPrintable() {
    const w = window.open('', '_blank')
    if (w) {
      w.document.write(html)
      w.document.close()
    }
  }

  return (
    <div className="results">
      <div className="results-bar">
        <div>
          <h2>{notes.title || 'Study Material'}</h2>
          <p className="sub">
            From <strong>{source_filename}</strong>
            {grade_level ? ` · ${grade_level}` : ''}
            {ocr_used && <span className="ocr-badge">🔎 Read via OCR</span>}
          </p>
        </div>
        <div className="actions">
          <button className="btn" onClick={download}>⬇ Download HTML</button>
          <button className="btn ghost" onClick={openPrintable}>🖨 Print</button>
          <button className="btn ghost" onClick={onReset}>↺ New document</button>
        </div>
      </div>

      {/* Notes */}
      <section className="card">
        <h3>📘 Study Notes</h3>
        {notes.summary && <p className="summary">{notes.summary}</p>}
        {notes.key_points?.length > 0 && (
          <>
            <h4>Key Points</h4>
            <ul>{notes.key_points.map((p, i) => <li key={i}>{p}</li>)}</ul>
          </>
        )}
        {notes.sections?.map((s, i) => (
          <div key={i}>
            {s.heading && <h4>{s.heading}</h4>}
            {s.points?.length > 0 && <ul>{s.points.map((p, j) => <li key={j}>{p}</li>)}</ul>}
          </div>
        ))}
        {notes.glossary?.length > 0 && (
          <>
            <h4>Glossary</h4>
            <ul>{notes.glossary.map((g, i) => <li key={i}>{g}</li>)}</ul>
          </>
        )}
      </section>

      {/* Questions */}
      {ORDER.map((type) => {
        const items = questions[type]
        if (!items || items.length === 0) return null
        return (
          <section className="card" key={type}>
            <h3>
              {TYPE_LABELS[type]} <span className="count">{items.length}</span>
            </h3>
            <ol className="qlist">
              {items.map((item, i) => (
                <li key={i}>{renderQuestion(type, item)}</li>
              ))}
            </ol>
          </section>
        )
      })}
    </div>
  )
}

function renderQuestion(type, item) {
  if (type === 'true_false') {
    return (
      <>
        <div className="q">{item.statement}</div>
        <Answer>
          <strong>{item.answer ? 'True' : 'False'}</strong>
          {item.explanation && <p>{item.explanation}</p>}
        </Answer>
      </>
    )
  }
  if (type === 'mcq') {
    return (
      <>
        <div className="q">{item.question}</div>
        <ol className="options" type="A">
          {item.options?.map((o, i) => <li key={i}>{o}</li>)}
        </ol>
        <Answer>
          <strong>{item.answer}</strong>
          {item.explanation && <p>{item.explanation}</p>}
        </Answer>
      </>
    )
  }
  if (type === 'case_based') {
    return (
      <>
        <div className="case">{item.case}</div>
        <ol className="subq">
          {item.questions?.map((sub, i) => (
            <li key={i}>
              <div className="q">{sub.question}</div>
              <Answer>{sub.answer}</Answer>
            </li>
          ))}
        </ol>
      </>
    )
  }
  // fill_blanks, very_short, short, long
  return (
    <>
      <div className="q">{item.question}</div>
      <Answer>{item.answer}</Answer>
    </>
  )
}
