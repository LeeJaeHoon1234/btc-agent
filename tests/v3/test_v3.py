import os

os.environ["USE_LLM"] = "false"
os.environ["COST_GUARD_ENABLED"] = "false"

from fastapi.testclient import TestClient

from backend.main import app
from src.agents.v3.derivatives_agent import run_derivatives_agent
from src.agents.v3.planner_agent import make_research_plan
from src.core.v3.skill_registry import skill_registry

client = TestClient(app)


def test_skill_registry_loads_markdown_skills():
    names = set(skill_registry.names())
    assert {"technical", "derivatives", "macro", "news", "historical", "risk"}.issubset(names)
    assert "open interest" in skill_registry.get("derivatives").content.lower()


def test_planner_routes_derivatives_question():
    plan = make_research_plan("Funding and OI show a short squeeze? Should I take profit?")
    assert "derivatives" in plan["selected_skills"]
    assert "risk" in plan["selected_skills"]


def test_derivatives_agent_classifies_short_squeeze_from_tool_data():
    raw = {
        "available": True,
        "provider": "test",
        "funding_rate": -0.0001,
        "open_interest": 100.0,
        "open_interest_change_24h_pct": -5.0,
        "global_long_short_ratio": 0.9,
        "taker_buy_sell_ratio": 1.1,
    }
    result = run_derivatives_agent({"latest": {"return_3d": 7.0}}, raw=raw)
    assert result["regime"] == "SHORT_SQUEEZE"
    assert result["score"] > 0


def test_v3_demo_contract_contains_autonomous_research():
    response = client.post(
        "/api/v1/analyze",
        json={
            "market": "KRW-BTC",
            "history_years": 8,
            "source": "demo",
            "question": "Why is BTC moving and should I add or take profit?",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    analysis = body["analysis"]
    assert body["meta"]["version"] == "5.0.2"
    assert analysis["plan"]["selected_skills"]
    assert "derivatives" in analysis["experts"]
    assert "macro" in analysis["experts"]
    assert "news" in analysis["experts"]
    assert "historical" in analysis["experts"]
    assert analysis["research"]["stance"] in {"BULLISH", "MIXED", "BEARISH"}
    assert analysis["research_adjustment"]["bounded"] is True
    assert abs(analysis["research_adjustment"]["entry_delta"]) <= 8
    assert len(analysis["evidence"]) > 0
    assert analysis["plan"]["source"] == "v5_deterministic"
    assert "specialist_research" in analysis["logs"]


def test_skills_endpoint():
    response = client.get("/api/v1/skills")
    assert response.status_code == 200
    names = {x["name"] for x in response.json()["skills"]}
    assert "news" in names
