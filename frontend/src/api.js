// Thin wrapper around the backend API.

const BASE = import.meta.env.VITE_API_BASE || ''

export async function fetchQuestionTypes() {
  const res = await fetch(`${BASE}/api/health`).catch(() => null)
  const typesRes = await fetch(`${BASE}/api/question-types`)
  if (!typesRes.ok) throw new Error('Could not load question types.')
  const data = await typesRes.json()
  const openaiConfigured = res && res.ok ? (await res.json()).openai_configured : true
  return { types: data.types, openaiConfigured }
}

export async function generate({ file, questionTypes, gradeLevel }) {
  const form = new FormData()
  form.append('file', file)
  form.append('question_types', questionTypes.join(','))
  form.append('grade_level', gradeLevel || '')

  const res = await fetch(`${BASE}/api/generate`, { method: 'POST', body: form })
  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const err = await res.json()
      if (err.detail) detail = err.detail
    } catch (_) {
      /* ignore */
    }
    throw new Error(detail)
  }
  return res.json()
}
