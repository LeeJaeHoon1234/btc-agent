import os
os.environ["USE_LLM"] = "false"
os.environ["COST_GUARD_ENABLED"] = "false"

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_v4():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == "5.0.2"
    assert body["live_layer"] is True
    assert body["reflection_memory"] is True
    assert "model_available" in body and "llm_available" in body


def test_demo_live_endpoint_is_fast_layer_contract():
    response = client.get("/api/v1/live?source=demo&market=KRW-BTC")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["meta"]["version"] == "5.0.2"
    assert body["live"]["available"] is True
    assert body["live"]["ticker"]["price"] > 0
    assert "return_1h_pct" in body["live"]["metrics"]
    assert "orderbook_imbalance" in body["live"]["metrics"]
    assert body["live"]["ticker"]["price_usd"] > 0
    assert body["live"]["validation"]["status"] == "ok"
    assert body["live"]["friendly"]["cards"]["1h"]["label"] == "최근 1시간"
    assert body["live"]["series_60m"]


def test_demo_analysis_v4_contract():
    response = client.post("/api/v1/analyze", json={"market": "KRW-BTC", "history_years": 8, "source": "demo"})
    assert response.status_code == 200, response.text
    body = response.json(); a = body["analysis"]
    assert body["meta"]["version"] == "5.0.2"
    assert set(a["horizons"]) == {"NOW", "TODAY", "1W", "1M", "1Y"}
    assert a["user_view"]["actions"].keys() == {"hold", "add", "take_profit"}
    assert a["live"]["available"] is True
    assert len(a["signals"]) >= 20
    assert "price" in a["data_health"]
    assert a["logs"][-1] == "plain_language_writer"
    assert "memory" in a and "reflection" in a


def test_upstream_failure_maps_to_502(monkeypatch):
    import requests
    from backend.main import analysis_service
    def fail(**kwargs): raise requests.ConnectionError("upstream offline")
    monkeypatch.setattr(analysis_service, "analyze", fail)
    response = client.post("/api/v1/analyze", json={"market": "KRW-BTC", "history_years": 8, "source": "live"})
    assert response.status_code == 502


def test_cors_preflight_for_local_frontend():
    response = client.options("/api/v1/analyze", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "content-type"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_usage_endpoint():
    response = client.get("/api/v1/usage")
    assert response.status_code == 200
    body = response.json(); assert "request" in body and "llm" in body and body["scope"] == "process_memory"


def test_journal_endpoint_contract():
    response = client.get("/api/v1/journal")
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["version"] == "5.0.2"
    assert "records" in body["journal"] and "reflections" in body["journal"]


def test_demo_analysis_supports_english_ui_contract():
    response = client.post(
        "/api/v1/analyze",
        json={
            "market": "KRW-BTC",
            "history_years": 8,
            "source": "demo",
            "language": "en",
            "question": "Analyze BTC across NOW, TODAY, 1W, 1M, and 1Y horizons.",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json(); a = body["analysis"]
    assert body["meta"]["language"] == "en"
    assert a["user_view"]["language"] == "en"
    assert a["user_view"]["actions"]["hold"] in {"Hold", "Consider reducing"}
    assert a["horizons"]["NOW"]["headline"]
