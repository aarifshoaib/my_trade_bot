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
    free_margin = getattr(info, "free_margin", None)
    if free_margin is None:
        free_margin = getattr(info, "margin_free", 0.0)
    return AccountInfoResponse(
        equity=info.equity,
        balance=info.balance,
        margin=info.margin,
        free_margin=free_margin,
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


@router.get("/history")
async def history(days: int = 1):
    mt5_connector.ensure_connected()
    from datetime import datetime, timedelta, timezone

    to_time = datetime.now(timezone.utc)
    from_time = to_time - timedelta(days=days)
    deals = mt5.history_deals_get(from_time, to_time)
    results = []
    if deals:
        for d in deals:
            results.append(
                {
                    "ticket": d.ticket,
                    "symbol": d.symbol,
                    "direction": "BUY" if d.type == mt5.DEAL_TYPE_BUY else "SELL",
                    "volume": d.volume,
                    "price": d.price,
                    "profit": d.profit,
                    "time": d.time,
                    "comment": d.comment,
                    "entry": d.entry,
                }
            )
    return results
