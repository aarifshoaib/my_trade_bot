"""RSI Divergence Strategy (simplified)."""
from __future__ import annotations

import pandas as pd

from app.indicators.atr import atr
from app.indicators.rsi import rsi
from app.models.enums import SignalDirection
from app.strategies.base_strategy import BaseStrategy, SignalResult


class RSIDivergenceStrategy(BaseStrategy):
    def default_params(self) -> dict:
        return {
            "rsi_period": 14,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "atr_period": 14,
            "atr_sl_mult": 1.2,
            "atr_tp_mult": 1.8,
            "lookback": 10,
        }

    def generate_signal(
        self,
        bars_m1: pd.DataFrame,
        bars_m5: pd.DataFrame,
        bars_m15: pd.DataFrame,
        tick_data: dict | None = None,
    ) -> SignalResult:
        if len(bars_m1) < self.params["lookback"] + 2:
            return self._neutral("Not enough bars")

        rsi_series = rsi(bars_m1["close"], self.params["rsi_period"])
        rsi_recent = rsi_series.iloc[-1]
        price = bars_m1["close"].iloc[-1]

        window = bars_m1["close"].iloc[-self.params["lookback"] :]
        low_recent = window.min()
        high_recent = window.max()

        direction = SignalDirection.NEUTRAL
        if rsi_recent < self.params["rsi_oversold"] and price <= low_recent:
            direction = SignalDirection.BUY
        elif rsi_recent > self.params["rsi_overbought"] and price >= high_recent:
            direction = SignalDirection.SELL

        if direction == SignalDirection.NEUTRAL:
            return self._neutral("RSI not extreme")

        atr_series = atr(bars_m1, self.params["atr_period"])
        atr_value = float(atr_series.iloc[-1])
        entry_price = float(price)
        stop_loss, take_profit = self.calculate_sl_tp(direction, entry_price, atr_value)

        return SignalResult(
            direction=direction,
            confidence=0.68,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name="rsi_divergence",
            symbol=self.symbol,
            timeframe="M1",
            reasoning="RSI extreme at recent high/low",
            metadata={"rsi": float(rsi_recent), "atr": atr_value},
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
            strategy_name="rsi_divergence",
            symbol=self.symbol,
            timeframe="M1",
            reasoning=reason,
            metadata={},
        )
