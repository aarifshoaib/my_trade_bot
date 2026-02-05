"""VWAP mean reversion scalper."""
from __future__ import annotations

import pandas as pd

from app.indicators.atr import atr
from app.indicators.rsi import rsi
from app.indicators.vwap import vwap
from app.models.enums import SignalDirection
from app.strategies.base_strategy import BaseStrategy, SignalResult


class VWAPScalperStrategy(BaseStrategy):
    def default_params(self) -> dict:
        return {
            "rsi_period": 7,
            "rsi_overbought": 70,
            "rsi_oversold": 30,
            "atr_period": 14,
            "atr_sl_mult": 1.2,
            "atr_tp_mult": 1.5,
            "vwap_dev_mult": 1.5,
        }

    def generate_signal(
        self,
        bars_m1: pd.DataFrame,
        bars_m5: pd.DataFrame,
        bars_m15: pd.DataFrame,
        tick_data: dict | None = None,
    ) -> SignalResult:
        if len(bars_m1) < 30:
            return self._neutral("Not enough bars")

        vwap_series = vwap(bars_m1)
        rsi_series = rsi(bars_m1["close"], self.params["rsi_period"])
        atr_series = atr(bars_m1, self.params["atr_period"])

        price = float(bars_m1["close"].iloc[-1])
        vwap_value = float(vwap_series.iloc[-1])
        atr_value = float(atr_series.iloc[-1])
        rsi_value = float(rsi_series.iloc[-1])

        if atr_value <= 0 or vwap_value == 0:
            return self._neutral("Invalid ATR/VWAP")

        deviation = (price - vwap_value) / atr_value

        direction = SignalDirection.NEUTRAL
        if deviation < -self.params["vwap_dev_mult"] and rsi_value < self.params["rsi_oversold"]:
            direction = SignalDirection.BUY
        elif deviation > self.params["vwap_dev_mult"] and rsi_value > self.params["rsi_overbought"]:
            direction = SignalDirection.SELL

        if direction == SignalDirection.NEUTRAL:
            return self._neutral("No VWAP deviation")

        stop_loss, take_profit = self.calculate_sl_tp(direction, price, atr_value)

        return SignalResult(
            direction=direction,
            confidence=0.66,
            entry_price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            strategy_name="vwap_scalper",
            symbol=self.symbol,
            timeframe="M1",
            reasoning="VWAP deviation with RSI filter",
            metadata={"vwap": vwap_value, "rsi": rsi_value, "atr": atr_value},
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
            strategy_name="vwap_scalper",
            symbol=self.symbol,
            timeframe="M1",
            reasoning=reason,
            metadata={},
        )
