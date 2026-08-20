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
  const { material, source_filename, grade_level, downloads, ocr_used } = result
  const { notes, questions } = material

  const base = (notes.title || source_filename || 'study-material').replace(/[^\w\-]+/g, '_')

  function download(htmlDoc, suffix) {
    const blob = new Blob([htmlDoc], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${base}_${suffix}.html`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  function openPrintable(htmlDoc) {
    const w = window.open('', '_blank')
    if (w) {
      w.document.write(htmlDoc)
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
          <button className="btn ghost" onClick={onReset}>↺ New document</button>
        </div>
      </div>

      <section className="card downloads">
        <h3>⬇ Download</h3>
        <p className="downloads-hint">Three ready-to-use HTML files (open or print in any browser):</p>
        <div className="download-grid">
          <div className="download-card">
            <div className="dl-title">📘 Notes</div>
            <div className="dl-desc">Revision notes only</div>
            <div className="dl-actions">
              <button className="btn" onClick={() => download(downloads.notes, 'notes')}>Download</button>
              <button className="btn ghost" onClick={() => openPrintable(downloads.notes)}>Print</button>
            </div>
          </div>
          <div className="download-card">
            <div className="dl-title">✅ Questions + Answers</div>
            <div className="dl-desc">Full question set with answer key</div>
            <div className="dl-actions">
              <button className="btn" onClick={() => download(downloads.questions_with_answers, 'questions_answers')}>Download</button>
              <button className="btn ghost" onClick={() => openPrintable(downloads.questions_with_answers)}>Print</button>
            </div>
          </div>
          <div className="download-card">
            <div className="dl-title">📝 Questions only</div>
            <div className="dl-desc">Practice/exam sheet, no answers</div>
            <div className="dl-actions">
              <button className="btn" onClick={() => download(downloads.questions_only, 'questions')}>Download</button>
              <button className="btn ghost" onClick={() => openPrintable(downloads.questions_only)}>Print</button>
            </div>
          </div>
        </div>
      </section>

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
