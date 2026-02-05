"""Pydantic schemas for API requests/responses."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.enums import SignalDirection


class HealthResponse(BaseModel):
    status: str
    mt5_connected: bool
    account_info: Optional[dict] = None
    uptime_seconds: float
    timestamp: datetime


class AccountInfoResponse(BaseModel):
    equity: float
    balance: float
    margin: float
    free_margin: float
    daily_pnl: float = 0.0


class SignalRequest(BaseModel):
    symbol: str
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0)
    entry_price: float
    stop_loss: float
    take_profit: float
    strategy_name: str = "manual"


class ExecuteTradeRequest(BaseModel):
    symbol: str
    direction: SignalDirection
    stop_loss: float
    take_profit: float
    lot_size: Optional[float] = None
    comment: str = ""


class TradeActionResponse(BaseModel):
    success: bool
    message: str
    details: Optional[dict] = None
