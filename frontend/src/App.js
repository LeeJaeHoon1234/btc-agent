import React, { useEffect, useMemo, useState } from 'react'
import { API_BASE_URL, getHealth, getSkills, runAnalysis } from './api.js'

const h = React.createElement
const DEFAULT_Q = '지금 BTC를 추매/보유/익절/비중축소 중 어떻게 대응해야 하고, 가장 중요한 근거는 무엇인가?'

const fmt = (value, digits = 1) => value === null || value === undefined || Number.isNaN(Number(value))
  ? '—' : Number(value).toLocaleString('ko-KR', { maximumFractionDigits: digits })
const pct = (value, digits = 1) => `${fmt(value, digits)}%`

function Badge({ children, tone = 'neutral' }) { return h('span', { className: `badge badge-${tone}` }, children) }
function Card({ label, value, sub, tone = 'neutral' }) {
  return h('article', { className: `metric-card tone-${tone}` }, h('div', { className: 'metric-label' }, label), h('div', { className: 'metric-value' }, value), sub ? h('div', { className: 'metric-sub' }, sub) : null)
}
function ModulePanel({ title, children, badge }) { return h('section', { className: 'panel' }, h('div', { className: 'panel-head' }, h('h3', null, title), badge || null), children) }
function List({ items = [], empty = '없음' }) {
  if (!items?.length) return h('p', { className: 'empty' }, empty)
  return h('ul', { className: 'clean-list' }, ...items.map((item, i) => h('li', { key: `${i}-${String(item)}` }, String(item))))
}
function ScoreBar({ label, score, inverse = false }) {
  const safe = Math.max(0, Math.min(100, Number(score || 0)))
  return h('div', { className: 'score-block' }, h('div', { className: 'score-row' }, h('span', null, label), h('strong', null, `${safe.toFixed(1)}/100`)), h('div', { className: 'score-track' }, h('div', { className: inverse ? 'score-fill score-fill-risk' : 'score-fill', style: { width: `${safe}%` } })))
}
function LineChart({ points = [] }) {
  const valid = points.filter((p) => Number.isFinite(Number(p.close)))
  if (valid.length < 2) return h('div', { className: 'empty' }, '가격 데이터 없음')
  const width = 900, height = 240, pad = 18
  const closes = valid.map((p) => Number(p.close)), min = Math.min(...closes), max = Math.max(...closes), range = max - min || 1
  const xy = valid.map((p, i) => [pad + (i / (valid.length - 1)) * (width - pad * 2), height - pad - ((Number(p.close) - min) / range) * (height - pad * 2)])
  const path = xy.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')
  return h('div', { className: 'chart-wrap' }, h('svg', { viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': '최근 BTC 가격 추이' }, h('path', { className: 'chart-line', d: path, fill: 'none' })), h('div', { className: 'chart-axis' }, h('span', null, `Low ${fmt(min, 0)} KRW`), h('span', null, `${valid.length}D`), h('span', null, `High ${fmt(max, 0)} KRW`)))
}
function actionTone(action) { if (action === '매수') return 'positive'; if (action === '비중축소') return 'negative'; return 'warning' }
function stanceTone(stance) { if (stance === 'BULLISH') return 'positive'; if (stance === 'BEARISH') return 'negative'; return 'warning' }

function ExpertPanel({ name, data }) {
  if (!data) return null
  return h(ModulePanel, { title: name, badge: h(Badge, { tone: data.available === false ? 'neutral' : data.score > 8 ? 'positive' : data.score < -8 ? 'negative' : 'warning' }, data.available === false ? 'unavailable' : `${fmt(data.score, 0)}`) },
    h('p', { className: 'muted' }, data.summary || '—'),
    data.regime ? h('p', { className: 'big-number small-big' }, data.regime) : null,
    h(List, { items: data.evidence?.slice(0, 4), empty: '근거 없음' }),
    data.risks?.length ? h('div', { className: 'subtle-box' }, h('strong', null, 'Risks'), h(List, { items: data.risks?.slice(0, 3) })) : null,
  )
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [skills, setSkills] = useState([])
  const [payload, setPayload] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [source, setSource] = useState('live')
  const [question, setQuestion] = useState(DEFAULT_Q)

  useEffect(() => { getHealth().then(setHealth).catch(() => setHealth(null)); getSkills().then((x) => setSkills(x.skills || [])).catch(() => setSkills([])) }, [])

  async function analyze(nextSource = source) {
    setLoading(true); setError('')
    try { const result = await runAnalysis({ source: nextSource, question }); setPayload(result); setSource(nextSource) }
    catch (err) { setError(err.message || String(err)) }
    finally { setLoading(false) }
  }

  const a = payload?.analysis, decision = a?.final_decision, explanation = a?.explanation, tone = actionTone(decision?.action)
  const regimeLabel = useMemo(() => ({ bull_trend: 'Bull Trend', bull_transition: 'Bull Transition', sideways: 'Sideways', bear_transition: 'Bear Transition', bear_trend: 'Bear Trend' }[a?.regime?.regime] || '—'), [a])
  const adjustedEntry = a?.research_adjustment?.adjusted_entry_score ?? a?.entry?.score
  const adjustedExit = a?.research_adjustment?.adjusted_exit_score ?? a?.exit?.score

  return h('div', { className: 'app-shell' },
    h('header', { className: 'topbar' }, h('div', { className: 'brand' }, h('span', { className: 'btc-mark' }, '₿'), h('span', null, 'BTC Agent V3')), h('div', { className: 'top-status' }, health ? h(Badge, { tone: 'positive' }, `API online · ML ${health.model_available ? 'ready' : 'fallback'} · LLM ${health.llm_available ? 'on' : 'off'} · ${health.skill_count || skills.length} skills`) : h(Badge, { tone: 'negative' }, 'API offline'))),
    h('main', null,
      h('section', { className: 'hero' },
        h('div', null, h('p', { className: 'eyebrow' }, 'PLANNER × SKILLS × TOOLS × RAG × RULE/ML × CRITIC'), h('h1', null, '질문을 받고, 필요한 전문가만 스스로 호출한다.'), h('p', { className: 'hero-copy' }, 'V2의 deterministic decision engine 위에 Planner, specialist skills, external research tools, retrieval, evidence tracking을 추가한 autonomous research layer.')),
        h('div', { className: 'controls controls-v3' }, h('div', { className: 'segmented' }, h('button', { className: source === 'live' ? 'active' : '', onClick: () => setSource('live') }, 'Live'), h('button', { className: source === 'demo' ? 'active' : '', onClick: () => setSource('demo') }, 'Demo')), h('button', { className: 'primary-btn', disabled: loading, onClick: () => analyze(source) }, loading ? 'Agent Researching…' : 'Run Autonomous Analysis')),
      ),
      h('section', { className: 'query-panel panel' }, h('label', { htmlFor: 'agent-question' }, 'Research Question'), h('textarea', { id: 'agent-question', value: question, onChange: (e) => setQuestion(e.target.value), rows: 3, maxLength: 600 }), h('div', { className: 'skill-row' }, ...skills.map((s) => h('span', { className: 'skill-chip', title: s.mission, key: s.name }, s.name)))),
      error ? h('section', { className: 'error-box' }, h('strong', null, '분석 실패'), h('span', null, error), source === 'live' ? h('button', { onClick: () => analyze('demo') }, 'Demo로 검증') : null) : null,
      !a ? h('section', { className: 'welcome panel' }, h('h2', null, 'Ready'), h('p', null, 'Live는 Upbit + 외부 research tools를 사용합니다. Demo는 외부 네트워크 없이 V3 전체 orchestration을 검증합니다.'), h('code', null, API_BASE_URL)) : h(React.Fragment, null,
        h('section', { className: 'decision-strip' }, h('div', null, h('p', { className: 'eyebrow' }, `${payload.meta.market} · V${payload.meta.version} · ${payload.meta.source.toUpperCase()}${payload.meta.cached ? ' · CACHED' : ''}`), h('h2', null, explanation?.headline || decision?.thesis || '분석 완료'), h('p', null, explanation?.summary || decision?.thesis)), h('div', { className: `decision-action decision-${tone}` }, h('span', null, 'FINAL'), h('strong', null, decision?.action || '—'), h('small', null, `confidence ${pct((decision?.confidence || 0) * 100, 0)}`))),
        h('section', { className: 'metrics-grid' },
          h(Card, { label: 'BTC / KRW', value: `${fmt(a.latest?.close, 0)} ₩`, sub: a.latest?.date }),
          h(Card, { label: 'Adjusted Entry', value: fmt(adjustedEntry), sub: `core ${fmt(a.entry?.score)} · research Δ ${fmt(a.research_adjustment?.entry_delta)}`, tone: Number(adjustedEntry) >= 70 ? 'positive' : 'neutral' }),
          h(Card, { label: 'Adjusted Exit Risk', value: fmt(adjustedExit), sub: `core ${fmt(a.exit?.score)}`, tone: Number(adjustedExit) >= 60 ? 'negative' : 'neutral' }),
          h(Card, { label: 'Core Regime', value: regimeLabel, sub: `bull score ${fmt(a.regime?.bull_score)}` }),
          h(Card, { label: 'Research Stance', value: a.research?.stance || '—', sub: `score ${fmt(a.research?.score)} · conf ${pct((a.research?.confidence || 0) * 100, 0)}`, tone: stanceTone(a.research?.stance) }),
        ),
        h(ModulePanel, { title: 'Planner', badge: h(Badge, { tone: a.plan?.source === 'llm' ? 'positive' : 'neutral' }, a.plan?.source || '—') }, h('p', { className: 'big-copy' }, a.plan?.objective), h('div', { className: 'skill-row' }, ...(a.plan?.selected_skills || []).map((s) => h('span', { className: 'skill-chip selected', key: s }, s))), h('p', { className: 'muted' }, a.plan?.reason)),
        h(ModulePanel, { title: 'Research Synthesis', badge: h(Badge, { tone: stanceTone(a.research?.stance) }, a.research?.stance || '—') }, h('p', { className: 'big-copy' }, a.research?.market_story), h('section', { className: 'two-col nested' }, h('div', null, h('strong', null, 'Bullish'), h(List, { items: a.research?.bullish_factors })), h('div', null, h('strong', null, 'Bearish / Unknown'), h(List, { items: [...(a.research?.bearish_factors || []), ...(a.research?.unknowns || [])] })))),
        h('section', { className: 'two-col' }, h(ExpertPanel, { name: 'Technical Expert', data: a.experts?.technical }), h(ExpertPanel, { name: 'Derivatives Expert', data: a.experts?.derivatives }), h(ExpertPanel, { name: 'Macro Expert', data: a.experts?.macro }), h(ExpertPanel, { name: 'News / RAG Expert', data: a.experts?.news }), h(ExpertPanel, { name: 'Historical RAG Expert', data: a.experts?.historical })),
        h(ModulePanel, { title: 'Evidence Registry', badge: h(Badge, { tone: 'neutral' }, `${a.evidence?.length || 0} items`) }, (a.evidence || []).length ? h('div', { className: 'evidence-list' }, ...(a.evidence || []).slice(0, 16).map((e) => h('div', { className: 'evidence-item', key: e.id }, h('span', { className: 'evidence-id' }, e.id), h('div', null, h('strong', null, `${e.agent} · ${e.source || e.kind}`), e.url ? h('a', { href: e.url, target: '_blank', rel: 'noreferrer' }, e.claim) : h('p', null, e.claim))))) : h('p', { className: 'empty' }, 'Evidence 없음')),
        h(ModulePanel, { title: 'Price Context' }, h(LineChart, { points: a.series }), h('div', { className: 'mini-metrics' }, h('span', null, `RSI ${fmt(a.latest?.rsi14)}`), h('span', null, `MA20 ${pct(a.latest?.ma20_gap_pct)}`), h('span', null, `MA200 ${pct(a.latest?.ma200_gap_pct)}`), h('span', null, `30D ${pct(a.latest?.return_30d)}`), h('span', null, `Volume ${fmt(a.latest?.volume_ratio, 2)}x`))),
        h('section', { className: 'two-col' }, h(ModulePanel, { title: 'Decision Scores' }, h(ScoreBar, { label: 'Core Entry', score: a.entry?.score }), h(ScoreBar, { label: 'Research-adjusted Entry', score: adjustedEntry }), h(ScoreBar, { label: 'Exit Risk', score: adjustedExit, inverse: true })), h(ModulePanel, { title: 'Confidence Gate', badge: h(Badge, { tone: a.gate?.route === 'deep_analysis' ? 'warning' : 'positive' }, a.gate?.route || '—') }, h('p', { className: 'big-number' }, pct((a.gate?.confidence || 0) * 100, 0)), h(List, { items: a.gate?.reasons, empty: '신호 충돌 없음' }))),
        h('section', { className: 'two-col' }, h(ModulePanel, { title: '좋은 신호' }, h(List, { items: explanation?.positives })), h(ModulePanel, { title: '주의할 점' }, h(List, { items: explanation?.cautions })), h(ModulePanel, { title: '현재 전략' }, h(List, { items: explanation?.strategy })), h(ModulePanel, { title: '다시 판단할 조건' }, h(List, { items: explanation?.recheck }))),
        h(ModulePanel, { title: 'Agent Execution Trace', badge: h(Badge, { tone: 'neutral' }, `${a.logs?.length || 0} steps`) }, h('div', { className: 'trace' }, ...(a.logs || []).map((step, index) => h('div', { className: 'trace-step', key: `${step}-${index}` }, h('span', null, String(index + 1).padStart(2, '0')), h('strong', null, step))))),
        h('footer', null, h('p', null, 'Decision support only · external data may be unavailable or delayed · research influence is bounded.'), h('p', null, `API ${API_BASE_URL}`)),
      ),
    ),
  )
}
