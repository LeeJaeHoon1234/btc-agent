from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Literal

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.serializers import serialize_state
from backend.service import analysis_service
from config.settings import HISTORY_YEARS, MARKET, MODEL_PATH
from src.agents.llm_client import llm_available
from src.agents.v3.planner_agent import DEFAULT_QUESTION
from src.core.v3.skill_registry import skill_registry

logger = logging.getLogger(__name__)


class AnalysisRequest(BaseModel):
    market: str = Field(default=MARKET, min_length=3, max_length=30)
    history_years: int = Field(default=HISTORY_YEARS, ge=2, le=12)
    source: Literal["live", "demo"] = "live"
    question: str = Field(default=DEFAULT_QUESTION, min_length=3, max_length=600)


class HealthResponse(BaseModel):
    status: str
    version: str
    model_available: bool
    llm_available: bool
    default_market: str
    skill_count: int


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


app = FastAPI(
    title="BTC Agent V3 API",
    description="Autonomous BTC research and decision-support agent with skill routing, retrieval, external tools, Rule/ML and conditional LLM reasoning.",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept"],
)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"service": "BTC Agent V3 API", "version": "3.0.0", "docs": "/docs", "health": "/health", "skills": "/api/v1/skills"}


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version="3.0.0",
        model_available=MODEL_PATH.exists(),
        llm_available=llm_available(),
        default_market=MARKET,
        skill_count=len(skill_registry.names()),
    )


@app.get("/api/v1/skills")
def skills() -> dict:
    return {"skills": skill_registry.describe()}


@app.post("/api/v1/analyze")
def analyze(request: AnalysisRequest) -> dict:
    try:
        state, cached = analysis_service.analyze(
            market=request.market,
            history_years=request.history_years,
            source=request.source,
            question=request.question,
        )
    except (requests.RequestException, ConnectionError, TimeoutError) as exc:
        raise HTTPException(
            status_code=502,
            detail="시장 데이터 제공처에 연결하지 못했습니다. 잠시 뒤 다시 시도하거나 source='demo'로 확인하세요.",
        ) from exc
    except (ValueError, IndexError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"Analysis input/data error: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected analysis failure")
        raise HTTPException(status_code=500, detail="Internal analysis error.") from exc

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "version": "3.0.0",
            "market": request.market,
            "history_years": request.history_years,
            "source": request.source,
            "cached": cached,
        },
        "analysis": serialize_state(state),
    }
