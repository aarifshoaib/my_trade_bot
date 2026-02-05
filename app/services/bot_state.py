"""Bot state and live-arming controls."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.config import settings


@dataclass
class BotStatus:
    running: bool = True
    paused: bool = False
    armed: bool = False
    reason: str | None = None


class BotState:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._status = BotStatus(running=True, paused=False, armed=False)
        self._auto_trade = settings.AUTO_TRADE

    async def get_status(self) -> BotStatus:
        async with self._lock:
            return BotStatus(
                running=self._status.running,
                paused=self._status.paused,
                armed=self._status.armed,
                reason=self._status.reason,
            )

    async def arm(self) -> None:
        async with self._lock:
            self._status.armed = True
            self._status.reason = None

    async def disarm(self, reason: str) -> None:
        async with self._lock:
            self._status.armed = False
            self._status.reason = reason

    async def set_paused(self, paused: bool, reason: str | None = None) -> None:
        async with self._lock:
            self._status.paused = paused
            self._status.reason = reason

    async def set_running(self, running: bool, reason: str | None = None) -> None:
        async with self._lock:
            self._status.running = running
            self._status.reason = reason

    async def set_auto_trade(self, enabled: bool) -> None:
        async with self._lock:
            self._auto_trade = enabled

    async def get_auto_trade(self) -> bool:
        async with self._lock:
            return self._auto_trade


bot_state = BotState()
