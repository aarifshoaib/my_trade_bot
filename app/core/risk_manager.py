"""Risk management engine."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Tuple

import MetaTrader5 as mt5

from app.config import settings
from app.core.mt5_connector import mt5_connector
from app.core.volatility_engine import VolatilityRegime
from app.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RiskDecision:
    approved: bool
    reason: str


class RiskManager:
    def __init__(self) -> None:
        self.max_risk_per_trade = Decimal(settings.MAX_RISK_PER_TRADE_PERCENT) / Decimal("100")
        self.max_daily_loss = Decimal(settings.MAX_DAILY_LOSS_PERCENT) / Decimal("100")
        self.max_open_positions = settings.MAX_OPEN_POSITIONS
        self.daily_pnl = Decimal("0")
        self._start_balance: Decimal | None = None
        self.consecutive_losses = 0
        self.is_paused = False

    def approve_trade(self, symbol: str, direction: str, equity: float) -> RiskDecision:
        if self.is_paused:
            return RiskDecision(False, "Trading paused by risk manager")

        if not mt5_connector.ensure_connected():
            return RiskDecision(False, "MT5 not connected")

        positions = mt5.positions_get()
        if positions is not None and len(positions) >= self.max_open_positions:
            return RiskDecision(False, "Max open positions reached")

        daily_loss_limit = Decimal(equity) * self.max_daily_loss * Decimal("-1")
        if self.daily_pnl <= daily_loss_limit:
            self.is_paused = True
            return RiskDecision(False, "Daily loss limit hit")

        if not self._check_correlation(symbol):
            return RiskDecision(False, "Correlated exposure limit")

        if not self._check_free_margin():
            return RiskDecision(False, "Free margin below threshold")

        return RiskDecision(True, "Approved")

    def calculate_lot_size(
        self,
        symbol: str,
        equity: float,
        sl_points: float,
        regime: VolatilityRegime,
    ) -> float:
        if sl_points <= 0:
            return 0.0

        risk_amount = Decimal(str(equity)) * self.max_risk_per_trade

        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return 0.0

        tick_value = Decimal(str(symbol_info.trade_tick_value))
        tick_size = Decimal(str(symbol_info.trade_tick_size))
        if tick_value <= 0 or tick_size <= 0:
            return float(symbol_info.volume_min)

        sl_distance = Decimal(str(sl_points))
        if sl_distance <= 0:
            return 0.0

        value_per_price = tick_value / tick_size
        base_lot = risk_amount / (sl_distance * value_per_price)

        multiplier = Decimal(str(self._regime_multiplier(regime)))
        lot = base_lot * multiplier

        step = Decimal(str(symbol_info.volume_step or 0.01))
        if step > 0:
            lot = (lot / step).quantize(Decimal("1"), rounding=ROUND_DOWN) * step

        min_override = settings.symbol_min_lots.get(symbol_info.name)
        min_lot = Decimal(str(min_override if min_override is not None else symbol_info.volume_min))
        max_lot = Decimal(str(symbol_info.volume_max))
        max_lot = min(max_lot, Decimal(str(settings.MAX_LOT_SIZE)))
        lot = max(min_lot, min(lot, max_lot))

        return float(lot)

    def update_daily_pnl(self, pnl: float) -> None:
        self.daily_pnl += Decimal(str(pnl))

    def sync_from_account(self, balance: float) -> None:
        if self._start_balance is None:
            self._start_balance = Decimal(str(balance))
        self.daily_pnl = Decimal(str(balance)) - self._start_balance

    def _check_correlation(self, symbol: str) -> bool:
        if symbol == "XAUUSDm":
            return self._count_symbol_positions("XAGUSDm") < 2
        if symbol == "XAGUSDm":
            return self._count_symbol_positions("XAUUSDm") < 2
        return True

    def _count_symbol_positions(self, symbol: str) -> int:
        positions = mt5.positions_get(symbol=symbol)
        return len(positions) if positions is not None else 0

    def _check_free_margin(self) -> bool:
        info = mt5.account_info()
        if info is None:
            return False
        if info.margin <= 0:
            return True
        free_margin = getattr(info, "free_margin", None)
        if free_margin is None:
            free_margin = getattr(info, "margin_free", 0.0)
        free_margin_percent = (free_margin / info.margin) * 100
        return free_margin_percent >= settings.FREE_MARGIN_MIN_PERCENT

    def _regime_multiplier(self, regime: VolatilityRegime) -> float:
        if regime == VolatilityRegime.HIGH_VOL:
            return 0.75
        if regime == VolatilityRegime.EXTREME:
            return 0.5
        return 1.0


risk_manager = RiskManager()
