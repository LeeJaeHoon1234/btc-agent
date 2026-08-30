import React, { useEffect, useMemo, useState } from 'react'
import { API_BASE_URL, getHealth, runAnalysis } from './api.js'

const h = React.createElement

const fmt = (value, digits = 1) =>
  value === null || value === undefined || Number.isNaN(Number(value))
    ? '—'
    : Number(value).toLocaleString('ko-KR', { maximumFractionDigits: digits })

const pct = (value, digits = 1) => `${fmt(value, digits)}%`

function Badge({ children, tone = 'neutral' }) {
  return h('span', { className: `badge badge-${tone}` }, children)
}

function Card({ label, value, sub, tone = 'neutral' }) {
  return h('article', { className: `metric-card tone-${tone}` },
    h('div', { className: 'metric-label' }, label),
    h('div', { className: 'metric-value' }, value),
    sub ? h('div', { className: 'metric-sub' }, sub) : null,
  )
}

function ScoreBar({ label, score, inverse = false }) {
  const safe = Math.max(0, Math.min(100, Number(score || 0)))
  return h('div', { className: 'score-block' },
    h('div', { className: 'score-row' },
      h('span', null, label),
      h('strong', null, `${safe.toFixed(1)}/100`),
    ),
    h('div', { className: 'score-track' },
      h('div', {
        className: inverse ? 'score-fill score-fill-risk' : 'score-fill',
        style: { width: `${safe}%` },
      }),
    ),
  )
}

function LineChart({ points = [] }) {
  const valid = points.filter((p) => Number.isFinite(Number(p.close)))
  if (valid.length < 2) return h('div', { className: 'empty' }, '가격 데이터 없음')

  const width = 900
  const height = 240
  const pad = 18
  const closes = valid.map((p) => Number(p.close))
  const min = Math.min(...closes)
  const max = Math.max(...closes)
  const range = max - min || 1
  const xy = valid.map((p, i) => {
    const x = pad + (i / (valid.length - 1)) * (width - pad * 2)
    const y = height - pad - ((Number(p.close) - min) / range) * (height - pad * 2)
    return [x, y]
  })
  const path = xy.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ')

  return h('div', { className: 'chart-wrap' },
    h('svg', { viewBox: `0 0 ${width} ${height}`, role: 'img', 'aria-label': '최근 BTC 가격 추이' },
      h('path', { className: 'chart-line', d: path, fill: 'none' }),
    ),
    h('div', { className: 'chart-axis' },
      h('span', null, `Low ${fmt(min, 0)} KRW`),
      h('span', null, `${valid.length}D`),
      h('span', null, `High ${fmt(max, 0)} KRW`),
    ),
  )
}

function List({ items = [], empty = '없음' }) {
  if (!items?.length) return h('p', { className: 'empty' }, empty)
  return h('ul', { className: 'clean-list' }, ...items.map((item, i) => h('li', { key: `${i}-${item}` }, String(item))))
}

function ModulePanel({ title, children, badge }) {
  return h('section', { className: 'panel' },
    h('div', { className: 'panel-head' },
      h('h3', null, title),
      badge || null,
    ),
    children,
  )
}

function actionTone(action) {
  if (action === '매수') return 'positive'
  if (action === '비중축소') return 'negative'
  return 'warning'
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [payload, setPayload] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [source, setSource] = useState('live')

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth(null))
  }, [])

  async function analyze(nextSource = source) {
    setLoading(true)
    setError('')
    try {
      const result = await runAnalysis({ source: nextSource })
      setPayload(result)
      setSource(nextSource)
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  const a = payload?.analysis
  const decision = a?.final_decision
  const explanation = a?.explanation
  const tone = actionTone(decision?.action)

  const regimeLabel = useMemo(() => {
    const map = {
      bull_trend: 'Bull Trend',
      bull_transition: 'Bull Transition',
      sideways: 'Sideways',
      bear_transition: 'Bear Transition',
      bear_trend: 'Bear Trend',
    }
    return map[a?.regime?.regime] || '—'
  }, [a])

  return h('div', { className: 'app-shell' },
    h('header', { className: 'topbar' },
      h('div', { className: 'brand' }, h('span', { className: 'btc-mark' }, '₿'), h('span', null, 'BTC Agent')),
      h('div', { className: 'top-status' },
        health
          ? h(Badge, { tone: 'positive' }, `API online · ML ${health.model_available ? 'ready' : 'fallback'} · LLM ${health.llm_available ? 'on' : 'off'}`)
          : h(Badge, { tone: 'negative' }, 'API offline'),
      ),
    ),

    h('main', null,
      h('section', { className: 'hero' },
        h('div', null,
          h('p', { className: 'eyebrow' }, 'RULE × ML × CONDITIONAL LLM'),
          h('h1', null, '시장 신호를 모으고, 충돌할 때만 깊게 분석한다.'),
          h('p', { className: 'hero-copy' }, '기존 BTC Agent 오케스트레이터를 FastAPI로 노출하고 React에서 결과를 시각화한 의사결정 보조 서비스.'),
        ),
        h('div', { className: 'controls' },
          h('div', { className: 'segmented' },
            h('button', { className: source === 'live' ? 'active' : '', onClick: () => setSource('live') }, 'Live'),
            h('button', { className: source === 'demo' ? 'active' : '', onClick: () => setSource('demo') }, 'Demo'),
          ),
          h('button', { className: 'primary-btn', disabled: loading, onClick: () => analyze(source) }, loading ? '분석 중…' : 'BTC 분석 실행'),
        ),
      ),

      error ? h('section', { className: 'error-box' },
        h('strong', null, '분석 실패'),
        h('span', null, error),
        source === 'live' ? h('button', { onClick: () => analyze('demo') }, 'Demo로 파이프라인 확인') : null,
      ) : null,

      !a ? h('section', { className: 'welcome panel' },
        h('h2', null, 'Ready'),
        h('p', null, 'Live는 Upbit 데이터를 사용합니다. Demo는 외부 네트워크 없이 동일한 Agent 파이프라인 전체를 검증합니다.'),
        h('code', null, API_BASE_URL),
      ) : h(React.Fragment, null,
        h('section', { className: 'decision-strip' },
          h('div', null,
            h('p', { className: 'eyebrow' }, `${payload.meta.market} · ${payload.meta.source.toUpperCase()}${payload.meta.cached ? ' · CACHED' : ''}`),
            h('h2', null, explanation?.headline || decision?.thesis || '분석 완료'),
            h('p', null, explanation?.summary || decision?.thesis),
          ),
          h('div', { className: `decision-action decision-${tone}` },
            h('span', null, 'FINAL'),
            h('strong', null, decision?.action || '—'),
            h('small', null, `confidence ${pct((decision?.confidence || 0) * 100, 0)}`),
          ),
        ),

        h('section', { className: 'metrics-grid' },
          h(Card, { label: 'BTC / KRW', value: `${fmt(a.latest?.close, 0)} ₩`, sub: a.latest?.date }),
          h(Card, { label: 'Entry Score', value: fmt(a.entry?.score), sub: a.entry?.label, tone: Number(a.entry?.score) >= 70 ? 'positive' : 'neutral' }),
          h(Card, { label: 'Exit Risk', value: fmt(a.exit?.score), sub: a.exit?.label, tone: Number(a.exit?.score) >= 60 ? 'negative' : 'neutral' }),
          h(Card, { label: 'Market Regime', value: regimeLabel, sub: `bull score ${fmt(a.regime?.bull_score)}` }),
          h(Card, { label: 'Route', value: a.gate?.route || '—', sub: `gate confidence ${pct((a.gate?.confidence || 0) * 100, 0)}`, tone: a.gate?.route === 'deep_analysis' ? 'warning' : 'positive' }),
        ),

        h(ModulePanel, { title: 'Price Context', badge: h(Badge, { tone: payload.meta.source === 'live' ? 'positive' : 'warning' }, payload.meta.source) },
          h(LineChart, { points: a.series }),
          h('div', { className: 'mini-metrics' },
            h('span', null, `RSI 14  ${fmt(a.latest?.rsi14)}`),
            h('span', null, `MA20 Gap  ${pct(a.latest?.ma20_gap_pct)}`),
            h('span', null, `MA200 Gap  ${pct(a.latest?.ma200_gap_pct)}`),
            h('span', null, `30D Return  ${pct(a.latest?.return_30d)}`),
            h('span', null, `Volume Ratio  ${fmt(a.latest?.volume_ratio, 2)}x`),
          ),
        ),

        h('section', { className: 'two-col' },
          h(ModulePanel, { title: 'Decision Scores' },
            h(ScoreBar, { label: '매수 매력도', score: a.entry?.score }),
            h(ScoreBar, { label: '고점 위험도', score: a.exit?.score, inverse: true }),
            h('div', { className: 'component-grid' },
              ...Object.entries(a.entry?.components || {}).map(([key, value]) => h('div', { key }, h('span', null, key), h('strong', null, fmt(value)))),
            ),
          ),
          h(ModulePanel, { title: 'Confidence Gate', badge: h(Badge, { tone: a.gate?.route === 'deep_analysis' ? 'warning' : 'positive' }, a.gate?.route || '—') },
            h('p', { className: 'big-number' }, pct((a.gate?.confidence || 0) * 100, 0)),
            h(List, { items: a.gate?.reasons, empty: '신호 충돌 없음' }),
          ),
        ),

        h('section', { className: 'three-col' },
          h(ModulePanel, { title: 'Technical', badge: h(Badge, { tone: a.technical?.stance === 'bullish' ? 'positive' : a.technical?.stance === 'bearish' ? 'negative' : 'neutral' }, a.technical?.stance || '—') },
            h('p', { className: 'big-number' }, fmt(a.technical?.score)),
            h(List, { items: a.technical?.reasons }),
          ),
          h(ModulePanel, { title: 'ML · 30D' },
            a.ml?.available
              ? h(React.Fragment, null,
                  h('p', { className: 'big-number' }, pct(a.ml?.up_probability, 0)),
                  h('p', { className: 'muted' }, `WF AUC ${fmt(a.ml?.metadata?.walk_forward_mean_auc, 3)}`),
                )
              : h(React.Fragment, null,
                  h(Badge, { tone: 'warning' }, 'Model fallback'),
                  h('p', { className: 'muted' }, a.ml?.message || '저장 모델이 없어 중립값을 사용합니다.'),
                ),
          ),
          h(ModulePanel, { title: 'Cycle' },
            h('p', { className: 'big-number' }, a.cycle?.stage || '—'),
            h('p', { className: 'muted' }, `heat ${fmt(a.cycle?.heat_score)}/100`),
            h(List, { items: a.cycle?.reasons, empty: '강한 과열 신호 없음' }),
          ),
        ),

        h('section', { className: 'two-col' },
          h(ModulePanel, { title: '좋은 신호' }, h(List, { items: explanation?.positives })),
          h(ModulePanel, { title: '주의할 점' }, h(List, { items: explanation?.cautions })),
          h(ModulePanel, { title: '현재 전략' }, h(List, { items: explanation?.strategy })),
          h(ModulePanel, { title: '다시 판단할 조건' }, h(List, { items: explanation?.recheck })),
        ),

        h(ModulePanel, { title: 'Agent Execution Trace', badge: h(Badge, { tone: 'neutral' }, `${a.logs?.length || 0} steps`) },
          h('div', { className: 'trace' }, ...(a.logs || []).map((step, index) => h('div', { className: 'trace-step', key: `${step}-${index}` }, h('span', null, String(index + 1).padStart(2, '0')), h('strong', null, step)))),
        ),

        h('footer', null,
          h('p', null, 'Decision support only · 투자 수익을 보장하지 않으며 데이터/모델 한계를 함께 표시합니다.'),
          h('p', null, `API ${API_BASE_URL}`),
        ),
      ),
    ),
  )
}
