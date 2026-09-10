// Thin API client for the FastAPI backend.

export const ACTIONS = [
  { id: 'grammar', label: 'Grammar', hint: 'Fix grammar mistakes' },
  { id: 'spelling', label: 'Spelling', hint: 'Fix spelling & typos' },
  { id: 'improve', label: 'Improve', hint: 'Improve clarity & flow' },
  { id: 'professional', label: 'Professional', hint: 'Polished business tone' },
  { id: 'simplify', label: 'Simplify', hint: 'Make it easier to read' },
  { id: 'formal', label: 'Formal', hint: 'Formal register' },
  { id: 'informal', label: 'Informal', hint: 'Casual & friendly' },
]

export async function transformText(text, action) {
  const res = await fetch('/api/transform', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, action }),
  })

  if (!res.ok) {
    let detail = `Request failed (${res.status})`
    try {
      const body = await res.json()
      if (body.detail) detail = body.detail
    } catch {
      /* ignore parse errors */
    }
    throw new Error(detail)
  }

  return res.json()
}

export async function getHealth() {
  const res = await fetch('/api/health')
  if (!res.ok) throw new Error('Backend not reachable')
  return res.json()
}
