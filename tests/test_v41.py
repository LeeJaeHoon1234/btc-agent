from datetime import datetime, timedelta, timezone

from src.memory.prediction_journal import PredictionJournal
from src.tools.live_market import make_demo_live_snapshot


def test_v41_live_snapshot_has_readable_and_sanity_layers():
    live = make_demo_live_snapshot()
    assert live["ticker"]["price_usd"] > 0
    assert live["ticker"]["day_low"] <= live["ticker"]["price"] <= live["ticker"]["day_high"]
    assert live["validation"]["status"] == "ok"
    assert live["friendly"]["cards"]["1h"]["meaning"]
    assert len(live["series_1m"]) >= 60
    assert live["series_60m"]


def test_prediction_journal_resolves_and_builds_memory(tmp_path):
    path = tmp_path / "journal.json"
    journal = PredictionJournal(path)
    now = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    horizons = {"NOW": {"stance": "POSITIVE", "confidence": .7, "headline": "test", "key_signal_ids": ["S_PRICE"]}}
    signals = [{"id": "S_PRICE", "domain": "technical", "direction": 1, "strength": .8, "simple": "가격 상승"}]
    ids = journal.add_prediction(price=100.0, horizons=horizons, signals=signals, regime="sideways", now=now)
    assert len(ids) == 1
    resolved = journal.resolve_matured(current_price=105.0, now=now + timedelta(hours=5))
    assert resolved and resolved[0]["grade"] == "aligned"
    memory = journal.memory_context()
    assert memory["resolved_count"] == 1
    assert memory["recent_lessons"]
    assert memory["performance_matrix"]["sideways"]["technical"]["aligned_rate"] == 1.0
