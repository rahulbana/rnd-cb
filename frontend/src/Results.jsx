export default function Results({ result, onReset }) {
  const { material, source_filename, grade_level, downloads, ocr_used,
    web_search_used, sources = [] } = result
  const { notes } = material
  const pyqCount = material?.previous_year?.length || 0

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
            {web_search_used && (
              <span className="web-badge">
                🌐 Enriched with {sources.length || 'online'} reference
                {sources.length === 1 ? '' : 's'}
              </span>
            )}
            {pyqCount > 0 && (
              <span className="pyq-badge">📜 {pyqCount} previous-year questions</span>
            )}
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
    </div>
  )
}
