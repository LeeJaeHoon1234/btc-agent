import React, { useEffect, useMemo, useRef, useState } from 'react'
import { getHealth, getLive, getUsage, runAnalysis } from './api.js'
import { DEFAULT_QUESTIONS, I18N, LANG_STORAGE_KEY, eventView, initialLanguage, liveHeadline, moveMeaning, reflectionLesson } from './i18n.js'

const HORIZONS = ['NOW', 'TODAY', '1W', '1M', '1Y']
const EXPOSURE_STORAGE_KEY = 'bitscope.currentExposurePct'
const fmt = (v, d = 1, lang = 'ko') => v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : Number(v).toLocaleString(lang === 'ko' ? 'ko-KR' : 'en-US', { maximumFractionDigits: d })
const usd = (v) => v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : `$${Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 })}`
const pct = (v, d = 1, lang = 'ko') => v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : `${Number(v) >= 0 ? '+' : ''}${fmt(v, d, lang)}%`
const clamp = (v, lo = 0, hi = 1) => Math.max(lo, Math.min(hi, Number(v)))
const ageText = (ts, lang = 'ko') => {
  const t = I18N[lang]
  if (!ts) return t.timeChecking
  const n = typeof ts === 'number' ? ts : new Date(ts).getTime()
  const ms = Date.now() - n
  if (!Number.isFinite(ms)) return t.timeChecking
  const sec = Math.max(0, Math.floor(ms / 1000))
  if (sec < 5) return t.justNow
  if (sec < 60) return t.secondsAgo(sec)
  const min = Math.floor(sec / 60)
  return min < 60 ? t.minutesAgo(min) : t.hoursAgo(Math.floor(min / 60))
}
const stanceMeta = (s, lang = 'ko') => {
  const tone = ({ POSITIVE: 'positive', NEGATIVE: 'negative', CAUTION: 'warning', NEUTRAL: 'neutral' }[s] || 'neutral')
  return [I18N[lang].stance[s] || I18N[lang].stance.UNKNOWN, tone]
}
const valueTone = (v) => Number(v) > 0.05 ? 'positive' : Number(v) < -0.05 ? 'negative' : 'neutral'
const signed = (v, d = 1, lang = 'ko') => v === null || v === undefined || Number.isNaN(Number(v)) ? '—' : `${Number(v) >= 0 ? '+' : ''}${fmt(v, d, lang)}`
const humanCode = (v = '') => String(v || '').replaceAll('_', ' ').replace(/\b\w/g, (m) => m.toUpperCase())
const councilStanceLabel = (stance, available, lang = 'ko') => {
  if (available === false) return lang === 'ko' ? '데이터 부족' : 'Unavailable'
  const s = String(stance || 'NEUTRAL').toUpperCase()
  if (lang === 'ko') return ({ BULLISH: '강세', BEARISH: '약세', NEUTRAL: '중립' }[s] || '중립')
  return ({ BULLISH: 'Bullish', BEARISH: 'Bearish', NEUTRAL: 'Neutral' }[s] || 'Neutral')
}
const marketStateLabel = (state, lang = 'ko') => {
  const key = String(state || '').toLowerCase()
  const ko = {
    range: '횡보', sideways: '횡보', strong_bull: '강한 상승', bull_pullback: '상승 중 조정',
    bull_flush_recovery: '상승 추세 내 급락 회복', bull_under_stress: '상승 추세 압박', leveraged_bull: '레버리지 동반 상승',
    recovery: '회복', flush_recovery: '급락 후 회복', leveraged_recovery: '레버리지 동반 회복',
    bear_trend: '하락 추세', bear_rally: '하락 추세 내 반등', capitulation: '투매', distribution: '분배/약세 전환',
    bear_acceleration: '하락 가속', range_break_shock: '횡보 이탈 급변', range_flush: '횡보 구간 급락',
    bull_trend: '상승 추세', bull_transition: '상승 전환', bear_transition: '하락 전환', unknown: '확인 중',
  }
  if (lang === 'ko') return ko[key] || humanCode(key || '—')
  return humanCode(key || '—')
}
const acuteStateLabel = (state, lang = 'ko') => {
  const key = String(state || 'normal').toLowerCase()
  const ko = {
    normal: '평온', volatility_shock_up: '단기 급등', volatility_shock_down: '단기 급락', long_flush: '롱 청산',
    leveraged_rally: '레버리지 상승', short_squeeze: '숏 스퀴즈', bearish_leverage: '하락 레버리지 확대', rebound_attempt: '반등 시도',
  }
  if (lang === 'ko') return ko[key] || marketStateLabel(key, lang)
  return humanCode(key)
}
const riskReasonLabel = (reason, lang = 'ko') => {
  if (lang !== 'ko') return reason
  const r = String(reason || '')
  const exact = {
    'too many evidence sources unavailable': '확인할 수 없는 보조 데이터가 많아 비중을 제한했습니다.',
    '1W historical-neighbor downside tail is severe': '1주 하방 시나리오가 매우 커 비중을 제한했습니다.',
    '1W downside tail is elevated': '1주 하방 위험이 평소보다 커 비중을 제한했습니다.',
    '1M downside tail is severe': '1개월 하방 시나리오가 매우 커 비중을 제한했습니다.',
    'long flush detected; recovery is not assumed': '롱 청산이 감지됐지만 회복을 확정적으로 가정하지 않습니다.',
    'severity-5 adverse market event': '강한 하락 이벤트가 감지돼 비중 상한을 낮췄습니다.',
    'severity-4 adverse market event': '하락 이벤트가 감지돼 비중 상한을 낮췄습니다.',
    'high agent disagreement': '전문 분석 간 의견 충돌이 커 비중을 보수적으로 제한했습니다.',
  }
  if (exact[r]) return exact[r]
  if (r.startsWith('critical data unavailable:')) return `핵심 데이터가 없어 신규 비중 확대를 막았습니다: ${r.split(':').slice(1).join(':').trim()}`
  if (r.startsWith('acute state:')) return `단기 급변 상태(${acuteStateLabel(r.split(':').slice(1).join(':').trim(), lang)})라 비중을 제한했습니다.`
  return r
}
const initialExposure = () => { try { const v = localStorage.getItem(EXPOSURE_STORAGE_KEY); return v === null ? '' : v } catch (_) { return '' } }

function Badge({ children, tone = 'neutral' }) { return <span className={`badge badge-${tone}`}>{children}</span> }
function List({ items = [], empty = '—' }) {
  return items?.length ? <ul className="clean-list">{items.map((x, i) => <li key={i}>{String(x)}</li>)}</ul> : <p className="muted">{empty}</p>
}
function Action({ label, value }) {
  const tone = /줄|피하|적극|reduce|avoid|aggressive/i.test(value || '') ? 'negative' : /매수 검토|유지|서두르지|hold|maintain|wait|do not rush/i.test(value || '') ? 'positive' : 'warning'
  return <div className={`action-card action-${tone}`}><span>{label}</span><strong>{value || '—'}</strong></div>
}
function HealthDot({ label, data, lang }) {
  const ok = data?.status === 'ok'
  return <div className="health-item" title={`${data?.provider || ''} · ${data?.cadence || ''}`}><i className={`dot ${ok ? 'ok' : 'bad'}`} /><span>{label}</span><small>{ok ? (data?.cadence || 'updated') : I18N[lang].unavailable}</small></div>
}
function FactGrid({ entries, lang }) {
  return <div className="fact-grid">{entries.map(([k, v]) => <div className="fact" key={k}><code>{k}</code><strong>{typeof v === 'number' ? fmt(v, 3, lang) : String(v)}</strong></div>)}</div>
}
function PerformanceMatrix({ memory, regime, lang }) {
  const t = I18N[lang]
  const rows = Object.entries(memory?.performance_matrix?.[regime] || {}).filter(([, v]) => Number(v?.samples || 0) > 0)
  if (!rows.length) return <p className="muted">{t.noPerformance}</p>
  return <div className="performance-table">{rows.sort((a,b) => (b[1]?.samples || 0) - (a[1]?.samples || 0)).map(([domain, v]) => <div key={domain}><span>{domain}</span><strong>{Number(v.samples) >= 3 ? `${fmt(Number(v.aligned_rate || 0) * 100, 0, lang)}%` : t.insufficient}</strong><small>{t.cases(v.samples)}</small></div>)}</div>
}


function ForecastCard({ forecast, horizon, lang }) {
  const t = I18N[lang]
  if (!forecast?.available) return <div className="forecast-empty">{t.forecastUnavailable}</div>
  const confidence = Number(forecast.confidence || 0) * 100
  return <div className="forecast-grid">
    <div><span>{t.expectedReturn}</span><strong className={`text-${valueTone(forecast.expected_return_pct)}`}>{pct(forecast.expected_return_pct, 1, lang)}</strong></div>
    <div><span>{t.probabilityUp}</span><strong>{fmt(forecast.probability_up_pct, 0, lang)}%</strong></div>
    <div><span>{t.downsideRange}</span><strong>{pct(forecast.q10_return_pct, 1, lang)}</strong></div>
    <div><span>{t.upsideRange}</span><strong>{pct(forecast.q90_return_pct, 1, lang)}</strong></div>
    <div><span>{t.forecastConfidence}</span><strong>{fmt(confidence, 0, lang)}%</strong></div>
    <div><span>{t.analogSamples}</span><strong>{forecast.sample_count ?? t.stateModel}</strong></div>
    <div className="forecast-range-row"><span>{t.centralRange}</span><div className="forecast-range"><i style={{ left: '10%' }} /><b style={{ left: '50%' }} /><i style={{ left: '90%' }} /></div><small>{pct(forecast.q10_return_pct, 1, lang)} → {pct(forecast.q90_return_pct, 1, lang)}</small></div>
  </div>
}

function CouncilPanel({ council, lang }) {
  const t = I18N[lang]
  const entries = Object.entries(council?.agents || {})
  if (!entries.length) return null
  const tone = (stance) => stance === 'BULLISH' ? 'positive' : stance === 'BEARISH' ? 'negative' : 'neutral'
  const sourceLabel = (source) => source === 'independent_specialist' ? t.specialistSource : t.fallbackSource
  return <section className="council-panel">
    <div className="section-heading"><div><p className="eyebrow">{t.agentCouncil}</p><h3>{t.agentCouncilTitle}</h3></div><Badge tone={Number(council?.disagreement || 0) >= .55 ? 'warning' : 'neutral'}>{t.disagreement} {fmt(Number(council?.disagreement || 0) * 100, 0, lang)}%</Badge></div>
    <div className="council-grid">{entries.map(([name, agent]) => {
      const isRisk = name === 'risk'
      const unavailable = agent?.available === false
      const badgeText = isRisk
        ? `${t.riskPressure} ${fmt(agent?.risk_pressure || 0, 0, lang)}/100`
        : unavailable
          ? councilStanceLabel(agent?.stance, false, lang)
          : `${councilStanceLabel(agent?.stance, true, lang)} · ${fmt(Number(agent?.confidence || 0) * 100, 0, lang)}%`
      const badgeTone = isRisk
        ? Number(agent?.risk_pressure || 0) >= 45 ? 'negative' : Number(agent?.risk_pressure || 0) >= 20 ? 'warning' : 'neutral'
        : unavailable ? 'warning' : tone(agent?.stance)
      return <article key={name} className={`council-agent council-${tone(agent?.stance)}`}>
        <div className="council-agent-head"><strong>{t.councilNames?.[name] || humanCode(name)}</strong><Badge tone={badgeTone}>{badgeText}</Badge></div>
        {!isRisk && <div className="council-agent-meta"><span>{sourceLabel(agent?.source)}</span>{Number(agent?.fact_count || 0) > 0 && <span>{t.evidenceCount(Number(agent.fact_count))}</span>}</div>}
        <p>{agent?.thesis || '—'}</p><small><b>{t.counterpoint}</b> {agent?.counterargument || '—'}</small>
      </article>
    })}</div>
  </section>
}

function PortfolioPanel({ portfolio, governor, marketState, currentExposure, setCurrentExposure, onApply, lang, loading }) {
  const t = I18N[lang]
  if (!portfolio && !governor) return null
  const levels = portfolio?.levels || {}
  const change = portfolio?.recommended_change_pct
  return <section className="portfolio-panel">
    <div className="portfolio-main">
      <div className="section-heading"><div><p className="eyebrow">{t.portfolioPlan}</p><h3>{t.targetExposure} {fmt(portfolio?.target_exposure_pct, 1, lang)}%</h3></div><Badge tone={governor?.capped ? 'warning' : 'positive'}>{governor?.capped ? t.riskCapped : t.riskPassed}</Badge></div>
      <div className="allocation-grid"><div><span>{t.currentExposure}</span><strong>{portfolio?.current_exposure_pct === null || portfolio?.current_exposure_pct === undefined ? t.notSet : `${fmt(portfolio.current_exposure_pct, 1, lang)}%`}</strong></div><div><span>{t.recommendedChange}</span><strong className={`text-${valueTone(change)}`}>{change === null || change === undefined ? '—' : `${signed(change, 1, lang)}%p`}</strong></div><div><span>{t.riskCeiling}</span><strong>{fmt(governor?.max_allowed_exposure_pct, 0, lang)}%</strong></div><div><span>{t.marketState}</span><strong>{marketStateLabel(marketState?.regime || '—', lang)}</strong><small>{acuteStateLabel(marketState?.acute_state || 'normal', lang)}</small></div></div>
      <div className="exposure-control"><label><span>{t.myExposure}</span><div><input type="number" min="0" max="100" step="1" placeholder="0–100" value={currentExposure} onChange={(e) => setCurrentExposure(e.target.value)} /><b>%</b></div></label><button className="refresh-btn" disabled={loading} onClick={onApply}>{t.applyExposure}</button><small>{t.exposureHelp}</small></div>
      {(governor?.reasons || []).length > 0 && <div className="governor-reasons"><strong>{t.governorReason}</strong><List items={governor.reasons.map((x) => riskReasonLabel(x, lang))} /></div>}
    </div>
    <div className="levels-panel"><p className="eyebrow">{t.scenarioLevels}</p><div className="levels-grid"><div><span>{t.entryZone}</span><strong>{levels?.entry_zone?.length ? `₩${fmt(levels.entry_zone[0],0,lang)} – ₩${fmt(levels.entry_zone[1],0,lang)}` : '—'}</strong></div><div><span>{t.addWeakness}</span><strong>{levels?.add_on_weakness_anchor ? `₩${fmt(levels.add_on_weakness_anchor,0,lang)}` : '—'}</strong></div><div><span>{t.invalidation}</span><strong>{levels?.invalidation_anchor ? `₩${fmt(levels.invalidation_anchor,0,lang)}` : '—'}</strong></div><div><span>{t.takeProfitLevels}</span><strong>{levels?.take_profit_1 ? `₩${fmt(levels.take_profit_1,0,lang)} / ₩${fmt(levels.take_profit_2,0,lang)}` : '—'}</strong></div></div><small>{t.scenarioNote}</small></div>
  </section>
}

function PriceChart({ series = [], height = 120, zoom = 1, interactive = false, lang = 'ko' }) {
  const [hover, setHover] = useState(null)
  const clean = series.filter((x) => Number.isFinite(Number(x?.close)))
  const count = Math.max(3, Math.ceil(clean.length / Math.max(1, zoom)))
  const data = clean.slice(-count)
  if (data.length < 2) return <div className="chart-empty">{I18N[lang].chartLoading}</div>
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
    {hv && <div className="chart-tooltip"><strong>₩{fmt(hv.close, 0, lang)}</strong><span>{new Date(hv.date).toLocaleString(lang === 'ko' ? 'ko-KR' : 'en-US', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</span></div>}
  </div>
}

function MetricCard({ label, value, meaning, series, onOpen, lang }) {
  const tone = valueTone(value)
  return <button className="metric-card" onClick={onOpen} title={I18N[lang].clickExpand}>
    <div className="metric-copy"><span>{label}</span><strong className={`text-${tone}`}>{pct(value, 1, lang)}</strong><small>{meaning}</small></div>
    <div className="spark-wrap"><PriceChart series={series} height={52} lang={lang} /><span>{I18N[lang].expand}</span></div>
  </button>
}

function RangeBar({ low, current, high, lang }) {
  const t = I18N[lang]
  const valid = Number(low) > 0 && Number(high) >= Number(low) && Number(current) > 0
  if (!valid) return <div className="range-card muted">{t.rangeLoading}</div>
  const raw = (Number(current) - Number(low)) / (Number(high) - Number(low) || 1)
  const position = clamp(raw)
  const label = position >= .85 ? t.rangeNearHigh : position >= .6 ? t.rangeUpper : position >= .4 ? t.rangeMiddle : position >= .15 ? t.rangeLower : t.rangeNearLow
  return <div className="range-card">
    <div className="range-heading"><div><span>{t.currentRange}</span><strong>{label}</strong></div><small>{t.realtimePrice}</small></div>
    <div className="range-track"><div className="range-fill" style={{ width: `${position * 100}%` }} /><i className="range-marker" style={{ left: `${position * 100}%` }} /></div>
    <div className="range-labels"><span><small>{t.dayLow}</small>₩{fmt(low, 0, lang)}</span><span className="range-current"><small>{t.current}</small>₩{fmt(current, 0, lang)}</span><span><small>{t.dayHigh}</small>₩{fmt(high, 0, lang)}</span></div>
  </div>
}

function ChartModal({ open, onClose, series1m, series5m, series60m, lang }) {
  const t = I18N[lang]
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
      <div className="modal-head"><div><span>{t.chartTitle}</span><h3>{frame} · {pct(change, 1, lang)}</h3></div><button onClick={onClose}>{t.close}</button></div>
      <div className="chart-controls"><div className="segmented compact">{Object.keys(map).map((x) => <button key={x} className={frame === x ? 'active' : ''} onClick={() => { setFrame(x); setZoom(1) }}>{x}</button>)}</div><div className="zoom-buttons"><button onClick={() => setZoom(Math.max(1, zoom / 2))}>−</button><span>{zoom === 1 ? t.whole : t.zoomed(zoom)}</span><button onClick={() => setZoom(Math.min(8, zoom * 2))}>+</button></div></div>
      <PriceChart series={data} height={360} zoom={zoom} interactive lang={lang} />
      <p className="modal-note">{t.chartNote}</p>
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
  const [lang, setLang] = useState(initialLanguage)
  const t = I18N[lang]
  const [health, setHealth] = useState(null)
  const [usage, setUsage] = useState(null)
  const [analysis, setAnalysis] = useState(null)
  const [liveRest, setLiveRest] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [source, setSource] = useState('live')
  const [selected, setSelected] = useState('NOW')
  const [question, setQuestion] = useState(() => DEFAULT_QUESTIONS[initialLanguage()])
  const [chartOpen, setChartOpen] = useState(false)
  const [currentExposure, setCurrentExposure] = useState(initialExposure)
  const { tick, status: wsStatus } = useUpbitTicker(source === 'live')

  const refreshLive = async (nextSource = source) => { try { setLiveRest(await getLive({ source: nextSource })) } catch (_) { /* websocket or last analysis remains visible */ } }
  const analyze = async (nextSource = source, nextLang = lang, nextQuestion = question, nextExposure = currentExposure) => {
    setLoading(true); setError('')
    const exposure = nextExposure === '' ? null : Number(nextExposure)
    try { const result = await runAnalysis({ source: nextSource, question: nextQuestion, language: nextLang, currentExposurePct: Number.isFinite(exposure) ? exposure : null }); setAnalysis(result); setSource(nextSource); getUsage().then(setUsage).catch(() => {}); refreshLive(nextSource) }
    catch (e) { setError(e.message || String(e)) }
    finally { setLoading(false) }
  }
  useEffect(() => { getHealth().then(setHealth).catch(() => null); getUsage().then(setUsage).catch(() => null); analyze('live', lang, question) }, [])
  useEffect(() => { refreshLive(source); const id = setInterval(() => refreshLive(source), source === 'live' ? 15000 : 60000); return () => clearInterval(id) }, [source])
  useEffect(() => { document.documentElement.lang = lang; document.title = lang === 'ko' ? 'BitScope — 비트코인 시장 인텔리전스' : 'BitScope — Bitcoin Market Intelligence' }, [lang])

  const changeLanguage = (nextLang) => {
    if (nextLang === lang) return
    const nextQuestion = question === DEFAULT_QUESTIONS[lang] ? DEFAULT_QUESTIONS[nextLang] : question
    setLang(nextLang)
    setQuestion(nextQuestion)
    try { localStorage.setItem(LANG_STORAGE_KEY, nextLang) } catch (_) {}
    document.documentElement.lang = nextLang
    analyze(source, nextLang, nextQuestion, currentExposure)
  }

  const a = analysis?.analysis
  const rest = liveRest?.live
  const livePrice = source === 'live' ? (tick?.price ?? rest?.ticker?.price ?? a?.latest?.live_price ?? a?.latest?.close) : (rest?.ticker?.price ?? a?.latest?.live_price ?? a?.latest?.close)
  const changePrevClose = source === 'live' ? (tick?.changePrevClose ?? rest?.ticker?.change_since_prev_close_pct ?? a?.live?.ticker?.change_since_prev_close_pct) : (rest?.ticker?.change_since_prev_close_pct ?? a?.live?.ticker?.change_since_prev_close_pct)
  const usdPrice = rest?.ticker?.price_usd ?? a?.live?.ticker?.price_usd
  const liveTs = source === 'live' ? (tick?.timestamp ?? rest?.ticker?.trade_timestamp ?? rest?.fetched_at) : rest?.fetched_at
  const hdata = a?.horizons?.[selected] || {}
  const [stanceLabel, stanceTone] = stanceMeta(hdata?.stance, lang)
  const rawEvent = rest?.events?.[0] || a?.events?.[0]
  const event = eventView(rawEvent, rest?.metrics || a?.live?.metrics || {}, lang)
  const m = rest?.metrics || a?.live?.metrics || {}
  const validation = rest?.validation || a?.live?.validation || {}
  const user = a?.user_view || a?.explanation || {}
  const quota = analysis?.meta?.llm_usage?.quota || usage
  const liveState = source === 'demo' ? 'DEMO' : wsStatus === 'live' ? 'LIVE' : rest?.available ? 'REST' : 'OFFLINE'
  const signalMap = useMemo(() => Object.fromEntries(((a?.facts?.length ? a.facts : a?.signals) || []).map((x) => [x.id, x])), [a])
  const selectedFacts = (hdata?.key_signal_ids || []).map((id) => signalMap[id]).filter(Boolean)
  const series1m = rest?.series_1m || a?.live?.series_1m || []
  const series5m = rest?.series_5m || a?.live?.series_5m || []
  const series60m = rest?.series_60m || a?.live?.series_60m || []
  const forecast = a?.forecasts?.[selected] || {}
  const applyExposure = () => { const n = Number(currentExposure); if (currentExposure === '' || (Number.isFinite(n) && n >= 0 && n <= 100)) { try { currentExposure === '' ? localStorage.removeItem(EXPOSURE_STORAGE_KEY) : localStorage.setItem(EXPOSURE_STORAGE_KEY, String(n)) } catch (_) {}; analyze(source, lang, question, currentExposure) } }

  const dayLow = source === 'live' ? (tick?.dayLow ?? rest?.ticker?.day_low ?? rest?.ticker?.low_24h) : (rest?.ticker?.day_low ?? rest?.ticker?.low_24h)
  const dayHigh = source === 'live' ? (tick?.dayHigh ?? rest?.ticker?.day_high ?? rest?.ticker?.high_24h) : (rest?.ticker?.day_high ?? rest?.ticker?.high_24h)
  const fromLow = livePrice && dayLow ? (Number(livePrice) / Number(dayLow) - 1) * 100 : m.rebound_from_24h_low_pct
  const fromHigh = livePrice && dayHigh ? (Number(livePrice) / Number(dayHigh) - 1) * 100 : m.pullback_from_24h_high_pct
  const liveOutsideRange = Number(livePrice) > 0 && Number(dayLow) > 0 && Number(dayHigh) > 0 && !(Number(dayLow) <= Number(livePrice) && Number(livePrice) <= Number(dayHigh))
  const qualityWarnings = [...(validation?.warnings || [])]
  if (liveOutsideRange) qualityWarnings.unshift(t.genericQualityWarning)
  const displayWarnings = lang === 'ko' ? qualityWarnings : (qualityWarnings.length ? [t.genericQualityWarning] : [])

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="btc-mark">₿</span><div><strong>BitScope</strong><small>{t.brandTagline}</small></div></div>
      <div className="header-actions"><div className="segmented language-toggle"><button className={lang === 'ko' ? 'active' : ''} onClick={() => changeLanguage('ko')}>KR</button><button className={lang === 'en' ? 'active' : ''} onClick={() => changeLanguage('en')}>EN</button></div><div className="segmented"><button className={source === 'live' ? 'active' : ''} onClick={() => analyze('live')}>Live</button><button className={source === 'demo' ? 'active' : ''} onClick={() => analyze('demo')}>Demo</button></div><button className="refresh-btn" disabled={loading} onClick={() => analyze(source)}>{loading ? t.analyzing : t.analyze}</button></div>
    </header>

    <main>
      {error && <div className="error-box"><strong>{t.analysisError}</strong><span>{error}</span></div>}
      {displayWarnings.length > 0 && <div className="quality-alert"><strong>{t.checkingValues}</strong><span>{displayWarnings[0]}</span>{qualityWarnings.length > 1 && <small>{t.extraChecks(qualityWarnings.length - 1)}</small>}</div>}

      <section className="price-hero-v41">
        <div className="price-primary">
          <div className="live-line"><span className={`live-pill ${liveState.toLowerCase()}`}>● {liveState}</span><span>{t.price} {ageText(liveTs, lang)}</span><span className="fresh-separator">·</span><span>{t.ai} {ageText(analysis?.meta?.generated_at, lang)}</span></div>
          <p className="market-name">{t.marketName}</p>
          <h1>₩{fmt(livePrice, 0, lang)}</h1>
          <div className="dual-price"><strong>{usd(usdPrice)}</strong><span>{t.usdRef} · {rest?.ticker?.usd_provider || a?.live?.ticker?.usd_provider || t.checking}</span></div>
          <div className={`day-change ${Number(changePrevClose) >= 0 ? 'up' : 'down'}`}>{pct(changePrevClose, 1, lang)} · {t.prevClose}</div>
        </div>
        <div className="live-context">
          <span className="context-label">{t.liveFlow}</span>
          <h2>{event?.title || liveHeadline(m, lang)}</h2>
          <p>{t.liveNote}</p>
        </div>
      </section>

      <section className="live-metrics-grid">
        <MetricCard label={t.last1h} value={m.return_1h_pct} meaning={moveMeaning(m.return_1h_pct, '1h', lang)} series={series1m.slice(-60)} onOpen={() => setChartOpen(true)} lang={lang} />
        <MetricCard label={t.last4h} value={m.return_4h_pct} meaning={moveMeaning(m.return_4h_pct, '4h', lang)} series={series5m.slice(-48)} onOpen={() => setChartOpen(true)} lang={lang} />
        <div className="position-stat"><span>{t.fromDayLow}</span><strong className={valueTone(fromLow) === 'negative' ? 'text-negative' : 'text-positive'}>{pct(fromLow, 1, lang)}</strong><small>{t.recoveredFromLow}</small></div>
        <div className="position-stat"><span>{t.fromDayHigh}</span><strong className={valueTone(fromHigh) === 'positive' ? 'text-positive' : 'text-negative'}>{pct(fromHigh, 1, lang)}</strong><small>{t.distanceToHigh}</small></div>
      </section>
      <RangeBar low={dayLow} current={livePrice} high={dayHigh} lang={lang} />
      <button className="open-chart" onClick={() => setChartOpen(true)}>{t.chartOpen}</button>

      <section className="decision-card">
        <div className="decision-copy"><p className="eyebrow">{t.currentDecision} · {analysis?.meta?.cached ? t.cachedAnalysis : t.freshAnalysis}</p><div className="state-badges"><Badge tone="neutral">{t.structure}: {marketStateLabel(a?.market_state?.structural_regime || a?.regime?.regime || 'unknown', lang)}</Badge><Badge tone={String(a?.market_state?.acute_state || "").includes("down") || String(a?.market_state?.acute_state || "").includes("flush") ? "warning" : "neutral"}>{t.nowState}: {acuteStateLabel(a?.market_state?.acute_state || 'normal', lang)}</Badge></div><h2>{user?.headline || t.analyzingMarket}</h2><p>{user?.summary || t.analysisRefreshNote}</p></div>
        <div className="actions-grid"><Action label={t.existingHold} value={user?.actions?.hold} /><Action label={t.add} value={user?.actions?.add} /><Action label={t.takeProfit} value={user?.actions?.take_profit} /></div>
      </section>
      <PortfolioPanel portfolio={a?.portfolio} governor={a?.risk_governor} marketState={a?.market_state} currentExposure={currentExposure} setCurrentExposure={setCurrentExposure} onApply={applyExposure} lang={lang} loading={loading} />

      {rest?.fast_view?.requires_ai_refresh && <div className="live-alert">{t.refreshNeeded} <button onClick={() => analyze(source)}>{t.recalcAI}</button></div>}
      {event && <section className="event-card"><div className="event-icon">⚡</div><div><span>{t.detectedMove}</span><h3>{event.title}</h3><p>{(event.facts || []).filter(Boolean).join(' · ')}</p></div></section>}

      <section className="horizon-panel">
        <div className="horizon-tabs">{HORIZONS.map((key) => { const [label, tone] = stanceMeta(a?.horizons?.[key]?.stance, lang); return <button key={key} className={`${selected === key ? 'active' : ''} horizon-${tone}`} onClick={() => setSelected(key)}><strong>{t.horizon[key]}</strong><span>{label}</span></button> })}</div>
        <div className="horizon-detail"><div className="horizon-title"><div><p className="eyebrow">{t.horizon[selected]} {t.perspective}</p><h2>{hdata?.headline || t.analyzingShort}</h2></div><Badge tone={stanceTone}>{stanceLabel} · {fmt((hdata?.confidence || 0) * 100, 0, lang)}%</Badge></div><p className="horizon-summary">{hdata?.summary || '—'}</p><ForecastCard forecast={forecast} horizon={selected} lang={lang} /><div className="horizon-columns"><div><h4>{t.positivePoints}</h4><List items={hdata?.good} empty={t.noPositive} /></div><div><h4>{t.riskPoints}</h4><List items={hdata?.risks} empty={t.noRisk} /></div></div></div>
      </section>
      <CouncilPanel council={a?.council} lang={lang} />

      <section className="two-panels"><article className="simple-panel"><p className="eyebrow">{t.keyAI}</p><List items={user?.why} empty={t.waitResult} /></article><article className="simple-panel"><p className="eyebrow">{t.recheckWhen}</p><List items={user?.watch} empty={t.calculating} /></article></section>

      <section className="data-strip"><div><strong>{t.dataStatus}</strong><span>{t.dataStatusNote}</span></div><div className="health-grid">{Object.entries(a?.data_health || {}).map(([k, v]) => <HealthDot key={k} label={t.health[k] || k} data={v} lang={lang} />)}</div></section>

      <details className="advanced"><summary>{t.advanced}</summary><div className="advanced-inner">
        <section><h3>{t.horizon[selected]} {t.coreEvidence}</h3>{selectedFacts.length ? <div className="fact-grid">{selectedFacts.map((x) => <div className="fact" key={x.id}><code>{x.id}</code><strong>{x.fact}</strong><small>{x.domain} · {x.freshness}</small></div>)}</div> : <p className="muted">{t.noEvidence}</p>}</section>
        <section><h3>{t.reflectionMemory}</h3><div className="memory-head"><Badge tone="neutral">{t.resolved} {a?.memory?.resolved_count || 0}</Badge><Badge tone="neutral">{t.pending} {a?.memory?.pending_count || 0}</Badge></div><List items={(a?.memory?.recent_lessons || []).map((x) => reflectionLesson(x, lang))} empty={t.noReflection} /></section>
        <section><h3>{t.performanceTitle}</h3><p className="section-note">{t.performanceNote}</p><PerformanceMatrix memory={a?.memory} regime={a?.market_state?.regime || a?.regime?.regime || 'unknown'} lang={lang} /></section>
        <section><h3>{t.trackRecord}</h3><div className="memory-head"><Badge tone="neutral">{t.resolved} {a?.track_record?.resolved_total || 0}</Badge><Badge tone="neutral">{t.pending} {a?.track_record?.pending_total || 0}</Badge></div>{Object.keys(a?.track_record?.by_horizon || {}).length ? <FactGrid entries={Object.entries(a.track_record.by_horizon).map(([k,v]) => [k, `${t.brier} ${fmt(v?.mean_brier,3,lang)} · ${t.coverage} ${fmt((v?.interval_80_coverage || 0)*100,0,lang)}%`])} lang={lang} /> : <p className="muted">{t.noTrackRecord}</p>}</section>
        <section><h3>{t.liveValidation}</h3><Badge tone={validation?.status === 'ok' ? 'positive' : 'warning'}>{validation?.status === 'ok' ? t.consistent : t.recheck}</Badge><List items={lang === 'ko' ? (validation?.warnings || []) : (validation?.warnings?.length ? [t.genericQualityWarning] : [])} empty={t.noConflict} /></section>
        <section><h3>{t.liveMetrics}</h3><FactGrid entries={Object.entries(m).filter(([, v]) => typeof v === 'number').slice(0, 36)} lang={lang} /></section>
        <section><h3>{t.longMetrics}</h3><FactGrid entries={Object.entries(a?.latest || {}).filter(([, v]) => typeof v === 'number').slice(0, 30)} lang={lang} /></section>
        <section><h3>Critic</h3><Badge tone={a?.v4_critic?.passed ? 'positive' : 'warning'}>{a?.v4_critic?.passed ? t.passed : t.caution}</Badge><List items={[...(a?.v4_critic?.issues || []), ...(a?.v4_critic?.warnings || [])]} empty={t.none} /></section>
        <section><h3>{t.developerCore}</h3><pre>{JSON.stringify({ forecasts: a?.forecasts, market_state: a?.market_state, council: a?.council, meta_decision: a?.meta_decision, risk_governor: a?.risk_governor, portfolio: a?.portfolio, entry: a?.entry, exit: a?.exit, ml: a?.ml, regime: a?.regime, events: a?.events, external: a?.external, memory: a?.memory, reflection: a?.reflection, llm_usage: analysis?.meta?.llm_usage, logs: a?.logs }, null, 2)}</pre></section>
      </div></details>

      <section className="ask-panel"><div><strong>{t.askAI}</strong><span>{t.askNote}</span></div><textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} maxLength={600} /><button className="refresh-btn" disabled={loading} onClick={() => analyze(source)}>{t.analyzeQuestion}</button></section>
      <footer><span>API {health?.version || '—'} · {health?.llm_available ? 'LLM ON' : 'Fallback'} · {analysis?.meta?.cached ? 'cached analysis' : 'fresh analysis'}</span><span>{quota ? `AI quota ${quota.llm.ip_daily_used}/${quota.llm.ip_daily_limit}` : ''}</span><span>{t.supportOnly}</span></footer>
    </main>
    <ChartModal open={chartOpen} onClose={() => setChartOpen(false)} series1m={series1m} series5m={series5m} series60m={series60m} lang={lang} />
  </div>
}
