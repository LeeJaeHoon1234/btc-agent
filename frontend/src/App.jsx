import React, { useEffect, useMemo, useRef, useState } from 'react'
import { API_BASE_URL, getHealth, getLive, getUsage, runAnalysis } from './api.js'

const HORIZONS = ['NOW', 'TODAY', '1W', '1M', '1Y']
const H_LABEL = { NOW: '지금', TODAY: '오늘', '1W': '1주', '1M': '1개월', '1Y': '1년' }
const DEFAULT_Q = '현재 BTC를 NOW, TODAY, 1W, 1M, 1Y 관점에서 분석하고 보유·추가매수·익절 대응을 판단해줘.'

const fmt = (v, d = 1) => v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : Number(v).toLocaleString('ko-KR', { maximumFractionDigits: d })
const pct = (v, d = 1) => v === null || v === undefined ? '—' : `${Number(v) >= 0 ? '+' : ''}${fmt(v, d)}%`
const ageText = (ts) => {
  if (!ts) return '시간 확인 중'
  const n = typeof ts === 'number' ? ts : new Date(ts).getTime()
  const ms = Date.now() - n
  if (!Number.isFinite(ms)) return '시간 확인 중'
  const sec = Math.max(0, Math.floor(ms / 1000))
  if (sec < 5) return '방금 업데이트'
  if (sec < 60) return `${sec}초 전`
  const min = Math.floor(sec / 60)
  return min < 60 ? `${min}분 전` : `${Math.floor(min / 60)}시간 전`
}
const stanceMeta = (s) => ({ POSITIVE: ['좋음', 'positive'], NEGATIVE: ['주의', 'negative'], CAUTION: ['확인 필요', 'warning'], NEUTRAL: ['중립', 'neutral'] }[s] || ['확인 중', 'neutral'])

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
function Metric({ label, value }) { return <div className="mini-stat"><span>{label}</span><strong>{value}</strong></div> }
function FactGrid({ entries }) {
  return <div className="fact-grid">{entries.map(([k, v]) => <div className="fact" key={k}><code>{k}</code><strong>{typeof v === 'number' ? fmt(v, 3) : String(v)}</strong></div>)}</div>
}

function useUpbitTicker(enabled = true) {
  const [tick, setTick] = useState(null)
  const [status, setStatus] = useState('connecting')
  const retry = useRef(null)
  useEffect(() => {
    if (!enabled) { setStatus('demo'); return undefined }
    let socket
    let stopped = false
    let delay = 1000
    const connect = () => {
      if (stopped) return
      setStatus('connecting')
      socket = new WebSocket('wss://api.upbit.com/websocket/v1')
      socket.binaryType = 'arraybuffer'
      socket.onopen = () => {
        delay = 1000
        setStatus('live')
        socket.send(JSON.stringify([{ ticket: `btc-v4-${Date.now()}` }, { type: 'ticker', codes: ['KRW-BTC'], is_only_realtime: true }, { format: 'DEFAULT' }]))
      }
      socket.onmessage = async (ev) => {
        try {
          let text
          if (typeof ev.data === 'string') text = ev.data
          else if (ev.data instanceof Blob) text = await ev.data.text()
          else text = new TextDecoder().decode(ev.data)
          const x = JSON.parse(text)
          setTick({ price: x.trade_price, change24h: Number(x.signed_change_rate || 0) * 100, high24h: x.high_price, low24h: x.low_price, timestamp: x.timestamp || x.trade_timestamp, streamType: x.stream_type })
          setStatus('live')
        } catch (_) { /* keep REST fallback */ }
      }
      socket.onerror = () => setStatus('fallback')
      socket.onclose = () => {
        if (!stopped) {
          setStatus('fallback')
          retry.current = setTimeout(connect, delay)
          delay = Math.min(delay * 2, 15000)
        }
      }
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
  const { tick, status: wsStatus } = useUpbitTicker(source === 'live')

  const refreshLive = async (nextSource = source) => {
    try { setLiveRest(await getLive({ source: nextSource })) } catch (_) { /* websocket or last analysis remains visible */ }
  }
  const analyze = async (nextSource = source) => {
    setLoading(true); setError('')
    try {
      const result = await runAnalysis({ source: nextSource, question })
      setAnalysis(result); setSource(nextSource)
      getUsage().then(setUsage).catch(() => {})
      refreshLive(nextSource)
    } catch (e) { setError(e.message || String(e)) }
    finally { setLoading(false) }
  }

  useEffect(() => { getHealth().then(setHealth).catch(() => null); getUsage().then(setUsage).catch(() => null); analyze('live') }, [])
  useEffect(() => { refreshLive(source); const id = setInterval(() => refreshLive(source), source === 'live' ? 15000 : 60000); return () => clearInterval(id) }, [source])

  const a = analysis?.analysis
  const rest = liveRest?.live
  const livePrice = source === 'live' ? (tick?.price ?? rest?.ticker?.price ?? a?.latest?.live_price ?? a?.latest?.close) : (rest?.ticker?.price ?? a?.latest?.live_price ?? a?.latest?.close)
  const change24h = source === 'live' ? (tick?.change24h ?? rest?.ticker?.change_24h_pct ?? a?.live?.ticker?.change_24h_pct) : (rest?.ticker?.change_24h_pct ?? a?.live?.ticker?.change_24h_pct)
  const liveTs = source === 'live' ? (tick?.timestamp ?? rest?.ticker?.trade_timestamp ?? rest?.fetched_at) : rest?.fetched_at
  const hdata = a?.horizons?.[selected] || {}
  const [stanceLabel, stanceTone] = stanceMeta(hdata?.stance)
  const event = rest?.events?.[0] || a?.events?.[0]
  const m = rest?.metrics || a?.live?.metrics || {}
  const user = a?.user_view || a?.explanation || {}
  const quota = analysis?.meta?.llm_usage?.quota || usage
  const liveState = source === 'demo' ? 'DEMO' : wsStatus === 'live' ? 'LIVE' : rest?.available ? 'REST' : 'OFFLINE'
  const signalMap = useMemo(() => Object.fromEntries((a?.signals || []).map((x) => [x.id, x])), [a])
  const selectedFacts = (hdata?.key_signal_ids || []).map((id) => signalMap[id]).filter(Boolean)

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="btc-mark">₿</span><div><strong>BTC Agent</strong><small>V4 · Multi-Horizon Intelligence</small></div></div>
      <div className="header-actions">
        <div className="segmented"><button className={source === 'live' ? 'active' : ''} onClick={() => analyze('live')}>Live</button><button className={source === 'demo' ? 'active' : ''} onClick={() => analyze('demo')}>Demo</button></div>
        <button className="refresh-btn" disabled={loading} onClick={() => analyze(source)}>{loading ? '분석 중…' : 'AI 새로 분석'}</button>
      </div>
    </header>

    <main>
      {error && <div className="error-box"><strong>분석 오류</strong><span>{error}</span></div>}

      <section className="price-hero">
        <div>
          <div className="live-line"><span className={`live-pill ${liveState.toLowerCase()}`}>● {liveState}</span><span>{ageText(liveTs)}</span></div>
          <p className="market-name">KRW · Bitcoin</p>
          <h1>{fmt(livePrice, 0)} ₩</h1>
          <div className={`day-change ${Number(change24h) >= 0 ? 'up' : 'down'}`}>{pct(change24h)} · 24시간</div>
        </div>
        <div className="price-side"><Metric label="1시간" value={pct(m.return_1h_pct)} /><Metric label="4시간" value={pct(m.return_4h_pct)} /><Metric label="저점 대비" value={pct(m.rebound_from_24h_low_pct)} /><Metric label="고점 대비" value={pct(m.pullback_from_24h_high_pct)} /></div>
      </section>

      <section className="decision-card">
        <div className="decision-copy"><p className="eyebrow">현재 판단 · AI 분석 {ageText(analysis?.meta?.generated_at)}</p><h2>{user?.headline || '시장 데이터를 분석하고 있습니다.'}</h2><p>{user?.summary || '실시간 가격은 계속 갱신되며, AI 분석은 별도 주기로 갱신됩니다.'}</p></div>
        <div className="actions-grid"><Action label="기존 보유" value={user?.actions?.hold} /><Action label="추가 매수" value={user?.actions?.add} /><Action label="익절" value={user?.actions?.take_profit} /></div>
      </section>

      {rest?.fast_view?.requires_ai_refresh && <div className="live-alert">시장 움직임이 크게 바뀌었습니다. 실시간 이벤트를 먼저 반영했습니다. 필요하면 <button onClick={() => analyze(source)}>AI 판단도 갱신</button></div>}
      {event && <section className="event-card"><div className="event-icon">⚡</div><div><span>지금 포착된 움직임</span><h3>{event.title}</h3><p>{(event.facts || []).join(' · ')}</p></div></section>}

      <section className="horizon-panel">
        <div className="horizon-tabs">{HORIZONS.map((key) => { const [label, tone] = stanceMeta(a?.horizons?.[key]?.stance); return <button key={key} className={`${selected === key ? 'active' : ''} horizon-${tone}`} onClick={() => setSelected(key)}><strong>{H_LABEL[key]}</strong><span>{label}</span></button> })}</div>
        <div className="horizon-detail">
          <div className="horizon-title"><div><p className="eyebrow">{H_LABEL[selected]} 관점</p><h2>{hdata?.headline || '분석 중'}</h2></div><Badge tone={stanceTone}>{stanceLabel} · {fmt((hdata?.confidence || 0) * 100, 0)}%</Badge></div>
          <p className="horizon-summary">{hdata?.summary || '—'}</p>
          <div className="horizon-columns"><div><h4>좋게 보는 점</h4><List items={hdata?.good} empty="뚜렷한 긍정 신호 없음" /></div><div><h4>조심할 점</h4><List items={hdata?.risks} empty="뚜렷한 위험 신호 없음" /></div></div>
        </div>
      </section>

      <section className="two-panels"><article className="simple-panel"><p className="eyebrow">AI가 보는 핵심</p><List items={user?.why} empty="분석 결과를 기다리는 중입니다." /></article><article className="simple-panel"><p className="eyebrow">다음에 바뀌면 다시 보기</p><List items={user?.watch} empty="조건을 계산 중입니다." /></article></section>

      <section className="data-strip"><div><strong>데이터 상태</strong><span>가격과 분석의 업데이트 주기를 따로 표시합니다.</span></div><div className="health-grid">{Object.entries(a?.data_health || {}).map(([k, v]) => <HealthDot key={k} label={({ price: '가격', intraday: '단기 흐름', derivatives: '선물', macro: '거시', news: '뉴스', etf_flow: 'ETF', sentiment: '심리', onchain_network: '네트워크', ml_30d: '30일 ML' }[k] || k)} data={v} />)}</div></section>

      <details className="advanced"><summary>상세 분석 · 지표 · 근거 보기</summary><div className="advanced-inner">
        <section><h3>{H_LABEL[selected]} 핵심 근거</h3>{selectedFacts.length ? <div className="fact-grid">{selectedFacts.map((x) => <div className="fact" key={x.id}><code>{x.id}</code><strong>{x.fact}</strong><small>{x.domain} · {x.freshness}</small></div>)}</div> : <p className="muted">근거 없음</p>}</section>
        <section><h3>실시간 지표</h3><FactGrid entries={Object.entries(m).filter(([, v]) => typeof v === 'number').slice(0, 30)} /></section>
        <section><h3>장기/모델 지표</h3><FactGrid entries={Object.entries(a?.latest || {}).filter(([, v]) => typeof v === 'number').slice(0, 30)} /></section>
        <section><h3>Critic</h3><Badge tone={a?.v4_critic?.passed ? 'positive' : 'warning'}>{a?.v4_critic?.passed ? '검증 통과' : '주의'}</Badge><List items={[...(a?.v4_critic?.issues || []), ...(a?.v4_critic?.warnings || [])]} empty="특이사항 없음" /></section>
        <section><h3>개발자용 Core</h3><pre>{JSON.stringify({ entry: a?.entry, exit: a?.exit, ml: a?.ml, regime: a?.regime, research: a?.research, events: a?.events, external: a?.external, llm_usage: analysis?.meta?.llm_usage, logs: a?.logs }, null, 2)}</pre></section>
      </div></details>

      <section className="ask-panel"><div><strong>AI에게 추가로 물어보기</strong><span>기본 화면은 짧게, 필요할 때만 질문을 바꿉니다.</span></div><textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} maxLength={600} /><button className="refresh-btn" disabled={loading} onClick={() => analyze(source)}>이 질문으로 분석</button></section>
      <footer><span>API {health?.version || '—'} · {health?.llm_available ? 'LLM ON' : 'Fallback'} · {analysis?.meta?.cached ? 'cached analysis' : 'fresh analysis'}</span><span>{quota ? `AI quota ${quota.llm.ip_daily_used}/${quota.llm.ip_daily_limit}` : ''}</span><span>Decision support only · 데이터는 제공처별 지연/누락 가능</span></footer>
    </main>
  </div>
}
