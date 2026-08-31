function resolveApiBase() {
  const params = new URLSearchParams(window.location.search)
  const queryBase = params.get('api')
  const envBase = import.meta.env.VITE_API_BASE_URL
  if (queryBase) return queryBase.replace(/\/$/, '')
  if (envBase) return envBase.replace(/\/$/, '')
  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') return 'http://localhost:8000'
  return ''
}

export const API_BASE_URL = resolveApiBase()
function requireApiBase() { if (!API_BASE_URL) throw new Error('VITE_API_BASE_URL is not configured.') }
async function json(response, label) { const body = await response.json().catch(() => ({})); if (!response.ok) throw new Error(body.detail || `${label} failed (${response.status})`); return body }

export async function getHealth() { requireApiBase(); return json(await fetch(`${API_BASE_URL}/health`), 'Health check') }
export async function getUsage() { requireApiBase(); return json(await fetch(`${API_BASE_URL}/api/v1/usage`), 'Usage lookup') }
export async function getLive({ market = 'KRW-BTC', source = 'live' } = {}) {
  requireApiBase(); const qs = new URLSearchParams({ market, source }); return json(await fetch(`${API_BASE_URL}/api/v1/live?${qs}`), 'Live snapshot')
}
export async function runAnalysis({ source = 'live', market = 'KRW-BTC', historyYears = 8, question = '현재 BTC를 NOW, TODAY, 1W, 1M, 1Y 관점에서 분석하고 보유·추가매수·익절 대응을 판단해줘.' } = {}) {
  requireApiBase(); return json(await fetch(`${API_BASE_URL}/api/v1/analyze`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ market, history_years: historyYears, source, question }) }), 'Analysis')
}
