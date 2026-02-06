"""Strategy endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.signal_engine import signal_engine

router = APIRouter(prefix="/api/v1/strategy", tags=["strategy"])


@router.get("/list")
async def list_strategies():
    return signal_engine.get_strategy_status()


@router.patch("/{name}/toggle")
async def toggle_strategy(name: str, enabled: bool):
    signal_engine.set_strategy_enabled(name, enabled)
    return {"success": True, "name": name, "enabled": enabled}


@router.patch("/{name}/params")
async def update_strategy_params(name: str, params: dict):
    signal_engine.set_strategy_params(name, params)
    return {"success": True, "name": name, "params": params}
