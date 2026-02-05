"""EMA Crossover Scalping Strategy."""
from __future__ import annotations

import pandas as pd

from app.indicators.atr import atr
from app.indicators.ema import ema
from app.models.enums import SignalDirection
from app.strategies.base_strategy import BaseStrategy, SignalResult


class EMACrossoverStrategy(BaseStrategy):
    def default_params(self) -> dict:
        return {
            "ema_fast": 8,
            "ema_slow": 21,
            "atr_period": 14,
            "atr_sl_mult": 1.5,
            "atr_tp_mult": 2.5,
        }

    def generate_signal(
        self,
        bars_m1: pd.DataFrame,
        bars_m5: pd.DataFrame,
        bars_m15: pd.DataFrame,
        tick_data: dict | None = None,
    ) -> SignalResult:
        fast = ema(bars_m1["close"], self.params["ema_fast"])
        slow = ema(bars_m1["close"], self.params["ema_slow"])
        if len(fast) < 2 or len(slow) < 2:
            return self._neutral("Not enough bars")

        prev_fast, prev_slow = fast.iloc[-2], slow.iloc[-2]
        curr_fast, curr_slow = fast.iloc[-1], slow.iloc[-1]

        direction = SignalDirection.NEUTRAL
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            direction = SignalDirection.BUY
        elif prev_fast >= prev_slow and curr_fast < curr_slow:
            direction = SignalDirection.SELL

        if direction == SignalDirection.NEUTRAL:
            return self._neutral("No crossover")

        atr_series = atr(bars_m1, self.params["atr_period"])
        atr_value = float(atr_series.iloc[-1])
        entry_price = float(bars_m1["close"].iloc[-1])
        stop_loss, take_profit = self.calculate_sl_tp(direction, entry_price, atr_value)

        return SignalResult(
            direction=direction,
            confidence=0.7,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name="ema_crossover",
            symbol=self.symbol,
            timeframe="M1",
            reasoning="EMA crossover on M1",
            metadata={
                "ema_fast": float(curr_fast),
                "ema_slow": float(curr_slow),
                "atr": atr_value,
            },
        )

    def calculate_sl_tp(
        self,
        direction: SignalDirection,
        entry_price: float,
        atr_value: float,
    ) -> tuple[float, float]:
        sl_distance = atr_value * self.params["atr_sl_mult"]
        tp_distance = atr_value * self.params["atr_tp_mult"]
        if direction == SignalDirection.BUY:
            return entry_price - sl_distance, entry_price + tp_distance
        return entry_price + sl_distance, entry_price - tp_distance

    def _neutral(self, reason: str) -> SignalResult:
        return SignalResult(
            direction=SignalDirection.NEUTRAL,
            confidence=0.0,
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
            strategy_name="ema_crossover",
            symbol=self.symbol,
            timeframe="M1",
            reasoning=reason,
            metadata={},
        )
