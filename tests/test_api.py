import os

os.environ["USE_LLM"] = "false"

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "model_available" in body
    assert "llm_available" in body


def test_demo_analysis_contract():
    response = client.post(
        "/api/v1/analyze",
        json={"market": "KRW-BTC", "history_years": 8, "source": "demo"},
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["meta"]["source"] == "demo"
    analysis = body["analysis"]
    assert analysis["final_decision"]["action"] in {"매수", "관망", "비중축소"}
    assert len(analysis["series"]) <= 120
    assert analysis["logs"][-1] == "explanation_agent"
    assert analysis["explanation"]["headline"]


def test_upstream_failure_maps_to_502(monkeypatch):
    import requests
    from backend.main import analysis_service

    def fail(**kwargs):
        raise requests.ConnectionError("upstream offline")

    monkeypatch.setattr(analysis_service, "analyze", fail)
    response = client.post(
        "/api/v1/analyze",
        json={"market": "KRW-BTC", "history_years": 8, "source": "live"},
    )
    assert response.status_code == 502
    assert "시장 데이터 제공처" in response.json()["detail"]


def test_cors_preflight_for_local_frontend():
    response = client.options(
        "/api/v1/analyze",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
