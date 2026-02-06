"""FastAPI application entry point."""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager

import MetaTrader5 as mt5
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_account import router as account_router
from app.api.routes_health import router as health_router
from app.api.routes_settings import router as settings_router
from app.api.routes_strategy import router as strategy_router
from app.api.routes_signal import router as signal_router
from app.api.routes_trade import router as trade_router
from app.api.routes_websocket import router as ws_router
from app.api.websocket import ws_manager
from app.config import settings
from app.core.mt5_connector import mt5_connector
from app.core.order_executor import order_executor
from app.core.market_data import market_data
from app.core.risk_manager import risk_manager
from app.core.signal_engine import signal_engine
from app.core.volatility_engine import VolatilityRegime, VolatilityEngine
from app.services.bot_state import bot_state
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def _signal_loop() -> None:
    while True:
        status = await bot_state.get_status()
        if status.running and not status.paused:
            for symbol in settings.symbol_list:
                signal = await asyncio.to_thread(signal_engine.generate_signal, symbol)
                if signal is None:
                    continue
                await ws_manager.broadcast(
                    {
                        "type": "signal",
                        "data": {
                            "symbol": signal.symbol,
                            "direction": signal.direction.value,
                            "confidence": signal.confidence,
                            "strategy": signal.strategy_name,
                            "entry": signal.entry_price,
                            "sl": signal.stop_loss,
                            "tp": signal.take_profit,
                        },
                    }
                )

                if not signal_engine.is_auto_execute(symbol) or not status.armed:
                    continue

                account_info = mt5.account_info()
                equity = account_info.equity if account_info else 0.0
                decision = risk_manager.approve_trade(symbol, signal.direction.value, equity)
                if not decision.approved:
                    continue

                sl_points = abs(signal.entry_price - signal.stop_loss)
                bars = market_data.get_bars(symbol, mt5.TIMEFRAME_M1, 250)
                if bars is None or bars.empty:
                    continue
                regime = VolatilityEngine().detect_regime(bars)
                lot_size = risk_manager.calculate_lot_size(symbol, equity, sl_points, regime)
                if lot_size <= 0:
                    continue

                result = order_executor.execute_market_order(
                    symbol=symbol,
                    direction=signal.direction.value,
                    lot_size=lot_size,
                    stop_loss=signal.stop_loss,
                    take_profit=signal.take_profit,
                    comment=signal.strategy_name,
                )
                await ws_manager.broadcast(
                    {
                        "type": "trade_opened" if result.get("success") else "error",
                        "data": result,
                    }
                )
        await asyncio.sleep(5)


async def _account_loop() -> None:
    while True:
        info = mt5.account_info()
        if info:
            free_margin = getattr(info, "free_margin", None)
            if free_margin is None:
                free_margin = getattr(info, "margin_free", 0.0)
            risk_manager.sync_from_account(info.balance)
            await ws_manager.broadcast(
                {
                    "type": "account_update",
                    "data": {
                        "equity": info.equity,
                        "balance": info.balance,
                        "margin": info.margin,
                        "free_margin": free_margin,
                        "daily_pnl": float(risk_manager.daily_pnl),
                    },
                }
            )
        await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting")
    mt5_connector.initialize()
    for symbol in settings.symbol_list:
        signal_engine.set_auto_execute(symbol, settings.AUTO_TRADE)
    if settings.AUTO_ARM:
        await bot_state.arm()
    signal_task = asyncio.create_task(_signal_loop())
    account_task = asyncio.create_task(_account_loop())
    yield
    signal_task.cancel()
    account_task.cancel()
    mt5_connector.shutdown()
    logger.info("app_shutdown")


app = FastAPI(
    title="MT5 Scalping Trading API",
    description="Algorithmic scalping bot backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(account_router)
app.include_router(trade_router)
app.include_router(signal_router)
app.include_router(settings_router)
app.include_router(strategy_router)
app.include_router(ws_router)


@app.get("/")
async def root():
    return {"name": "MT5 Scalping Trading API", "status": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
