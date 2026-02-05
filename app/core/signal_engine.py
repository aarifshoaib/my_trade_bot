"""Signal generation engine."""
from __future__ import annotations

from typing import Optional

import MetaTrader5 as mt5

from app.core.market_data import market_data
from app.core.volatility_engine import VolatilityEngine, VolatilityRegime
from app.strategies.ema_crossover import EMACrossoverStrategy
from app.strategies.rsi_divergence import RSIDivergenceStrategy
from app.strategies.bollinger_squeeze import BollingerSqueezeStrategy
from app.strategies.vwap_scalper import VWAPScalperStrategy
from app.strategies.base_strategy import SignalResult
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SignalEngine:
    def __init__(self) -> None:
        self.volatility_engine = VolatilityEngine()
        self._strategies = {}
        self._signal_history: list[dict] = []
        self._auto_execute: dict[str, bool] = {}

    def _get_strategies(self, symbol: str) -> list:
        if symbol not in self._strategies:
            self._strategies[symbol] = [
                EMACrossoverStrategy(symbol),
                RSIDivergenceStrategy(symbol),
                BollingerSqueezeStrategy(symbol),
                VWAPScalperStrategy(symbol),
            ]
        return self._strategies[symbol]

    def generate_signal(self, symbol: str) -> Optional[SignalResult]:
        bars_m1 = market_data.get_bars(symbol, mt5.TIMEFRAME_M1, 250)
        bars_m5 = market_data.get_bars(symbol, mt5.TIMEFRAME_M5, 200)
        bars_m15 = market_data.get_bars(symbol, mt5.TIMEFRAME_M15, 120)
        if bars_m1 is None or bars_m5 is None or bars_m15 is None:
            logger.warning("signal_bars_missing", symbol=symbol)
            return None

        regime = self.volatility_engine.detect_regime(bars_m1)
        weights = self.volatility_engine.get_strategy_weights(regime)

        strategies = self._get_strategies(symbol)
        signals: list[SignalResult] = []
        for strategy in strategies:
            signal = strategy.generate_signal(bars_m1, bars_m5, bars_m15)
            if signal.direction.value != "NEUTRAL":
                signals.append(signal)

        if not signals:
            return None
        direction, confidence, final_signal = self._calculate_confluence(signals, weights)
        if direction is None or confidence < 0.6:
            return None

        if not self._spread_ok(symbol):
            return None

        logger.info(
            "signal_generated",
            symbol=symbol,
            direction=direction.value,
            confidence=confidence,
            regime=regime.value,
        )
        final_signal.confidence = confidence
        self._record_signal(final_signal, regime)
        return final_signal

    def _spread_ok(self, symbol: str) -> bool:
        tick = market_data.get_tick(symbol)
        if tick is None:
            return False
        spread = abs(tick["ask"] - tick["bid"])
        return spread > 0

    def _record_signal(self, signal: SignalResult, regime: VolatilityRegime) -> None:
        self._signal_history.append(
            {
                "symbol": signal.symbol,
                "direction": signal.direction.value,
                "confidence": signal.confidence,
                "strategy": signal.strategy_name,
                "entry": signal.entry_price,
                "sl": signal.stop_loss,
                "tp": signal.take_profit,
                "regime": regime.value,
            }
        )
        self._signal_history = self._signal_history[-500:]

    def get_recent_signals(self, limit: int = 50) -> list[dict]:
        return list(reversed(self._signal_history[-limit:]))

    def set_auto_execute(self, symbol: str, enabled: bool) -> None:
        self._auto_execute[symbol] = enabled

    def is_auto_execute(self, symbol: str) -> bool:
        return self._auto_execute.get(symbol, False)

    def _calculate_confluence(
        self,
        signals: list[SignalResult],
        weights: dict[str, float],
    ) -> tuple[SignalDirection | None, float, SignalResult]:
        buy = [s for s in signals if s.direction.value == "BUY"]
        sell = [s for s in signals if s.direction.value == "SELL"]

        if len(buy) >= 2 and len(buy) >= len(sell):
            return self._aggregate("BUY", buy, weights)
        if len(sell) >= 2 and len(sell) > len(buy):
            return self._aggregate("SELL", sell, weights)
        return None, 0.0, signals[0]

    def _aggregate(
        self,
        direction: str,
        signals: list[SignalResult],
        weights: dict[str, float],
    ) -> tuple[SignalDirection, float, SignalResult]:
        total_weight = 0.0
        weighted_conf = 0.0
        for s in signals:
            w = weights.get(s.strategy_name, 0.1)
            total_weight += w
            weighted_conf += s.confidence * w
        confidence = weighted_conf / total_weight if total_weight > 0 else 0.0
        best = max(signals, key=lambda s: s.confidence)
        return best.direction, confidence, best


signal_engine = SignalEngine()
