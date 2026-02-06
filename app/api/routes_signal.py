"""Signal endpoints."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter

from app.core.signal_engine import signal_engine
from app.config import settings

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.get("/latest")
async def latest_signals():
    return signal_engine.get_recent_signals()


@router.get("/history")
async def signal_history():
    return signal_engine.get_recent_signals(limit=200)


@router.get("/forecast")
async def signal_forecast():
    results = []
    for symbol in settings.symbol_list:
        signal = await asyncio.to_thread(signal_engine.generate_signal, symbol)
        if signal is None:
            results.append(
                {
                    "symbol": symbol,
                    "direction": "NEUTRAL",
                    "confidence": 0.0,
                    "strategy": "none",
                    "entry": 0.0,
                    "sl": 0.0,
                    "tp": 0.0,
                    "regime": "unknown",
                    "reason": "no_signal",
                }
            )
            continue
        results.append(
            {
                "symbol": signal.symbol,
                "direction": signal.direction.value,
                "confidence": signal.confidence,
                "strategy": signal.strategy_name,
                "entry": signal.entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "regime": "live",
                "reason": signal.reasoning,
            }
        )
    return results


@router.post("/toggle-auto")
async def toggle_auto(symbol: str, enabled: bool):
    signal_engine.set_auto_execute(symbol, enabled)
    return {"success": True, "symbol": symbol, "enabled": enabled}
