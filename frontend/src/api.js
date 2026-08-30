function resolveApiBase() {
  const params = new URLSearchParams(window.location.search)
  const queryBase = params.get('api')
  const envBase = import.meta.env.VITE_API_BASE_URL

  if (queryBase) return queryBase.replace(/\/$/, '')
  if (envBase) return envBase.replace(/\/$/, '')
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return 'http://localhost:8000'
  }
  return ''
}

export const API_BASE_URL = resolveApiBase()

function requireApiBase() {
  if (!API_BASE_URL) throw new Error('VITE_API_BASE_URL is not configured.')
}

export async function getHealth() {
  requireApiBase()
  const response = await fetch(`${API_BASE_URL}/health`)
  if (!response.ok) throw new Error(`Health check failed (${response.status})`)
  return response.json()
}

export async function getSkills() {
  requireApiBase()
  const response = await fetch(`${API_BASE_URL}/api/v1/skills`)
  if (!response.ok) throw new Error(`Skill lookup failed (${response.status})`)
  return response.json()
}

export async function runAnalysis({ source = 'live', market = 'KRW-BTC', historyYears = 8, question } = {}) {
  requireApiBase()
  const response = await fetch(`${API_BASE_URL}/api/v1/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ market, history_years: historyYears, source, question }),
  })
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.detail || `Analysis failed (${response.status})`)
  return body
}
