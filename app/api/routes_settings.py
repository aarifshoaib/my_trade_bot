"""Settings and bot control endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.services.bot_state import bot_state

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.post("/bot/start")
async def start_bot():
    await bot_state.set_running(True, reason=None)
    return {"success": True, "status": "running"}


@router.post("/bot/stop")
async def stop_bot():
    await bot_state.set_running(False, reason="Stopped by user")
    return {"success": True, "status": "stopped"}


@router.post("/bot/pause")
async def pause_bot():
    await bot_state.set_paused(True, reason="Paused by user")
    return {"success": True, "status": "paused"}


@router.post("/bot/resume")
async def resume_bot():
    await bot_state.set_paused(False, reason=None)
    return {"success": True, "status": "running"}


@router.post("/bot/arm")
async def arm_bot():
    await bot_state.arm()
    return {"success": True, "armed": True}


@router.post("/bot/disarm")
async def disarm_bot():
    await bot_state.disarm("Disarmed by user")
    return {"success": True, "armed": False}
