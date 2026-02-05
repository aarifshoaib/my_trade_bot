"""Health check endpoint."""
from __future__ import annotations

from datetime import datetime
import time

from fastapi import APIRouter

from app.core.mt5_connector import mt5_connector
from app.models.schemas import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    mt5_connected = mt5_connector.is_connected()
    account_info = mt5_connector.get_account_info() if mt5_connected else None
    uptime = time.time() - _start_time
    return HealthResponse(
        status="healthy" if mt5_connected else "degraded",
        mt5_connected=mt5_connected,
        account_info=account_info,
        uptime_seconds=uptime,
        timestamp=datetime.utcnow(),
    )
