"""Bollinger Band squeeze breakout strategy."""
from __future__ import annotations

import pandas as pd

from app.indicators.atr import atr
from app.indicators.bollinger import bollinger_bands
from app.models.enums import SignalDirection
from app.strategies.base_strategy import BaseStrategy, SignalResult


class BollingerSqueezeStrategy(BaseStrategy):
    def default_params(self) -> dict:
        return {
            "bb_period": 20,
            "bb_std": 2.0,
            "squeeze_lookback": 50,
            "atr_period": 14,
            "atr_sl_mult": 1.4,
            "atr_tp_mult": 2.0,
        }

    def generate_signal(
        self,
        bars_m1: pd.DataFrame,
        bars_m5: pd.DataFrame,
        bars_m15: pd.DataFrame,
        tick_data: dict | None = None,
    ) -> SignalResult:
        if len(bars_m1) < self.params["squeeze_lookback"] + 2:
            return self._neutral("Not enough bars")

        bands = bollinger_bands(
            bars_m1["close"],
            self.params["bb_period"],
            self.params["bb_std"],
        )
        width = bands["upper"] - bands["lower"]
        recent_width = width.iloc[-1]
        min_width = width.iloc[-self.params["squeeze_lookback"] :].min()

        if recent_width > min_width * 1.2:
            return self._neutral("No squeeze")

        price = bars_m1["close"].iloc[-1]
        prev_price = bars_m1["close"].iloc[-2]

        direction = SignalDirection.NEUTRAL
        if prev_price <= bands["upper"].iloc[-2] and price > bands["upper"].iloc[-1]:
            direction = SignalDirection.BUY
        elif prev_price >= bands["lower"].iloc[-2] and price < bands["lower"].iloc[-1]:
            direction = SignalDirection.SELL

        if direction == SignalDirection.NEUTRAL:
            return self._neutral("No breakout")

        atr_series = atr(bars_m1, self.params["atr_period"])
        atr_value = float(atr_series.iloc[-1])
        entry_price = float(price)
        stop_loss, take_profit = self.calculate_sl_tp(direction, entry_price, atr_value)

        return SignalResult(
            direction=direction,
            confidence=0.7,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name="bollinger_squeeze",
            symbol=self.symbol,
            timeframe="M1",
            reasoning="Bollinger squeeze breakout",
            metadata={"bb_width": float(recent_width), "atr": atr_value},
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
            strategy_name="bollinger_squeeze",
            symbol=self.symbol,
            timeframe="M1",
            reasoning=reason,
            metadata={},
        )
