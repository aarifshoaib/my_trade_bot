"""Account endpoints."""
from __future__ import annotations

from fastapi import APIRouter

import MetaTrader5 as mt5

from app.core.mt5_connector import mt5_connector
from app.core.risk_manager import risk_manager
from app.models.schemas import AccountInfoResponse

router = APIRouter(prefix="/api/v1/account", tags=["account"])


@router.get("/info", response_model=AccountInfoResponse)
async def account_info() -> AccountInfoResponse:
    mt5_connector.ensure_connected()
    info = mt5.account_info()
    if info is None:
        return AccountInfoResponse(equity=0, balance=0, margin=0, free_margin=0, daily_pnl=0)
    return AccountInfoResponse(
        equity=info.equity,
        balance=info.balance,
        margin=info.margin,
        free_margin=info.free_margin,
        daily_pnl=float(risk_manager.daily_pnl),
    )


@router.get("/positions")
async def positions():
    mt5_connector.ensure_connected()
    positions = mt5.positions_get()
    results = []
    if positions:
        for p in positions:
            results.append(
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "direction": "BUY" if p.type == mt5.POSITION_TYPE_BUY else "SELL",
                    "lot": p.volume,
                    "entry": p.price_open,
                    "sl": p.sl,
                    "tp": p.tp,
                    "pnl": p.profit,
                }
            )
    return results
