import streamlit as st

from src.core.orchestrator import BTCAgentOrchestrator


st.set_page_config(
    page_title="BTC Agent Harness v2",
    page_icon="₿",
    layout="wide",
)

st.title("₿ BTC Agent")
st.caption("복잡한 신호는 내부에서 분석하고, 화면에는 지금 필요한 결론부터 보여줍니다.")


def _action_icon(action: str) -> str:
    if action == "매수":
        return "🟢"
    if action == "비중축소":
        return "🔴"
    return "🟡"


def _market_text(regime: str | None) -> str:
    mapping = {
        "bull_trend": "상승 흐름",
        "bull_transition": "상승 전환 확인 중",
        "sideways": "방향 확인 중",
        "bear_transition": "하락 전환 경계",
        "bear_trend": "하락 흐름",
    }
    return mapping.get(regime, "확인 필요")


def _score_caption(score: float, kind: str) -> str:
    if kind == "entry":
        if score >= 80:
            return "매수 조건 강함"
        if score >= 70:
            return "매수 조건 충족"
        if score >= 65:
            return "매수 조건 거의 도달"
        if score >= 55:
            return "일부 매수 신호"
        return "매수 신호 약함"

    if score >= 88:
        return "고점 위험 매우 높음"
    if score >= 75:
        return "고점 위험 높음"
    if score >= 60:
        return "고점 위험 경계"
    if score >= 40:
        return "일부 과열"
    return "고점 위험 낮음"


if st.button("BTC 분석 실행", type="primary", use_container_width=True):
    try:
        with st.status("시장 데이터를 분석하고 있습니다...", expanded=True) as status:
            orchestrator = BTCAgentOrchestrator()
            state = orchestrator.run()
            status.update(label="분석 완료", state="complete", expanded=False)

        decision = state.final_decision
        explanation = state.explanation
        entry_score = float(state.entry.get("score", 50))
        exit_score = float(state.exit.get("score", 0))

        # ==========================================================
        # 1. 사람이 먼저 읽는 결론
        # ==========================================================
        st.subheader(f'{_action_icon(decision.action)} 현재 판단: {decision.action}')
        st.markdown(f"### {explanation.get('headline', decision.thesis)}")
        st.write(explanation.get("summary", decision.thesis))

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("BTC 가격", f'{state.latest["close"]:,.0f} 원')
        c2.metric("매수 매력도", f"{entry_score:.0f} / 100")
        c3.metric("고점 위험도", f"{exit_score:.0f} / 100")
        c4.metric("판단 확신도", f"{decision.confidence:.0%}")

        p1, p2 = st.columns(2)
        with p1:
            st.write(f"**매수 상태:** {_score_caption(entry_score, 'entry')}")
            st.progress(min(100, max(0, int(round(entry_score)))))
        with p2:
            st.write(f"**고점 상태:** {_score_caption(exit_score, 'exit')}")
            st.progress(min(100, max(0, int(round(exit_score)))))

        st.write(f"**현재 시장:** {_market_text(state.regime.get('regime'))}")

        # ==========================================================
        # 2. 왜 이런 판단인지
        # ==========================================================
        st.divider()
        st.subheader("왜 이렇게 판단했나")

        good_col, caution_col = st.columns(2)
        with good_col:
            st.markdown("#### ✅ 좋은 신호")
            positives = explanation.get("positives", [])
            if positives:
                for item in positives:
                    st.write(f"• {item}")
            else:
                st.write("• 현재 뚜렷하게 강한 긍정 신호는 많지 않습니다.")

        with caution_col:
            st.markdown("#### ⚠️ 주의할 점")
            cautions = explanation.get("cautions", [])
            if cautions:
                for item in cautions:
                    st.write(f"• {item}")
            else:
                st.write("• 현재 특별히 큰 위험 신호는 많지 않습니다.")

        # ==========================================================
        # 3. 지금 할 행동
        # ==========================================================
        st.divider()
        st.subheader("지금 어떻게 할까")
        for item in explanation.get("strategy", []):
            st.write(f"• {item}")

        recheck = explanation.get("recheck", [])
        if recheck:
            st.markdown("#### 다시 판단할 조건")
            for item in recheck:
                st.write(f"• {item}")

        # ==========================================================
        # 4. 가격 차트
        # ==========================================================
        st.divider()
        st.subheader("가격 흐름")
        chart_df = (
            state.market_df[["date", "close", "ma20", "ma200", "ma350"]]
            .dropna()
            .tail(730)
            .set_index("date")
        )
        st.line_chart(chart_df)

        # ==========================================================
        # 5. 전문 데이터는 접어 둔다.
        # ==========================================================
        with st.expander("상세 분석 보기"):
            st.markdown("### 점수와 분석 경로")
            c1, c2, c3 = st.columns(3)
            c1.metric("Entry Score", f"{entry_score:.2f}")
            c2.metric("Exit Score", f"{exit_score:.2f}")
            c3.metric("Gate Confidence", f'{state.gate.confidence:.0%}')

            st.write("**분석 경로:**", state.gate.route)
            st.write("**시장 분류:**", state.regime.get("regime"))
            st.write("**사이클 단계:**", state.cycle.get("stage"))

            if state.gate.reasons:
                st.write("**추가 분석이 필요하다고 판단한 이유**")
                for reason in state.gate.reasons:
                    st.write(f"• {reason}")

            st.markdown("### 최종 판단 원문")
            st.write("**Thesis:**", decision.thesis)

            if decision.reasons:
                st.write("**근거**")
                for reason in decision.reasons:
                    st.write(f"• {reason}")

            if decision.invalidation:
                st.write("**재판단 조건**")
                for item in decision.invalidation:
                    st.write(f"• {item}")

            st.markdown("### 내부 데이터")
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Technical Agent**")
                st.json(state.technical)
                st.write("**ML Predictor**")
                st.json(state.ml)
                st.write("**Market State**")
                st.json(state.regime)
                st.write("**Similar Periods**")
                st.json(state.similarity)

            with col2:
                st.write("**Cycle Analysis**")
                st.json(state.cycle)
                st.write("**Entry Engine**")
                st.json(state.entry)
                st.write("**Exit Engine**")
                st.json(state.exit)
                st.write("**Risk Agent**")
                st.json(state.risk)

            st.markdown("### 반론 검토")
            if not state.critiques:
                st.info("이번 분석은 추가 반론 검토가 필요하지 않은 경로로 처리됐습니다.")
            else:
                for i, critique in enumerate(state.critiques, start=1):
                    st.write(
                        f"**검토 {i}** — 통과={critique.passed}, "
                        f"중요도={critique.severity}, source={critique.source}"
                    )
                    for issue in critique.issues:
                        st.write(f"• {issue}")
                    if critique.revision_instructions:
                        st.write("**수정 제안**")
                        for item in critique.revision_instructions:
                            st.write(f"• {item}")

            st.markdown("### 실행 순서")
            st.code(" -> ".join(state.logs))

        st.caption(
            "현재 고점 위험 분석은 가격 기반 신호가 중심입니다. "
            "온체인·ETF·파생상품 데이터는 이후 단계에서 추가할 수 있습니다."
        )
        st.warning("이 결과는 투자 의사결정 보조용이며 수익을 보장하지 않습니다.")

    except Exception as e:
        st.error(f"실행 중 오류: {e}")
        st.exception(e)
