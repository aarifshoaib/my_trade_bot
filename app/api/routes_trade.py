"""Trade execution endpoints."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.order_executor import order_executor
from app.core.risk_manager import risk_manager
from app.core.volatility_engine import VolatilityRegime
from app.models.schemas import ExecuteTradeRequest, TradeActionResponse
from app.services.bot_state import bot_state
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/trade", tags=["trade"])


@router.post("/execute", response_model=TradeActionResponse)
async def execute_trade(payload: ExecuteTradeRequest) -> TradeActionResponse:
    status = await bot_state.get_status()
    if not status.armed:
        raise HTTPException(status_code=403, detail="Live trading is not armed")

    import MetaTrader5 as mt5

    account_info = mt5.account_info()
    equity = account_info.equity if account_info else 0.0
    decision = risk_manager.approve_trade(payload.symbol, payload.direction.value, equity=equity)
    if not decision.approved:
        return TradeActionResponse(success=False, message=decision.reason)

    if payload.lot_size is None:
        lot_size = 0.01
    else:
        lot_size = payload.lot_size

    result = order_executor.execute_market_order(
        symbol=payload.symbol,
        direction=payload.direction.value,
        lot_size=lot_size,
        stop_loss=payload.stop_loss,
        take_profit=payload.take_profit,
        comment=payload.comment,
    )
    return TradeActionResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        details=result.get("details"),
    )


@router.post("/close/{ticket}", response_model=TradeActionResponse)
async def close_trade(ticket: int) -> TradeActionResponse:
    status = await bot_state.get_status()
    if not status.armed:
        raise HTTPException(status_code=403, detail="Live trading is not armed")

    result = order_executor.close_position(ticket)
    return TradeActionResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        details=result.get("details"),
    )


@router.post("/close-all", response_model=TradeActionResponse)
async def close_all(symbol: str | None = None) -> TradeActionResponse:
    status = await bot_state.get_status()
    if not status.armed:
        raise HTTPException(status_code=403, detail="Live trading is not armed")

    results = order_executor.close_all_positions(symbol=symbol)
    return TradeActionResponse(
        success=True,
        message="Close all executed",
        details={"results": results},
    )
