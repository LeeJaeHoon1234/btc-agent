import React, { useEffect, useMemo, useRef, useState } from 'react'
import { getHealth, getLive, getUsage, runAnalysis } from './api.js'

const HORIZONS = ['NOW', 'TODAY', '1W', '1M', '1Y']
const H_LABEL = { NOW: '지금', TODAY: '오늘', '1W': '1주', '1M': '1개월', '1Y': '1년' }
const DEFAULT_Q = '현재 BTC를 NOW, TODAY, 1W, 1M, 1Y 관점에서 분석하고 보유·추가매수·익절 대응을 판단해줘.'

const fmt = (v, d = 1) => v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : Number(v).toLocaleString('ko-KR', { maximumFractionDigits: d })
const usd = (v) => v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : `$${Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
const pct = (v, d = 1) => v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : `${Number(v) >= 0 ? '+' : ''}${fmt(v, d)}%`
const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, Number(v)))
const ageText = (ts) => {
  if (!ts) return '시간 확인 중'
  const n = typeof ts === 'number' ? ts : new Date(ts).getTime()
  const ms = Date.now() - n
  if (!Number.isFinite(ms)) return '시간 확인 중'
  const sec = Math.max(0, Math.floor(ms / 1000))
  if (sec < 5) return '방금 갱신됨'
  if (sec < 60) return `${sec}초 전`
  const min = Math.floor(sec / 60)
  return min < 60 ? `${min}분 전` : `${Math.floor(min / 60)}시간 전`
}
const stanceMeta = (s) => ({ POSITIVE: ['좋음', 'positive'], NEGATIVE: ['주의', 'negative'], CAUTION: ['확인 필요', 'warning'], NEUTRAL: ['중립', 'neutral'] }[s] || ['확인 중', 'neutral'])
const valueTone = (v) => Number(v) > 0.05 ? 'positive' : Number(v) < -0.05 ? 'negative' : 'neutral'

function Badge({ children, tone = 'neutral' }) { return <span className={`badge badge-${tone}`}>{children}</span> }
function List({ items = [], empty = '표시할 내용이 없습니다.' }) {
  return items?.length ? <ul className="clean-list">{items.map((x, i) => <li key={i}>{String(x)}</li>)}</ul> : <p className="muted">{empty}</p>
}
function Action({ label, value }) {
  const tone = /줄|피하|적극/.test(value || '') ? 'negative' : /매수 검토|유지|서두르지/.test(value || '') ? 'positive' : 'warning'
  return <div className={`action-card action-${tone}`}><span>{label}</span><strong>{value || '—'}</strong></div>
}
function HealthDot({ label, data }) {
  const ok = data?.status === 'ok'
  return <div className="health-item" title={`${data?.provider || ''} · ${data?.cadence || ''}`}><i className={`dot ${ok ? 'ok' : 'bad'}`} /><span>{label}</span><small>{ok ? (data?.cadence || 'updated') : '없음'}</small></div>
}
function FactGrid({ entries }) {
  return <div className="fact-grid">{entries.map(([k, v]) => <div className="fact" key={k}><code>{k}</code><strong>{typeof v === 'number' ? fmt(v, 3) : String(v)}</strong></div>)}</div>
}
function PerformanceMatrix({ memory, regime }) {
  const rows = Object.entries(memory?.performance_matrix?.[regime] || {}).filter(([, v]) => Number(v?.samples || 0) > 0)
  if (!rows.length) return <p className="muted">현재 국면에서 쌓인 전문가 성과 표본이 아직 없습니다.</p>
  return <div className="performance-table">{rows.sort((a,b) => (b[1]?.samples || 0) - (a[1]?.samples || 0)).map(([domain, v]) => <div key={domain}><span>{domain}</span><strong>{Number(v.samples) >= 3 ? `${fmt(Number(v.aligned_rate || 0) * 100, 0)}%` : '표본 부족'}</strong><small>{v.samples}건</small></div>)}</div>
}

function PriceChart({ series = [], height = 120, zoom = 1, interactive = false }) {
  const [hover, setHover] = useState(null)
  const clean = series.filter((x) => Number.isFinite(Number(x?.close)))
  const count = Math.max(3, Math.ceil(clean.length / Math.max(1, zoom)))
  const data = clean.slice(-count)
  if (data.length < 2) return <div className="chart-empty">차트 데이터 확인 중</div>
  const values = data.map((x) => Number(x.close))
  const min = Math.min(...values); const max = Math.max(...values); const span = max - min || 1
  const w = 1000; const h = height
  const points = data.map((x, i) => `${(i / (data.length - 1)) * w},${h - 12 - ((Number(x.close) - min) / span) * (h - 24)}`).join(' ')
  const onMove = (e) => {
    if (!interactive) return
    const r = e.currentTarget.getBoundingClientRect(); const x = clamp((e.clientX - r.left) / r.width)
    setHover(Math.round(x * (data.length - 1)))
  }
  const hv = hover === null ? null : data[hover]
  const hx = hover === null ? null : (hover / (data.length - 1)) * w
  return <div className={`price-chart ${interactive ? 'interactive' : ''}`}>
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
      <line x1="0" y1={h - 12} x2={w} y2={h - 12} className="chart-baseline" />
      <polyline points={points} className="chart-line" />
      {hover !== null && <><line x1={hx} y1="4" x2={hx} y2={h - 8} className="chart-cross" /><circle cx={hx} cy={h - 12 - ((Number(hv.close) - min) / span) * (h - 24)} r="5" className="chart-dot" /></>}
    </svg>
    {hv && <div className="chart-tooltip"><strong>₩{fmt(hv.close, 0)}</strong><span>{new Date(hv.date).toLocaleString('ko-KR', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span></div>}
  </div>
}

function MetricCard({ label, value, meaning, series, onOpen }) {
  const tone = valueTone(value)
  return <button className="metric-card" onClick={onOpen} title="눌러서 차트 크게 보기">
    <div className="metric-copy"><span>{label}</span><strong className={`text-${tone}`}>{pct(value)}</strong><small>{meaning}</small></div>
    <div className="spark-wrap"><PriceChart series={series} height={52} /><span>확대 ↗</span></div>
  </button>
}

function RangeBar({ low, current, high }) {
  const valid = Number(low) > 0 && Number(high) >= Number(low) && Number(current) > 0
  if (!valid) return <div className="range-card muted">일중 고가/저가를 확인 중입니다.</div>
  const raw = (Number(current) - Number(low)) / (Number(high) - Number(low) || 1)
  const position = clamp(raw)
  const label = position >= .85 ? '일중 고점 부근' : position >= .6 ? '일중 범위 상단' : position >= .4 ? '일중 범위 중간' : position >= .15 ? '일중 범위 하단' : '일중 저점 부근'
  return <div className="range-card">
    <div className="range-heading"><div><span>현재 일중 위치</span><strong>{label}</strong></div><small>실시간 현재가 기준</small></div>
    <div className="range-track"><div className="range-fill" style={{ width: `${position * 100}%` }} /><i className="range-marker" style={{ left: `${position * 100}%` }} /></div>
    <div className="range-labels"><span><small>일중 저점</small>₩{fmt(low, 0)}</span><span className="range-current"><small>현재</small>₩{fmt(current, 0)}</span><span><small>일중 고점</small>₩{fmt(high, 0)}</span></div>
  </div>
}

function ChartModal({ open, onClose, series1m, series5m, series60m }) {
  const [frame, setFrame] = useState('1H')
  const [zoom, setZoom] = useState(1)
  useEffect(() => { if (open) { setFrame('1H'); setZoom(1) } }, [open])
  if (!open) return null
  const map = {
    '1H': (series1m || []).slice(-60),
    '4H': (series5m || []).slice(-48),
    '1D': (series60m || []).slice(-24),
    '3D': (series60m || []).slice(-72),
  }
  const data = map[frame] || []
  const first = data[0]?.close; const last = data[data.length - 1]?.close
  const change = first && last ? (Number(last) / Number(first) - 1) * 100 : null
  return <div className="modal-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
    <div className="chart-modal">
      <div className="modal-head"><div><span>BTC 가격 차트</span><h3>{frame} · {pct(change)}</h3></div><button onClick={onClose}>닫기 ×</button></div>
      <div className="chart-controls"><div className="segmented compact">{Object.keys(map).map((x) => <button key={x} className={frame === x ? 'active' : ''} onClick={() => { setFrame(x); setZoom(1) }}>{x}</button>)}</div><div className="zoom-buttons"><button onClick={() => setZoom(Math.max(1, zoom / 2))}>−</button><span>{zoom === 1 ? '전체' : `${zoom}× 확대`}</span><button onClick={() => setZoom(Math.min(8, zoom * 2))}>+</button></div></div>
      <PriceChart series={data} height={360} zoom={zoom} interactive />
      <p className="modal-note">마우스를 움직이면 해당 시점 가격을 확인할 수 있습니다. +/−로 최근 구간을 확대합니다.</p>
    </div>
  </div>
}

function useUpbitTicker(enabled = true) {
  const [tick, setTick] = useState(null)
  const [status, setStatus] = useState('connecting')
  const retry = useRef(null)
  useEffect(() => {
    if (!enabled) { setStatus('demo'); return undefined }
    let socket; let stopped = false; let delay = 1000
    const connect = () => {
      if (stopped) return
      setStatus('connecting')
      socket = new WebSocket('wss://api.upbit.com/websocket/v1')
      socket.binaryType = 'arraybuffer'
      socket.onopen = () => {
        delay = 1000; setStatus('live')
        socket.send(JSON.stringify([{ ticket: `btc-v41-${Date.now()}` }, { type: 'ticker', codes: ['KRW-BTC'], is_only_realtime: true }, { format: 'DEFAULT' }]))
      }
      socket.onmessage = async (ev) => {
        try {
          let text
          if (typeof ev.data === 'string') text = ev.data
          else if (ev.data instanceof Blob) text = await ev.data.text()
          else text = new TextDecoder().decode(ev.data)
          const x = JSON.parse(text)
          setTick({ price: x.trade_price, changePrevClose: Number(x.signed_change_rate || 0) * 100, dayHigh: x.high_price, dayLow: x.low_price, timestamp: x.timestamp || x.trade_timestamp, streamType: x.stream_type })
          setStatus('live')
        } catch (_) { /* REST fallback remains visible */ }
      }
      socket.onerror = () => setStatus('fallback')
      socket.onclose = () => { if (!stopped) { setStatus('fallback'); retry.current = setTimeout(connect, delay); delay = Math.min(delay * 2, 15000) } }
    }
    connect()
    return () => { stopped = true; if (retry.current) clearTimeout(retry.current); try { socket?.close() } catch (_) {} }
  }, [enabled])
  return { tick, status }
}

export default function App() {
  const [health, setHealth] = useState(null)
  const [usage, setUsage] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [liveRest, setLiveRest] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [source, setSource] = useState('live')
  const [selected, setSelected] = useState('NOW')
  const [question, setQuestion] = useState(DEFAULT_Q)
  const [chartOpen, setChartOpen] = useState(false)
  const { tick, status: wsStatus } = useUpbitTicker(source === 'live')

  const refreshLive = async (nextSource = source) => { try { setLiveRest(await getLive({ source: nextSource })) } catch (_) { /* websocket or last analysis remains visible */ } }
  const analyze = async (nextSource = source) => {
    setLoading(true); setError('')
    try { const result = await runAnalysis({ source: nextSource, question }); setAnalysis(result); setSource(nextSource); getUsage().then(setUsage).catch(() => {}); refreshLive(nextSource) }
    catch (e) { setError(e.message || String(e)) }
    finally { setLoading(false) }
  }
  useEffect(() => { getHealth().then(setHealth).catch(() => null); getUsage().then(setUsage).catch(() => null); analyze('live') }, [])
  useEffect(() => { refreshLive(source); const id = setInterval(() => refreshLive(source), source === 'live' ? 15000 : 60000); return () => clearInterval(id) }, [source])

  const a = analysis?.analysis
  const rest = liveRest?.live
  const livePrice = source === 'live' ? (tick?.price ?? rest?.ticker?.price ?? a?.latest?.live_price ?? a?.latest?.close) : (rest?.ticker?.price ?? a?.latest?.live_price ?? a?.latest?.close)
  const changePrevClose = source === 'live' ? (tick?.changePrevClose ?? rest?.ticker?.change_since_prev_close_pct ?? a?.live?.ticker?.change_since_prev_close_pct) : (rest?.ticker?.change_since_prev_close_pct ?? a?.live?.ticker?.change_since_prev_close_pct)
  const usdPrice = rest?.ticker?.price_usd ?? a?.live?.ticker?.price_usd
  const liveTs = source === 'live' ? (tick?.timestamp ?? rest?.ticker?.trade_timestamp ?? rest?.fetched_at) : rest?.fetched_at
  const hdata = a?.horizons?.[selected] || {}
  const [stanceLabel, stanceTone] = stanceMeta(hdata?.stance)
  const event = rest?.events?.[0] || a?.events?.[0]
  const m = rest?.metrics || a?.live?.metrics || {}
  const friendly = rest?.friendly || a?.live?.friendly || {}
  const validation = rest?.validation || a?.live?.validation || {}
  const user = a?.user_view || a?.explanation || {}
  const quota = analysis?.meta?.llm_usage?.quota || usage
  const liveState = source === 'demo' ? 'DEMO' : wsStatus === 'live' ? 'LIVE' : rest?.available ? 'REST' : 'OFFLINE'
  const signalMap = useMemo(() => Object.fromEntries((a?.signals || []).map((x) => [x.id, x])), [a])
  const selectedFacts = (hdata?.key_signal_ids || []).map((id) => signalMap[id]).filter(Boolean)
  const series1m = rest?.series_1m || a?.live?.series_1m || []
  const series5m = rest?.series_5m || a?.live?.series_5m || []
  const series60m = rest?.series_60m || a?.live?.series_60m || []

  const dayLow = source === 'live' ? (tick?.dayLow ?? rest?.ticker?.day_low ?? rest?.ticker?.low_24h) : (rest?.ticker?.day_low ?? rest?.ticker?.low_24h)
  const dayHigh = source === 'live' ? (tick?.dayHigh ?? rest?.ticker?.day_high ?? rest?.ticker?.high_24h) : (rest?.ticker?.day_high ?? rest?.ticker?.high_24h)
  const fromLow = livePrice && dayLow ? (Number(livePrice) / Number(dayLow) - 1) * 100 : m.rebound_from_24h_low_pct
  const fromHigh = livePrice && dayHigh ? (Number(livePrice) / Number(dayHigh) - 1) * 100 : m.pullback_from_24h_high_pct
  const liveOutsideRange = Number(livePrice) > 0 && Number(dayLow) > 0 && Number(dayHigh) > 0 && !(Number(dayLow) <= Number(livePrice) && Number(livePrice) <= Number(dayHigh))
  const qualityWarnings = [...(validation?.warnings || [])]
  if (liveOutsideRange) qualityWarnings.unshift('실시간 가격이 직전 REST 고가/저가 범위를 벗어났습니다. 범위 값을 다시 갱신하고 있습니다.')
  const cards = friendly?.cards || {}

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="btc-mark">₿</span><div><strong>BTC Agent</strong><small>V4.1 · Live Context + Reflection Memory</small></div></div>
      <div className="header-actions"><div className="segmented"><button className={source === 'live' ? 'active' : ''} onClick={() => analyze('live')}>Live</button><button className={source === 'demo' ? 'active' : ''} onClick={() => analyze('demo')}>Demo</button></div><button className="refresh-btn" disabled={loading} onClick={() => analyze(source)}>{loading ? '분석 중…' : 'AI 새로 분석'}</button></div>
    </header>

    <main>
      {error && <div className="error-box"><strong>분석 오류</strong><span>{error}</span></div>}
      {qualityWarnings.length > 0 && <div className="quality-alert"><strong>값을 다시 확인하는 중</strong><span>{qualityWarnings[0]}</span>{qualityWarnings.length > 1 && <small>추가 점검 {qualityWarnings.length - 1}건</small>}</div>}

      <section className="price-hero-v41">
        <div className="price-primary">
          <div className="live-line"><span className={`live-pill ${liveState.toLowerCase()}`}>● {liveState}</span><span>가격 {ageText(liveTs)}</span><span className="fresh-separator">·</span><span>AI {ageText(analysis?.meta?.generated_at)}</span></div>
          <p className="market-name">KRW-BTC · Upbit</p>
          <h1>₩{fmt(livePrice, 0)}</h1>
          <div className="dual-price"><strong>{usd(usdPrice)}</strong><span>BTC-USD 참고가 · {rest?.ticker?.usd_provider || a?.live?.ticker?.usd_provider || '확인 중'}</span></div>
          <div className={`day-change ${Number(changePrevClose) >= 0 ? 'up' : 'down'}`}>{pct(changePrevClose)} · 전일 종가 대비</div>
        </div>
        <div className="live-context">
          <span className="context-label">실시간 흐름</span>
          <h2>{event?.title || friendly?.headline || '단기 흐름을 확인 중입니다.'}</h2>
          <p>숫자는 실시간/단기 데이터로 계속 갱신되고, AI 판단은 별도 시점에 다시 계산됩니다.</p>
        </div>
      </section>

      <section className="live-metrics-grid">
        <MetricCard label={cards?.['1h']?.label || '최근 1시간'} value={m.return_1h_pct} meaning={cards?.['1h']?.meaning || '최근 한 시간 흐름'} series={series1m.slice(-60)} onOpen={() => setChartOpen(true)} />
        <MetricCard label={cards?.['4h']?.label || '최근 4시간'} value={m.return_4h_pct} meaning={cards?.['4h']?.meaning || '최근 몇 시간 방향'} series={series5m.slice(-48)} onOpen={() => setChartOpen(true)} />
        <div className="position-stat"><span>일중 저점에서</span><strong className={valueTone(fromLow) === 'negative' ? 'text-negative' : 'text-positive'}>{pct(fromLow)}</strong><small>저점 이후 회복한 폭</small></div>
        <div className="position-stat"><span>일중 고점에서</span><strong className={valueTone(fromHigh) === 'positive' ? 'text-positive' : 'text-negative'}>{pct(fromHigh)}</strong><small>고점까지 남은 거리</small></div>
      </section>
      <RangeBar low={dayLow} current={livePrice} high={dayHigh} />
      <button className="open-chart" onClick={() => setChartOpen(true)}>가격 차트 크게 보기 · 1H / 4H / 1D / 3D ↗</button>

      <section className="decision-card">
        <div className="decision-copy"><p className="eyebrow">현재 판단 · {analysis?.meta?.cached ? '캐시된 AI 분석' : '새 AI 분석'}</p><h2>{user?.headline || '시장 데이터를 분석하고 있습니다.'}</h2><p>{user?.summary || '실시간 가격은 계속 갱신되며, AI 분석은 별도 주기로 갱신됩니다.'}</p></div>
        <div className="actions-grid"><Action label="기존 보유" value={user?.actions?.hold} /><Action label="추가 매수" value={user?.actions?.add} /><Action label="익절" value={user?.actions?.take_profit} /></div>
      </section>

      {rest?.fast_view?.requires_ai_refresh && <div className="live-alert">시장 상태가 AI 분석 시점보다 많이 달라졌거나 데이터 재검증이 필요합니다. <button onClick={() => analyze(source)}>AI 판단도 다시 계산</button></div>}
      {event && <section className="event-card"><div className="event-icon">⚡</div><div><span>지금 포착된 움직임</span><h3>{event.title}</h3><p>{(event.facts || []).join(' · ')}</p></div></section>}

      <section className="horizon-panel">
        <div className="horizon-tabs">{HORIZONS.map((key) => { const [label, tone] = stanceMeta(a?.horizons?.[key]?.stance); return <button key={key} className={`${selected === key ? 'active' : ''} horizon-${tone}`} onClick={() => setSelected(key)}><strong>{H_LABEL[key]}</strong><span>{label}</span></button> })}</div>
        <div className="horizon-detail"><div className="horizon-title"><div><p className="eyebrow">{H_LABEL[selected]} 관점</p><h2>{hdata?.headline || '분석 중'}</h2></div><Badge tone={stanceTone}>{stanceLabel} · {fmt((hdata?.confidence || 0) * 100, 0)}%</Badge></div><p className="horizon-summary">{hdata?.summary || '—'}</p><div className="horizon-columns"><div><h4>좋게 보는 점</h4><List items={hdata?.good} empty="뚜렷한 긍정 신호 없음" /></div><div><h4>조심할 점</h4><List items={hdata?.risks} empty="뚜렷한 위험 신호 없음" /></div></div></div>
      </section>

      <section className="two-panels"><article className="simple-panel"><p className="eyebrow">AI가 보는 핵심</p><List items={user?.why} empty="분석 결과를 기다리는 중입니다." /></article><article className="simple-panel"><p className="eyebrow">다음에 바뀌면 다시 보기</p><List items={user?.watch} empty="조건을 계산 중입니다." /></article></section>

      <section className="data-strip"><div><strong>데이터 상태</strong><span>가격·달러 참고가·AI 분석의 갱신 시점을 분리해서 봅니다.</span></div><div className="health-grid">{Object.entries(a?.data_health || {}).map(([k, v]) => <HealthDot key={k} label={({ price: '원화 가격', usd_reference: '달러 참고가', intraday: '단기 흐름', derivatives: '선물', macro: '거시', news: '뉴스', etf_flow: 'ETF', sentiment: '심리', onchain_network: '네트워크', ml_30d: '30일 ML' }[k] || k)} data={v} />)}</div></section>

      <details className="advanced"><summary>상세 분석 · 지표 · 자기평가 기록 보기</summary><div className="advanced-inner">
        <section><h3>{H_LABEL[selected]} 핵심 근거</h3>{selectedFacts.length ? <div className="fact-grid">{selectedFacts.map((x) => <div className="fact" key={x.id}><code>{x.id}</code><strong>{x.fact}</strong><small>{x.domain} · {x.freshness}</small></div>)}</div> : <p className="muted">근거 없음</p>}</section>
        <section><h3>Reflection Memory</h3><div className="memory-head"><Badge tone="neutral">해결 {a?.memory?.resolved_count || 0}</Badge><Badge tone="neutral">평가 대기 {a?.memory?.pending_count || 0}</Badge></div><List items={(a?.memory?.recent_lessons || []).map((x) => x.lesson)} empty="아직 평가가 끝난 과거 판단이 없습니다. 실제 시간이 지나면 자동으로 쌓입니다." /></section>
        <section><h3>현재 국면에서 어떤 영역이 잘 맞았나</h3><p className="section-note">과거 표본 3건 미만은 가중치처럼 쓰지 않고 '표본 부족'으로 표시합니다.</p><PerformanceMatrix memory={a?.memory} regime={a?.regime?.regime || 'unknown'} /></section>
        <section><h3>실시간 데이터 검증</h3><Badge tone={validation?.status === 'ok' ? 'positive' : 'warning'}>{validation?.status === 'ok' ? '일관성 확인' : '재검증 필요'}</Badge><List items={validation?.warnings || []} empty="현재 스냅샷에서 명백한 값 충돌은 발견되지 않았습니다." /></section>
        <section><h3>실시간 지표</h3><FactGrid entries={Object.entries(m).filter(([, v]) => typeof v === 'number').slice(0, 36)} /></section>
        <section><h3>장기/모델 지표</h3><FactGrid entries={Object.entries(a?.latest || {}).filter(([, v]) => typeof v === 'number').slice(0, 30)} /></section>
        <section><h3>Critic</h3><Badge tone={a?.v4_critic?.passed ? 'positive' : 'warning'}>{a?.v4_critic?.passed ? '검증 통과' : '주의'}</Badge><List items={[...(a?.v4_critic?.issues || []), ...(a?.v4_critic?.warnings || [])]} empty="특이사항 없음" /></section>
        <section><h3>개발자용 Core</h3><pre>{JSON.stringify({ entry: a?.entry, exit: a?.exit, ml: a?.ml, regime: a?.regime, events: a?.events, external: a?.external, memory: a?.memory, reflection: a?.reflection, llm_usage: analysis?.meta?.llm_usage, logs: a?.logs }, null, 2)}</pre></section>
      </div></details>

      <section className="ask-panel"><div><strong>AI에게 추가로 물어보기</strong><span>기본 화면은 짧게, 필요할 때만 질문을 바꿉니다.</span></div><textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} maxLength={600} /><button className="refresh-btn" disabled={loading} onClick={() => analyze(source)}>이 질문으로 분석</button></section>
      <footer><span>API {health?.version || '—'} · {health?.llm_available ? 'LLM ON' : 'Fallback'} · {analysis?.meta?.cached ? 'cached analysis' : 'fresh analysis'}</span><span>{quota ? `AI quota ${quota.llm.ip_daily_used}/${quota.llm.ip_daily_limit}` : ''}</span><span>Decision support only · 제공처 지연/누락 시 별도 경고</span></footer>
    </main>
    <ChartModal open={chartOpen} onClose={() => setChartOpen(false)} series1m={series1m} series5m={series5m} series60m={series60m} />
  </div>
}
