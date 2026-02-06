"""Market data fetcher."""
from __future__ import annotations

from typing import Optional

import pandas as pd

from app.core.mt5_connector import mt5_connector
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MarketData:
    def get_tick(self, symbol: str) -> Optional[dict]:
        if not mt5_connector.ensure_connected():
            return None

        import MetaTrader5 as mt5

        info = mt5.symbol_info(symbol)
        if info is None:
            logger.warning("symbol_not_found", symbol=symbol)
            return None
        if not info.visible:
            mt5.symbol_select(symbol, True)

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.warning("tick_missing", symbol=symbol, error=mt5.last_error())
            return None
        return {
            "symbol": symbol,
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "volume": tick.volume,
            "time": tick.time,
        }

    def get_bars(self, symbol: str, timeframe: int, count: int = 200) -> Optional[pd.DataFrame]:
        if not mt5_connector.ensure_connected():
            return None

        import MetaTrader5 as mt5

        info = mt5.symbol_info(symbol)
        if info is None:
            logger.warning("symbol_not_found", symbol=symbol)
            return None
        if not info.visible:
            mt5.symbol_select(symbol, True)

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            logger.warning("bars_missing", symbol=symbol, timeframe=timeframe, error=mt5.last_error())
            return None
        return pd.DataFrame(rates)


market_data = MarketData()
