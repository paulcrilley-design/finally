"""Health check."""

import os

from fastapi import APIRouter, Request

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/health")
async def health(request: Request) -> dict:
    status = request.app.state.market_source.status()
    market = {key: status[key] for key in ("mode", "degraded", "tickers")}
    return {
        "status": "degraded" if market["degraded"] else "ok",
        "market": market,
        "llm_mock": os.environ.get("LLM_MOCK", "").strip().lower() == "true",
    }
