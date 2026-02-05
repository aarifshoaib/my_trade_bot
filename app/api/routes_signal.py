"""Signal endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.signal_engine import signal_engine

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.get("/latest")
async def latest_signals():
    return signal_engine.get_recent_signals()


@router.get("/history")
async def signal_history():
    return signal_engine.get_recent_signals(limit=200)


@router.post("/toggle-auto")
async def toggle_auto(symbol: str, enabled: bool):
    signal_engine.set_auto_execute(symbol, enabled)
    return {"success": True, "symbol": symbol, "enabled": enabled}
