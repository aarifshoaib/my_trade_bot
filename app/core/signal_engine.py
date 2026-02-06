"""Signal generation engine."""
from __future__ import annotations

from typing import Optional

import MetaTrader5 as mt5

from app.core.market_data import market_data
from app.core.volatility_engine import VolatilityEngine, VolatilityRegime
from app.indicators.ema import ema
from app.strategies.ema_crossover import EMACrossoverStrategy
from app.strategies.rsi_divergence import RSIDivergenceStrategy
from app.strategies.bollinger_squeeze import BollingerSqueezeStrategy
from app.strategies.vwap_scalper import VWAPScalperStrategy
from app.strategies.base_strategy import SignalResult
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SignalEngine:
    def __init__(self) -> None:
        self.volatility_engine = VolatilityEngine()
        self._strategies = {}
        self._signal_history: list[dict] = []
        self._auto_execute: dict[str, bool] = {}
        self._strategy_enabled: dict[str, bool] = {
            "ema_crossover": True,
            "rsi_divergence": True,
            "bollinger_squeeze": True,
            "vwap_scalper": True,
        }
        self._strategy_params: dict[str, dict] = {}

    def _get_strategies(self, symbol: str) -> dict[str, object]:
        if symbol not in self._strategies:
            self._strategies[symbol] = {
                "ema_crossover": EMACrossoverStrategy(symbol),
                "rsi_divergence": RSIDivergenceStrategy(symbol),
                "bollinger_squeeze": BollingerSqueezeStrategy(symbol),
                "vwap_scalper": VWAPScalperStrategy(symbol),
            }
        return self._strategies[symbol]

    def generate_signal(self, symbol: str) -> Optional[SignalResult]:
        bars_m1 = market_data.get_bars(symbol, mt5.TIMEFRAME_M1, 250)
        bars_m5 = market_data.get_bars(symbol, mt5.TIMEFRAME_M5, 200)
        bars_m15 = market_data.get_bars(symbol, mt5.TIMEFRAME_M15, 120)
        if bars_m1 is None or bars_m5 is None or bars_m15 is None:
            logger.warning("signal_bars_missing", symbol=symbol)
            return None

        regime = self.volatility_engine.detect_regime(bars_m1)
        if regime == VolatilityRegime.EXTREME:
            if settings.DEBUG_SIGNALS:
                logger.info("signal_skipped_extreme_regime", symbol=symbol)
            return None
        weights = self.volatility_engine.get_strategy_weights(regime)

        strategies = self._get_strategies(symbol)
        signals: list[SignalResult] = []
        for key, strategy in strategies.items():
            if not self._strategy_enabled.get(key, True):
                continue
            params = self._strategy_params.get(key)
            if params:
                strategy.params = {**strategy.params, **params}
            signal = strategy.generate_signal(bars_m1, bars_m5, bars_m15)
            if signal.direction.value != "NEUTRAL":
                signals.append(signal)

        if not signals:
            if settings.DEBUG_SIGNALS:
                logger.info("signal_skipped_no_strategy_match", symbol=symbol, regime=regime.value)
            return None
        direction, confidence, final_signal = self._calculate_confluence(signals, weights)
        if direction is None or confidence < 0.7:
            if settings.DEBUG_SIGNALS:
                logger.info(
                    "signal_skipped_low_confluence",
                    symbol=symbol,
                    confidence=confidence,
                    regime=regime.value,
                    candidates=len(signals),
                )
            return None
        if not self._trend_alignment_ok(direction.value, bars_m5):
            if settings.DEBUG_SIGNALS:
                logger.info("signal_skipped_trend_misalignment", symbol=symbol, direction=direction.value)
            return None

        if not self._spread_ok(symbol):
            if settings.DEBUG_SIGNALS:
                logger.info("signal_skipped_spread", symbol=symbol)
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

    def _trend_alignment_ok(self, direction: str, bars_m5) -> bool:
        if bars_m5 is None or len(bars_m5) < 25:
            return False
        fast = ema(bars_m5["close"], 8)
        slow = ema(bars_m5["close"], 21)
        if fast.iloc[-1] > slow.iloc[-1] and direction == "BUY":
            return True
        if fast.iloc[-1] < slow.iloc[-1] and direction == "SELL":
            return True
        return False

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

    def set_strategy_enabled(self, name: str, enabled: bool) -> None:
        self._strategy_enabled[name] = enabled

    def set_strategy_params(self, name: str, params: dict) -> None:
        self._strategy_params[name] = params

    def get_strategy_status(self) -> list[dict]:
        return [
            {"name": "ema_crossover", "enabled": self._strategy_enabled.get("ema_crossover", True)},
            {"name": "rsi_divergence", "enabled": self._strategy_enabled.get("rsi_divergence", True)},
            {"name": "bollinger_squeeze", "enabled": self._strategy_enabled.get("bollinger_squeeze", True)},
            {"name": "vwap_scalper", "enabled": self._strategy_enabled.get("vwap_scalper", True)},
        ]

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
