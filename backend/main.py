from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Literal

import requests
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.serializers import _clean, serialize_state
from backend.service import analysis_service, live_snapshot_service
from config.settings import HISTORY_YEARS, MARKET, MODEL_PATH
from src.agents.llm_client import llm_available
from src.agents.v3.planner_agent import DEFAULT_QUESTION
from src.core.v3.skill_registry import skill_registry
from src.core.v3.usage_guard import usage_guard
from src.memory.prediction_journal import prediction_journal

logger = logging.getLogger(__name__)
VERSION = "5.0.1"


class AnalysisRequest(BaseModel):
    market: str = Field(default=MARKET, min_length=3, max_length=30)
    history_years: int = Field(default=HISTORY_YEARS, ge=2, le=12)
    source: Literal["live", "demo"] = "live"
    question: str = Field(default=DEFAULT_QUESTION, min_length=3, max_length=600)
    language: Literal["ko", "en"] = "ko"
    current_exposure_pct: float | None = Field(default=None, ge=0, le=100)


class HealthResponse(BaseModel):
    status: str
    version: str
    model_available: bool
    llm_available: bool
    default_market: str
    skill_count: int
    cost_guard_enabled: bool
    live_layer: bool
    reflection_memory: bool


def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    raw_client = forwarded.split(",", 1)[0].strip() if forwarded else ""
    if not raw_client and request.client:
        raw_client = request.client.host
    return usage_guard.anonymize_client(raw_client)


app = FastAPI(
    title="BitScope API",
    description="Real-time multi-horizon Bitcoin market intelligence with deterministic data checks, specialist reasoning, and reflection memory.",
    version=VERSION,
)
app.add_middleware(CORSMiddleware, allow_origins=_cors_origins(), allow_credentials=False, allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type", "Accept"])


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "BitScope API", "version": VERSION, "docs": "/docs", "health": "/health", "live": "/api/v1/live", "usage": "/api/v1/usage", "journal": "/api/v1/journal"}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", version=VERSION, model_available=MODEL_PATH.exists(), llm_available=llm_available(), default_market=MARKET, skill_count=len(skill_registry.names()), cost_guard_enabled=usage_guard.enabled, live_layer=True, reflection_memory=True)


@app.get("/api/v1/skills")
def skills() -> dict:
    return {"skills": skill_registry.describe()}


@app.get("/api/v1/usage")
def usage(request: Request) -> dict:
    return usage_guard.status(_client_key(request))


@app.get("/api/v1/journal")
def journal() -> dict:
    """Recent self-evaluation history. No portfolio/account data is stored."""
    return {"meta": {"generated_at": datetime.now(timezone.utc).isoformat(), "version": VERSION}, "journal": _clean(prediction_journal.snapshot())}


@app.get("/api/v1/live")
def live(market: str = MARKET, source: Literal["live", "demo"] = "live") -> dict:
    try:
        snapshot, cached = live_snapshot_service.get(market=market, source=source)
    except requests.RequestException as exc:
        raise HTTPException(status_code=502, detail="실시간 시장 데이터 제공처에 연결하지 못했습니다.") from exc
    return {"meta": {"generated_at": datetime.now(timezone.utc).isoformat(), "version": VERSION, "market": market, "source": source, "cached": cached}, "live": _clean(snapshot)}


@app.post("/api/v1/analyze")
def analyze(payload: AnalysisRequest, request: Request) -> dict:
    client_key = _client_key(request)
    rate = usage_guard.register_request(client_key)
    if not rate.allowed:
        raise HTTPException(status_code=429, detail="Public analysis rate limit reached. Try again later.", headers={"Retry-After": str(rate.retry_after_seconds or 60)})
    try:
        state, cached, llm_usage = analysis_service.analyze(market=payload.market, history_years=payload.history_years, source=payload.source, question=payload.question, client_key=client_key, language=payload.language, current_exposure_pct=payload.current_exposure_pct)
    except (requests.RequestException, ConnectionError, TimeoutError) as exc:
        raise HTTPException(status_code=502, detail="시장 데이터 제공처에 연결하지 못했습니다. 잠시 뒤 다시 시도하거나 source='demo'로 확인하세요.") from exc
    except (ValueError, IndexError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"Analysis input/data error: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected analysis failure")
        raise HTTPException(status_code=500, detail="Internal analysis error.") from exc
    return {"meta": {"generated_at": datetime.now(timezone.utc).isoformat(), "version": VERSION, "market": payload.market, "history_years": payload.history_years, "source": payload.source, "language": payload.language, "cached": cached, "llm_usage": llm_usage}, "analysis": serialize_state(state)}
