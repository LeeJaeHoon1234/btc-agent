export const LANG_STORAGE_KEY = 'bitscope.lang'

export const DEFAULT_QUESTIONS = {
  ko: '현재 BTC를 NOW, TODAY, 1W, 1M, 1Y 관점에서 분석하고 보유·추가매수·익절 대응을 판단해줘.',
  en: 'Analyze BTC across NOW, TODAY, 1W, 1M, and 1Y horizons and assess whether to hold, add exposure, or take profit.',
}

export const I18N = {
  ko: {
    brandTagline: 'V5 · 예측분포 + 전문 분석 + 리스크 관리',
    analyze: 'AI 새로 분석', analyzing: '분석 중…', analysisError: '분석 오류',
    checkingValues: '값을 다시 확인하는 중', extraChecks: (n) => `추가 점검 ${n}건`,
    price: '가격', ai: 'AI', marketName: 'KRW-BTC · Upbit', usdRef: 'BTC-USD 참고가', checking: '확인 중', prevClose: '전일 종가 대비',
    liveFlow: '실시간 흐름', liveFallback: '단기 흐름을 확인 중입니다.', liveNote: '숫자는 실시간/단기 데이터로 계속 갱신되고, AI 판단은 별도 시점에 다시 계산됩니다.',
    last1h: '최근 1시간', last4h: '최근 4시간', oneHourFlow: '최근 한 시간 흐름', fourHourFlow: '최근 몇 시간 방향',
    fromDayLow: '일중 저점에서', recoveredFromLow: '저점 이후 회복한 폭', fromDayHigh: '일중 고점에서', distanceToHigh: '고점까지 남은 거리',
    chartOpen: '가격 차트 크게 보기 · 1H / 4H / 1D / 3D ↗',
    currentDecision: '현재 판단', cachedAnalysis: '캐시된 AI 분석', freshAnalysis: '새 AI 분석',
    structure: '큰 구조', nowState: '지금 상태', portfolioPlan: '포트폴리오 · 리스크 관리', targetExposure: '목표 BTC 비중', currentExposure: '현재 비중', recommendedChange: '권장 변화', riskCeiling: '리스크 상한', marketState: '시장 국면', notSet: '미입력', myExposure: '내 현재 BTC 비중', applyExposure: '비중 반영해 재분석', exposureHelp: '입력하지 않아도 시장 판단은 가능하고, 입력하면 목표 비중과 증감폭까지 계산합니다.', riskCapped: 'Risk cap 적용', riskPassed: 'Risk check 통과', governorReason: '비중을 제한한 이유',
    scenarioLevels: '시나리오 기준 가격', entryZone: '관심 진입 구간', addWeakness: '눌림 추가관찰', invalidation: '시나리오 무효화', takeProfitLevels: '상단 시나리오', scenarioNote: '예측분포에서 계산한 시나리오 앵커이며 자동 주문 가격이 아닙니다.',
    analyzingMarket: '시장 데이터를 분석하고 있습니다.', analysisRefreshNote: '실시간 가격은 계속 갱신되며, AI 분석은 별도 주기로 갱신됩니다.',
    existingHold: '기존 보유', add: '추가 매수', takeProfit: '익절',
    refreshNeeded: '시장 상태가 AI 분석 시점보다 많이 달라졌거나 데이터 재검증이 필요합니다.', recalcAI: 'AI 판단도 다시 계산',
    detectedMove: '지금 포착된 움직임', perspective: '관점', analyzingShort: '분석 중', positivePoints: '좋게 보는 점', riskPoints: '조심할 점',
    expectedReturn: '기대수익', probabilityUp: '상승확률', downsideRange: '하단 10%', upsideRange: '상단 10%', forecastConfidence: '분포 신뢰도', analogSamples: '유사 표본', stateModel: '상태모델', centralRange: '예상 분포 10–90%', forecastUnavailable: '이 시간축 예측분포를 계산할 수 없습니다.',
    agentCouncil: '전문 분석 의견', agentCouncilTitle: '각 영역을 따로 본 뒤 서로 비교합니다', disagreement: '의견 충돌', counterpoint: '틀릴 수 있는 조건:', councilNames: { technical: '기술적 구조', derivatives: '파생시장', onchain_flow: 'ETF·네트워크', macro: '거시', news: '뉴스·이벤트', historical: '과거 유사장', risk: '리스크' }, specialistSource: '전문 Agent', fallbackSource: '규칙 보조', evidenceCount: (n) => `근거 ${n}개`, riskPressure: '리스크 압력',
    noPositive: '뚜렷한 긍정 신호 없음', noRisk: '뚜렷한 위험 신호 없음', keyAI: 'AI가 보는 핵심', waitResult: '분석 결과를 기다리는 중입니다.',
    recheckWhen: '다음에 바뀌면 다시 보기', calculating: '조건을 계산 중입니다.', dataStatus: '데이터 상태', dataStatusNote: '가격·달러 참고가·AI 분석의 갱신 시점을 분리해서 봅니다.',
    advanced: '상세 분석 · 지표 · 자기평가 기록 보기', coreEvidence: '핵심 근거', noEvidence: '근거 없음', reflectionMemory: 'Reflection Memory', resolved: '해결', pending: '평가 대기',
    noReflection: '아직 평가가 끝난 과거 판단이 없습니다. 실제 시간이 지나면 자동으로 쌓입니다.', performanceTitle: '현재 국면에서 어떤 영역이 잘 맞았나', performanceNote: "과거 표본 3건 미만은 가중치처럼 쓰지 않고 '표본 부족'으로 표시합니다.",
    noPerformance: '현재 국면에서 쌓인 전문가 성과 표본이 아직 없습니다.', insufficient: '표본 부족', cases: (n) => `${n}건`, liveValidation: '실시간 데이터 검증', consistent: '일관성 확인', recheck: '재검증 필요',
    noConflict: '현재 스냅샷에서 명백한 값 충돌은 발견되지 않았습니다.', liveMetrics: '실시간 지표', longMetrics: '장기/모델 지표', passed: '검증 통과', caution: '주의', none: '특이사항 없음', developerCore: '개발자용 Core',
    trackRecord: 'Live Forecast Track Record', noTrackRecord: '아직 만기가 지난 실전 예측이 없습니다. 라이브 판단이 쌓이면 Brier score와 예측구간 적중률을 자동 평가합니다.', brier: 'Brier', coverage: '80% 구간 적중',
    askAI: 'AI에게 추가로 물어보기', askNote: '기본 화면은 짧게, 필요할 때만 질문을 바꿉니다.', analyzeQuestion: '이 질문으로 분석', supportOnly: 'Decision support only · 제공처 지연/누락 시 별도 경고',
    chartTitle: 'BTC 가격 차트', close: '닫기 ×', whole: '전체', zoomed: (z) => `${z}× 확대`, chartNote: '마우스를 움직이면 해당 시점 가격을 확인할 수 있습니다. +/−로 최근 구간을 확대합니다.', chartLoading: '차트 데이터 확인 중', expand: '확대 ↗', clickExpand: '눌러서 차트 크게 보기',
    rangeLoading: '일중 고가/저가를 확인 중입니다.', currentRange: '현재 일중 위치', realtimePrice: '실시간 현재가 기준', dayLow: '일중 저점', current: '현재', dayHigh: '일중 고점',
    rangeNearHigh: '일중 고점 부근', rangeUpper: '일중 범위 상단', rangeMiddle: '일중 범위 중간', rangeLower: '일중 범위 하단', rangeNearLow: '일중 저점 부근',
    timeChecking: '시간 확인 중', justNow: '방금 갱신됨', secondsAgo: (n) => `${n}초 전`, minutesAgo: (n) => `${n}분 전`, hoursAgo: (n) => `${n}시간 전`,
    stance: { POSITIVE: '좋음', NEGATIVE: '주의', CAUTION: '확인 필요', NEUTRAL: '중립', UNKNOWN: '확인 중' },
    health: { price: '원화 가격', usd_reference: '달러 참고가', intraday: '단기 흐름', derivatives: '선물', macro: '거시', news: '뉴스', etf_flow: 'ETF', sentiment: '심리', onchain_network: '네트워크', ml_30d: '30일 ML' },
    unavailable: '없음', horizon: { NOW: '지금', TODAY: '오늘', '1W': '1주', '1M': '1개월', '1Y': '1년' },
    genericQualityWarning: '최신 가격과 일부 보조 지표의 시점이 어긋나 재검증하고 있습니다.',
  },
  en: {
    brandTagline: 'V5 · Forecast + Agent Council + Risk Governor',
    analyze: 'Refresh AI analysis', analyzing: 'Analyzing…', analysisError: 'Analysis error',
    checkingValues: 'Rechecking market values', extraChecks: (n) => `${n} more checks`,
    price: 'Price', ai: 'AI', marketName: 'KRW-BTC · Upbit', usdRef: 'BTC-USD reference', checking: 'checking', prevClose: 'vs previous close',
    liveFlow: 'Live market context', liveFallback: 'Checking the short-term market structure.', liveNote: 'Live metrics keep updating independently; the AI view is refreshed on its own analysis cycle.',
    last1h: 'Last 1 hour', last4h: 'Last 4 hours', oneHourFlow: 'Very recent price direction', fourHourFlow: 'Short-term trend over several hours',
    fromDayLow: 'From intraday low', recoveredFromLow: 'Recovery since the low', fromDayHigh: 'From intraday high', distanceToHigh: 'Distance below the high',
    chartOpen: 'Open price chart · 1H / 4H / 1D / 3D ↗',
    currentDecision: 'Current view', cachedAnalysis: 'cached AI analysis', freshAnalysis: 'fresh AI analysis',
    structure: 'Structure', nowState: 'Current state', portfolioPlan: 'Portfolio · Risk Governor', targetExposure: 'Target BTC exposure', currentExposure: 'Current exposure', recommendedChange: 'Recommended change', riskCeiling: 'Risk ceiling', marketState: 'Market state', notSet: 'Not set', myExposure: 'My current BTC exposure', applyExposure: 'Apply & re-analyze', exposureHelp: 'The market view works without this input; add it to calculate a target exposure and exact change.', riskCapped: 'Risk cap applied', riskPassed: 'Risk check passed', governorReason: 'Why exposure was capped',
    scenarioLevels: 'Scenario price anchors', entryZone: 'Entry watch zone', addWeakness: 'Add-on-weakness watch', invalidation: 'Invalidation anchor', takeProfitLevels: 'Upside scenario', scenarioNote: 'These are forecast-distribution scenario anchors, not automatic order prices.',
    analyzingMarket: 'Analyzing the market.', analysisRefreshNote: 'The live price updates continuously while the AI analysis refreshes separately.',
    existingHold: 'Existing position', add: 'Add exposure', takeProfit: 'Take profit',
    refreshNeeded: 'The market has moved materially since the last AI analysis, or one of the data checks needs a refresh.', recalcAI: 'Refresh AI view',
    detectedMove: 'Move detected now', perspective: 'perspective', analyzingShort: 'Analyzing', positivePoints: 'What looks constructive', riskPoints: 'What needs caution',
    expectedReturn: 'Expected return', probabilityUp: 'Probability up', downsideRange: '10th percentile', upsideRange: '90th percentile', forecastConfidence: 'Distribution confidence', analogSamples: 'Analog samples', stateModel: 'State model', centralRange: 'Forecast 10–90% range', forecastUnavailable: 'A forecast distribution is not available for this horizon.',
    agentCouncil: 'Agent Council', agentCouncilTitle: 'Independent specialist views', disagreement: 'Disagreement', counterpoint: 'Counterpoint', councilNames: { technical: 'Technical', derivatives: 'Derivatives', onchain_flow: 'On-chain & flows', macro: 'Macro', news: 'News & events', historical: 'Historical analogs', risk: 'Risk' }, specialistSource: 'Specialist', fallbackSource: 'Rule fallback', evidenceCount: (n) => `${n} facts`, riskPressure: 'Risk pressure',
    noPositive: 'No clear positive signal', noRisk: 'No clear risk signal', keyAI: 'What matters most', waitResult: 'Waiting for the analysis.',
    recheckWhen: 'What would change the view', calculating: 'Calculating recheck conditions.', dataStatus: 'Data status', dataStatusNote: 'Price, USD reference, and AI-analysis freshness are tracked separately.',
    advanced: 'Detailed analysis · metrics · self-evaluation', coreEvidence: 'Core evidence', noEvidence: 'No evidence selected', reflectionMemory: 'Reflection Memory', resolved: 'Resolved', pending: 'Pending',
    noReflection: 'No matured historical decisions yet. Lessons appear after the relevant horizon has elapsed.', performanceTitle: 'Which domains have worked in this regime?', performanceNote: 'Fewer than 3 historical samples are treated as insufficient evidence, not as a weighting signal.',
    noPerformance: 'No specialist performance sample has accumulated for this regime yet.', insufficient: 'Insufficient', cases: (n) => `${n} samples`, liveValidation: 'Live data validation', consistent: 'Consistency passed', recheck: 'Recheck needed',
    noConflict: 'No obvious value conflict was detected in the current snapshot.', liveMetrics: 'Live metrics', longMetrics: 'Long-term / model metrics', passed: 'Validation passed', caution: 'Caution', none: 'No notable issue', developerCore: 'Developer core',
    trackRecord: 'Live Forecast Track Record', noTrackRecord: 'No live forecast has matured yet. Once enough time passes, Brier score and interval coverage are evaluated automatically.', brier: 'Brier', coverage: '80% coverage',
    askAI: 'Ask the AI a follow-up', askNote: 'Keep the main view short and change the question only when you need more detail.', analyzeQuestion: 'Analyze this question', supportOnly: 'Decision support only · source delays or gaps are shown separately',
    chartTitle: 'BTC price chart', close: 'Close ×', whole: 'Full', zoomed: (z) => `${z}× zoom`, chartNote: 'Move the pointer to inspect a point in time. Use +/− to zoom into the most recent section.', chartLoading: 'Loading chart data', expand: 'Expand ↗', clickExpand: 'Click to open the chart',
    rangeLoading: 'Checking the intraday high/low range.', currentRange: 'Current intraday position', realtimePrice: 'based on the live price', dayLow: 'Intraday low', current: 'Current', dayHigh: 'Intraday high',
    rangeNearHigh: 'Near the intraday high', rangeUpper: 'Upper part of today’s range', rangeMiddle: 'Middle of today’s range', rangeLower: 'Lower part of today’s range', rangeNearLow: 'Near the intraday low',
    timeChecking: 'checking time', justNow: 'updated just now', secondsAgo: (n) => `${n}s ago`, minutesAgo: (n) => `${n}m ago`, hoursAgo: (n) => `${n}h ago`,
    stance: { POSITIVE: 'Constructive', NEGATIVE: 'Risk', CAUTION: 'Needs confirmation', NEUTRAL: 'Neutral', UNKNOWN: 'Checking' },
    health: { price: 'KRW price', usd_reference: 'USD reference', intraday: 'Intraday', derivatives: 'Derivatives', macro: 'Macro', news: 'News', etf_flow: 'ETF', sentiment: 'Sentiment', onchain_network: 'Network', ml_30d: '30D ML' },
    unavailable: 'unavailable', horizon: { NOW: 'Now', TODAY: 'Today', '1W': '1 week', '1M': '1 month', '1Y': '1 year' },
    genericQualityWarning: 'The latest price and one or more supporting metrics are temporarily out of sync and are being revalidated.',
  },
}

export function initialLanguage() {
  try {
    const saved = localStorage.getItem(LANG_STORAGE_KEY)
    if (saved === 'ko' || saved === 'en') return saved
  } catch (_) {}
  return (navigator.language || '').toLowerCase().startsWith('ko') ? 'ko' : 'en'
}

export function moveMeaning(value, frame, lang) {
  const v = Number(value)
  if (!Number.isFinite(v)) return lang === 'ko' ? '확인 중' : 'checking'
  if (lang === 'ko') {
    if (v >= 1.5) return frame === '1h' ? '짧게 강한 상승' : '최근 몇 시간 강한 상승'
    if (v >= .25) return frame === '1h' ? '소폭 오르는 중' : '완만한 상승 흐름'
    if (v <= -1.5) return frame === '1h' ? '짧게 강한 하락' : '최근 몇 시간 강한 하락'
    if (v <= -.25) return frame === '1h' ? '소폭 눌리는 중' : '완만한 하락 흐름'
    return '큰 방향 없이 움직이는 중'
  }
  if (v >= 1.5) return frame === '1h' ? 'Strong short-term rise' : 'Strong rise over the last few hours'
  if (v >= .25) return frame === '1h' ? 'Modestly rising' : 'Gradual short-term rise'
  if (v <= -1.5) return frame === '1h' ? 'Sharp short-term drop' : 'Sharp drop over the last few hours'
  if (v <= -.25) return frame === '1h' ? 'Slightly pulling back' : 'Gradual short-term decline'
  return 'Moving without a clear short-term direction'
}

export function liveHeadline(metrics, lang) {
  const r1 = Number(metrics?.return_1h_pct)
  const r4 = Number(metrics?.return_4h_pct)
  if (!Number.isFinite(r1) && !Number.isFinite(r4)) return I18N[lang].liveFallback
  if (lang === 'ko') {
    if (r1 < -.2 && r4 > .2) return '방금은 조금 밀렸지만, 최근 몇 시간 흐름은 아직 플러스입니다.'
    if (r1 > .2 && r4 < -.2) return '방금 반등 중이지만, 최근 몇 시간 하락을 아직 다 되돌리진 못했습니다.'
    if (r1 > .2 && r4 > .2) return '짧은 시간과 최근 몇 시간 모두 상승 쪽입니다.'
    if (r1 < -.2 && r4 < -.2) return '짧은 시간과 최근 몇 시간 모두 약한 흐름입니다.'
    return '단기 방향은 아직 뚜렷하지 않습니다.'
  }
  if (r1 < -.2 && r4 > .2) return 'The market is pulling back now, but the last few hours are still positive.'
  if (r1 > .2 && r4 < -.2) return 'Price is rebounding now, but it has not fully recovered the earlier decline.'
  if (r1 > .2 && r4 > .2) return 'Both the very short-term move and the last few hours are pointing higher.'
  if (r1 < -.2 && r4 < -.2) return 'Both the very short-term move and the last few hours remain weak.'
  return 'The short-term direction is still mixed.'
}

export function eventView(event, metrics, lang) {
  if (!event) return null
  if (lang === 'ko') return event
  const v = (x, d = 2) => Number.isFinite(Number(x)) ? `${Number(x) >= 0 ? '+' : ''}${Number(x).toFixed(d)}%` : '—'
  const r15 = metrics?.return_15m_pct, r1 = metrics?.return_1h_pct, rebound = metrics?.rebound_from_24h_low_pct, pullback = metrics?.pullback_from_24h_high_pct
  const map = {
    fast_shock: { title: Number(r15) >= 0 ? '15-minute surge' : '15-minute selloff', facts: [`15m ${v(r15)}`] },
    hour_shock: { title: Number(r1) >= 0 ? '1-hour surge' : '1-hour selloff', facts: [`1h ${v(r1)}`] },
    flush_rebound: { title: 'Strong rebound after a sharp drop', facts: [`From intraday low ${v(rebound)}`, `Last 1h ${v(r1)}`] },
    high_rejection: { title: 'Fast rejection from the intraday high', facts: [`From intraday high ${v(pullback)}`] },
    volume_spike: { title: 'Volume spike', facts: ['Recent trading volume is unusually elevated'] },
    near_high: { title: 'Trading near the intraday high', facts: ['Price is near the top of today’s range'] },
    oi_jump: { title: 'Large change in futures positioning', facts: ['Open interest moved sharply over 24 hours'] },
    funding_crowding: { title: 'Leverage crowding risk', facts: ['Funding is unusually one-sided'] },
  }
  return { ...event, ...(map[event.id] || { title: 'Notable market move', facts: [] }) }
}

export function reflectionLesson(item, lang) {
  if (lang === 'ko') return item?.lesson
  const h = item?.horizon || 'This horizon'
  const ret = Number.isFinite(Number(item?.return_pct)) ? `${Number(item.return_pct) >= 0 ? '+' : ''}${Number(item.return_pct).toFixed(1)}%` : 'the realized move'
  if (item?.grade === 'aligned') return `${h} direction aligned with the realized ${ret} move. Keep the evidence as context, not as a rule.`
  if (item?.grade === 'too_cautious') return `${h} was too cautious before a realized ${ret} move. Recheck whether strong change signals were underweighted in similar setups.`
  if (item?.grade === 'overconfident') return `${h} expressed too much directional confidence while the realized move was only ${ret}. Do not automatically raise confidence when the same evidence returns.`
  return `${h} direction disagreed with the realized ${ret} move. Re-examine the selected evidence in a similar regime.`
}
