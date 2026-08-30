from src.core.orchestrator import BTCAgentOrchestrator


def main():
    orchestrator = BTCAgentOrchestrator()
    state = orchestrator.run()

    decision = state.final_decision
    explanation = state.explanation

    print("\n===== BTC AGENT =====")
    print("날짜:", state.latest["date"])
    print("가격:", f'{state.latest["close"]:,.0f} KRW')
    print("매수 매력도:", f'{state.entry.get("score", 0):.1f}/100')
    print("고점 위험도:", f'{state.exit.get("score", 0):.1f}/100')
    print("Route:", state.gate.route if state.gate else None)

    print("\n===== 쉬운 요약 =====")
    print("판단:", decision.action)
    print("한줄:", explanation.get("headline", decision.thesis))
    print("요약:", explanation.get("summary", ""))

    print("\n좋은 신호:")
    for item in explanation.get("positives", []):
        print("-", item)

    print("\n주의할 점:")
    for item in explanation.get("cautions", []):
        print("-", item)

    print("\n지금 전략:")
    for item in explanation.get("strategy", []):
        print("-", item)

    print("\n다시 판단할 조건:")
    for item in explanation.get("recheck", []):
        print("-", item)

    if state.critiques:
        print("\n===== CRITIC LOOP =====")
        for i, critique in enumerate(state.critiques, start=1):
            print(f"Critic {i}: passed={critique.passed}, severity={critique.severity}")
            for issue in critique.issues:
                print("  -", issue)

    print("\nExecution Log:", " -> ".join(state.logs))


if __name__ == "__main__":
    main()
