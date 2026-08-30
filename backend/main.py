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

logger = logging.getLogger(__name__)


class AnalysisRequest(BaseModel):
    market: str = Field(default=MARKET, min_length=3, max_length=30)
    history_years: int = Field(default=HISTORY_YEARS, ge=2, le=12)
    source: Literal["live", "demo"] = "live"


class HealthResponse(BaseModel):
    status: str
    model_available: bool
    llm_available: bool
    default_market: str


def _cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [item.strip().rstrip("/") for item in raw.split(",") if item.strip()]


app = FastAPI(
    title="BTC Agent API",
    description="Rule + ML + conditional LLM BTC decision-support agent.",
    version="2.1.0-web",
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
    return {
        "service": "BTC Agent API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        model_available=MODEL_PATH.exists(),
        llm_available=llm_available(),
        default_market=MARKET,
    )


@app.post("/api/v1/analyze")
def analyze(request: AnalysisRequest) -> dict:
    try:
        state, cached = analysis_service.analyze(
            market=request.market,
            history_years=request.history_years,
            source=request.source,
        )
    except (requests.RequestException, ConnectionError, TimeoutError) as exc:
        raise HTTPException(
            status_code=502,
            detail=(
                "시장 데이터 제공처에 연결하지 못했습니다. "
                "잠시 뒤 다시 시도하거나 source='demo'로 전체 파이프라인을 확인하세요."
            ),
        ) from exc
    except (ValueError, IndexError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"분석 입력/데이터 오류: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected analysis failure")
        raise HTTPException(status_code=500, detail="내부 분석 오류가 발생했습니다.") from exc

    return {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market": request.market,
            "history_years": request.history_years,
            "source": request.source,
            "cached": cached,
        },
        "analysis": serialize_state(state),
    }
