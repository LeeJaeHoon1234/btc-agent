import os
os.environ["USE_LLM"] = "false"

from src.tools.demo_data import make_demo_market_data
from src.tools.live_market import make_demo_live_snapshot
from src.tools.event_detector import detect_market_events
from src.tools.indicators import add_indicators
from src.tools.intraday_indicators import add_intraday_indicators


def test_daily_indicator_store_is_broad():
    df = add_indicators(make_demo_market_data(900, 5))
    expected = {"rsi14", "macd_hist", "bb_position", "atr14_pct", "adx14", "stoch_k", "obv_slope_10d", "ma200_gap_pct", "volatility_30d_pct"}
    assert expected.issubset(df.columns)
    assert df[list(expected)].tail(1).notna().sum(axis=1).iloc[0] >= 7


def test_intraday_indicator_store_and_event_detector():
    live = make_demo_live_snapshot(make_demo_market_data(500, 3))
    metrics = live["metrics"]
    for key in ["return_15m_pct", "return_1h_pct", "return_4h_pct", "rsi14", "vwap_gap_pct", "volume_zscore", "rebound_from_24h_low_pct"]:
        assert key in metrics
    events = detect_market_events(live, {"available": True, "funding_rate": 0.0008, "open_interest_change_24h_pct": 9.0})
    ids = {e["id"] for e in events}
    assert "oi_jump" in ids or "funding_crowding" in ids
