from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import threading
import uuid

HORIZON_HOURS = {"NOW": 4, "TODAY": 24, "1W": 24 * 7, "1M": 24 * 30, "1Y": 24 * 365}
OUTCOME_BANDS = {"NOW": 0.35, "TODAY": 0.6, "1W": 1.5, "1M": 4.0, "1Y": 10.0}
MAX_RECORDS = 1200
MAX_REFLECTIONS = 600
_LOCK = threading.RLock()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _direction(stance: str) -> int:
    stance = str(stance or "").upper()
    if stance == "POSITIVE":
        return 1
    if stance == "NEGATIVE":
        return -1
    return 0


def _outcome_direction(ret_pct: float, horizon: str) -> int:
    band = OUTCOME_BANDS.get(horizon, 1.0)
    if ret_pct > band:
        return 1
    if ret_pct < -band:
        return -1
    return 0


def _grade(expected: int, outcome: int) -> str:
    if expected == outcome:
        return "aligned"
    if expected == 0 and outcome != 0:
        return "too_cautious"
    if expected != 0 and outcome == 0:
        return "overconfident"
    return "opposite"


class PredictionJournal:
    """Small JSON journal for self-evaluation.

    It is intentionally advisory: memories are fed back as weak context, never as
    automatic parameter/threshold changes. On ephemeral hosting the file only
    persists for the life of the instance unless a persistent disk is configured.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        default = Path(__file__).resolve().parents[2] / "data" / "runtime" / "prediction_journal.json"
        self.path = Path(path or os.getenv("PREDICTION_JOURNAL_PATH", str(default)))

    def _empty(self) -> dict:
        return {"version": 2, "records": [], "reflections": []}

    def _load_unlocked(self) -> dict:
        if not self.path.exists():
            return self._empty()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return self._empty()
            data.setdefault("records", [])
            data.setdefault("reflections", [])
            return data
        except Exception:
            return self._empty()

    def _save_unlocked(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data["records"] = list(data.get("records", []))[-MAX_RECORDS:]
        data["reflections"] = list(data.get("reflections", []))[-MAX_REFLECTIONS:]
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def add_prediction(self, *, price: float, horizons: dict, signals: list[dict], regime: str | None, source: str = "live", now: datetime | None = None, forecasts: dict | None = None, market_state: dict | None = None, portfolio: dict | None = None, model_version: str = "5.0.2") -> list[str]:
        if not price or price <= 0:
            return []
        now = now or _utcnow()
        signal_map = {str(x.get("id")): x for x in signals}
        forecasts = forecasts or {}
        market_state = market_state or {}
        portfolio = portfolio or {}
        created: list[str] = []
        with _LOCK:
            data = self._load_unlocked()
            recent_cutoff = now - timedelta(minutes=15)
            for horizon, view in horizons.items():
                if horizon not in HORIZON_HOURS or not isinstance(view, dict):
                    continue
                duplicate = False
                for old in reversed(data.get("records", [])[-30:]):
                    if old.get("status") != "pending" or old.get("horizon") != horizon:
                        continue
                    created_at = _parse(old.get("created_at"))
                    if created_at and created_at >= recent_cutoff and str(old.get("stance")) == str(view.get("stance")):
                        duplicate = True
                        break
                if duplicate:
                    continue
                ids = [str(x) for x in (view.get("key_signal_ids") or [])][:6]
                evidence = []
                for sid in ids:
                    sig = signal_map.get(sid, {})
                    evidence.append({
                        "id": sid,
                        "domain": sig.get("domain"),
                        "direction": sig.get("direction"),
                        "strength": sig.get("strength"),
                        "fact": sig.get("simple") or sig.get("fact"),
                    })
                record_id = uuid.uuid4().hex[:16]
                data["records"].append({
                    "id": record_id,
                    "created_at": now.isoformat(),
                    "due_at": (now + timedelta(hours=HORIZON_HOURS[horizon])).isoformat(),
                    "resolved_at": None,
                    "status": "pending",
                    "source": source,
                    "horizon": horizon,
                    "stance": view.get("stance"),
                    "confidence": view.get("confidence"),
                    "headline": view.get("headline"),
                    "price": float(price),
                    "regime": regime or "unknown",
                    "market_state": market_state.get("regime"),
                    "model_version": model_version,
                    "forecast": {k: forecasts.get(horizon, {}).get(k) for k in [
                        "expected_return_pct", "median_return_pct", "q10_return_pct", "q90_return_pct",
                        "probability_up_pct", "confidence", "sample_count", "effective_sample_size", "method"
                    ] if forecasts.get(horizon, {}).get(k) is not None},
                    "portfolio": {k: portfolio.get(k) for k in ["target_exposure_pct", "recommended_change_pct", "next_exposure_pct"] if portfolio.get(k) is not None},
                    "evidence": evidence,
                })
                created.append(record_id)
            self._save_unlocked(data)
        return created

    def resolve_matured(self, *, current_price: float, now: datetime | None = None, max_items: int = 20) -> list[dict]:
        if not current_price or current_price <= 0:
            return []
        now = now or _utcnow()
        resolved: list[dict] = []
        with _LOCK:
            data = self._load_unlocked()
            for record in data.get("records", []):
                if len(resolved) >= max_items or record.get("status") != "pending":
                    continue
                due = _parse(record.get("due_at"))
                if due is None or due > now:
                    continue
                start = float(record.get("price") or 0)
                if start <= 0:
                    continue
                ret = (float(current_price) / start - 1) * 100
                horizon = str(record.get("horizon"))
                expected = _direction(record.get("stance"))
                outcome = _outcome_direction(ret, horizon)
                grade = _grade(expected, outcome)
                forecast = record.get("forecast") or {}
                p_up = forecast.get("probability_up_pct")
                expected_ret = forecast.get("expected_return_pct")
                q10 = forecast.get("q10_return_pct"); q90 = forecast.get("q90_return_pct")
                brier = None
                if p_up is not None:
                    p = max(0.0, min(1.0, float(p_up) / 100.0))
                    brier = (p - (1.0 if ret > 0 else 0.0)) ** 2
                abs_error = None if expected_ret is None else abs(ret - float(expected_ret))
                interval_hit = None if q10 is None or q90 is None else float(q10) <= ret <= float(q90)
                domains = sorted({str(x.get("domain")) for x in record.get("evidence", []) if x.get("domain")})
                if grade == "aligned":
                    lesson = f"{horizon} 판단은 실제 {ret:+.1f}% 움직임과 방향이 맞았습니다. 당시 선택한 근거는 참고하되 현재 데이터가 바뀌면 그대로 반복하지 않습니다."
                elif grade == "too_cautious":
                    lesson = f"{horizon}에서 중립/주의 판단 뒤 실제로 {ret:+.1f}% 움직였습니다. 다음 유사 상황에서는 강한 변화 신호를 과소평가했는지 먼저 점검합니다."
                elif grade == "overconfident":
                    lesson = f"{horizon}에서 방향성을 강하게 봤지만 실제 움직임은 {ret:+.1f}%로 제한적이었습니다. 같은 근거가 다시 나와도 확신도를 자동으로 높이지 않습니다."
                else:
                    lesson = f"{horizon} 판단과 실제 {ret:+.1f}% 움직임이 반대였습니다. {', '.join(domains[:3]) or '선택 근거'}를 다음 유사 국면에서 재검토합니다."
                reflection = {
                    "record_id": record.get("id"),
                    "resolved_at": now.isoformat(),
                    "horizon": horizon,
                    "regime": record.get("regime", "unknown"),
                    "expected_direction": expected,
                    "outcome_direction": outcome,
                    "return_pct": ret,
                    "grade": grade,
                    "domains": domains,
                    "evidence_ids": [x.get("id") for x in record.get("evidence", []) if x.get("id")],
                    "evidence": record.get("evidence", []),
                    "original_stance": record.get("stance"),
                    "original_confidence": record.get("confidence"),
                    "headline": record.get("headline"),
                    "forecast": forecast,
                    "forecast_metrics": {
                        "brier": None if brier is None else round(brier, 5),
                        "absolute_return_error_pct": None if abs_error is None else round(abs_error, 4),
                        "interval_80_hit": interval_hit,
                    },
                    "lesson": lesson,
                    "attention_up": [],
                    "attention_down": [],
                    "reflection_source": "structured",
                }
                record.update({
                    "status": "resolved", "resolved_at": now.isoformat(), "outcome_price": float(current_price),
                    "return_pct": ret, "grade": grade,
                    "forecast_metrics": {"brier": brier, "absolute_return_error_pct": abs_error, "interval_80_hit": interval_hit},
                })
                data["reflections"].append(reflection)
                resolved.append(reflection)
            self._save_unlocked(data)
        return resolved


    def apply_refinements(self, refinements: list[dict]) -> None:
        if not refinements:
            return
        by_id = {str(x.get("record_id")): x for x in refinements if x.get("record_id")}
        if not by_id:
            return
        with _LOCK:
            data = self._load_unlocked()
            changed = False
            for item in data.get("reflections", []):
                ref = by_id.get(str(item.get("record_id")))
                if not ref:
                    continue
                lesson = str(ref.get("lesson") or "").strip()
                if lesson:
                    item["lesson"] = lesson[:500]
                item["attention_up"] = [str(x)[:80] for x in (ref.get("attention_up") or [])][:4]
                item["attention_down"] = [str(x)[:80] for x in (ref.get("attention_down") or [])][:4]
                try:
                    item["reflection_confidence"] = max(0.0, min(1.0, float(ref.get("confidence", 0.6))))
                except (TypeError, ValueError):
                    item["reflection_confidence"] = 0.6
                item["reflection_source"] = "llm"
                changed = True
            if changed:
                self._save_unlocked(data)

    def memory_context(self, limit: int = 8) -> dict:
        with _LOCK:
            data = self._load_unlocked()
        reflections = list(data.get("reflections", []))
        recent = reflections[-limit:][::-1]
        stats: dict[str, dict[str, dict[str, float]]] = defaultdict(lambda: defaultdict(lambda: {"hits": 0, "total": 0}))
        for item in reflections:
            regime = str(item.get("regime") or "unknown")
            hit = item.get("grade") == "aligned"
            for domain in item.get("domains", []) or ["unknown"]:
                stats[regime][domain]["total"] += 1
                if hit:
                    stats[regime][domain]["hits"] += 1
        matrix: dict[str, dict[str, dict]] = {}
        for regime, domains in stats.items():
            matrix[regime] = {}
            for domain, values in domains.items():
                total = int(values["total"])
                hits = int(values["hits"])
                matrix[regime][domain] = {"samples": total, "aligned_rate": hits / total if total else None}
        return {
            "recent_lessons": recent,
            "performance_matrix": matrix,
            "resolved_count": len(reflections),
            "pending_count": sum(1 for x in data.get("records", []) if x.get("status") == "pending"),
            "persistence": "local_json",
        }

    def performance_summary(self) -> dict:
        with _LOCK:
            data = self._load_unlocked()
        reflections = list(data.get("reflections", []))
        by_horizon: dict[str, dict] = {}
        for horizon in HORIZON_HOURS:
            items = [x for x in reflections if x.get("horizon") == horizon]
            if not items:
                by_horizon[horizon] = {"resolved": 0}
                continue
            aligned = sum(1 for x in items if x.get("grade") == "aligned")
            metrics = [x.get("forecast_metrics") or {} for x in items]
            briers = [float(m["brier"]) for m in metrics if m.get("brier") is not None]
            errors = [float(m["absolute_return_error_pct"]) for m in metrics if m.get("absolute_return_error_pct") is not None]
            interval = [bool(m["interval_80_hit"]) for m in metrics if m.get("interval_80_hit") is not None]
            by_horizon[horizon] = {
                "resolved": len(items),
                "stance_alignment_rate": round(aligned / len(items), 4),
                "mean_brier": None if not briers else round(sum(briers) / len(briers), 5),
                "mean_absolute_return_error_pct": None if not errors else round(sum(errors) / len(errors), 4),
                "interval_80_coverage": None if not interval else round(sum(interval) / len(interval), 4),
            }
        total = len(reflections)
        return {
            "resolved_total": total,
            "pending_total": sum(1 for x in data.get("records", []) if x.get("status") == "pending"),
            "by_horizon": by_horizon,
            "note": "Live, timestamped decisions only; demo analyses are not included.",
        }

    def snapshot(self, record_limit: int = 30, reflection_limit: int = 30) -> dict:
        with _LOCK:
            data = self._load_unlocked()
        return {
            "records": list(data.get("records", []))[-record_limit:][::-1],
            "reflections": list(data.get("reflections", []))[-reflection_limit:][::-1],
            "memory": self.memory_context(limit=8),
            "performance": self.performance_summary(),
        }


prediction_journal = PredictionJournal()
