"""Order execution engine."""
from __future__ import annotations

from typing import Dict, Optional
from decimal import Decimal, ROUND_DOWN

import MetaTrader5 as mt5

from app.config import settings
from app.core.mt5_connector import mt5_connector
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OrderExecutor:
    RETCODE_MAP = {
        mt5.TRADE_RETCODE_DONE: "Order executed successfully",
        mt5.TRADE_RETCODE_REQUOTE: "Requote received",
        mt5.TRADE_RETCODE_REJECT: "Order rejected by server",
        mt5.TRADE_RETCODE_CANCEL: "Order cancelled",
        mt5.TRADE_RETCODE_PLACED: "Order placed (pending)",
        mt5.TRADE_RETCODE_NO_MONEY: "Insufficient margin",
        mt5.TRADE_RETCODE_PRICE_OFF: "Price changed, no requote",
        mt5.TRADE_RETCODE_INVALID: "Invalid request",
        mt5.TRADE_RETCODE_INVALID_VOLUME: "Invalid volume",
        mt5.TRADE_RETCODE_INVALID_PRICE: "Invalid price",
        mt5.TRADE_RETCODE_INVALID_STOPS: "Invalid SL/TP",
        mt5.TRADE_RETCODE_MARKET_CLOSED: "Market closed",
        mt5.TRADE_RETCODE_CONNECTION: "No connection",
        mt5.TRADE_RETCODE_TIMEOUT: "Request timeout",
        10027: "Invalid volume",
    }

    def execute_market_order(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        stop_loss: float,
        take_profit: float,
        comment: str = "",
        magic_number: Optional[int] = None,
        max_deviation: int = 15,
    ) -> Dict:
        if not mt5_connector.ensure_connected():
            return {"success": False, "message": "MT5 not connected"}

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return {"success": False, "message": f"Symbol {symbol} not found"}
        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)

        if not symbol_info.trade_allowed:
            return {"success": False, "message": "Symbol not tradeable"}

        lot_size = self._normalize_volume(symbol_info, lot_size)
        if lot_size <= 0:
            return {"success": False, "message": "Invalid lot size"}

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "message": "No tick data"}

        price = tick.ask if direction == "BUY" else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": stop_loss,
            "tp": take_profit,
            "deviation": max_deviation,
            "magic": magic_number or settings.MAGIC_NUMBER,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        check = mt5.order_check(request)
        if check is not None and check.retcode != mt5.TRADE_RETCODE_DONE:
            message = self.RETCODE_MAP.get(check.retcode, "Order check failed")
            logger.info(
                "order_check_failed",
                retcode=check.retcode,
                message=message,
                request=request,
            )
            return {"success": False, "message": message, "details": {"retcode": check.retcode}}

        result = mt5.order_send(request)
        if result is None:
            return {"success": False, "message": "No result from MT5"}

        message = self.RETCODE_MAP.get(result.retcode, "Unknown retcode")
        success = result.retcode == mt5.TRADE_RETCODE_DONE

        logger.info(
            "order_send_result",
            success=success,
            retcode=result.retcode,
            message=message,
            request=request,
        )

        return {
            "success": success,
            "message": message,
            "details": {
                "retcode": result.retcode,
                "order": result.order,
                "deal": result.deal,
                "price": result.price,
                "volume": result.volume,
                "comment": result.comment,
            },
        }

    def modify_position(self, ticket: int, new_sl: float, new_tp: float) -> Dict:
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
            "tp": new_tp,
        }
        result = mt5.order_send(request)
        if result is None:
            return {"success": False, "message": "No result from MT5"}
        success = result.retcode == mt5.TRADE_RETCODE_DONE
        message = self.RETCODE_MAP.get(result.retcode, "Unknown retcode")
        return {"success": success, "message": message, "details": {"retcode": result.retcode}}

    def close_position(self, ticket: int, lot_size: Optional[float] = None) -> Dict:
        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            return {"success": False, "message": "Position not found"}

        position = pos[0]
        symbol = position.symbol
        volume = lot_size or position.volume
        direction = "SELL" if position.type == mt5.POSITION_TYPE_BUY else "BUY"

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"success": False, "message": "No tick data"}

        price = tick.bid if direction == "SELL" else tick.ask
        order_type = mt5.ORDER_TYPE_SELL if direction == "SELL" else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 15,
            "magic": settings.MAGIC_NUMBER,
            "comment": "close_position",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None:
            return {"success": False, "message": "No result from MT5"}
        success = result.retcode == mt5.TRADE_RETCODE_DONE
        message = self.RETCODE_MAP.get(result.retcode, "Unknown retcode")
        return {"success": success, "message": message, "details": {"retcode": result.retcode}}

    def close_all_positions(self, symbol: Optional[str] = None) -> list[Dict]:
        positions = mt5.positions_get(symbol=symbol) if symbol else mt5.positions_get()
        if not positions:
            return []
        results = []
        for pos in positions:
            results.append(self.close_position(pos.ticket))
        return results

    def _normalize_volume(self, symbol_info, lot_size: float) -> float:
        min_lot = Decimal(str(symbol_info.volume_min))
        max_lot = Decimal(str(symbol_info.volume_max))
        step = Decimal(str(symbol_info.volume_step or 0.01))
        max_lot = min(max_lot, Decimal(str(settings.MAX_LOT_SIZE)))

        if max_lot < min_lot:
            logger.info(
                "max_lot_below_min",
                min_lot=float(min_lot),
                max_lot=float(max_lot),
            )
            max_lot = min_lot

        lot = Decimal(str(lot_size))
        lot = max(min_lot, min(lot, max_lot))
        if step > 0:
            lot = (lot / step).quantize(Decimal("1"), rounding=ROUND_DOWN) * step
        return float(lot)


order_executor = OrderExecutor()
