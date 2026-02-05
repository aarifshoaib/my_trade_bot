"""Volatility regime detector."""
from __future__ import annotations

from enum import Enum
from typing import Dict

import numpy as np
import pandas as pd

from app.indicators.atr import atr


class VolatilityRegime(Enum):
    LOW_VOL = "low_volatility"
    NORMAL = "normal"
    HIGH_VOL = "high_volatility"
    EXTREME = "extreme"


class VolatilityEngine:
    def detect_regime(self, bars: pd.DataFrame, lookback: int = 200) -> VolatilityRegime:
        series = atr(bars, 14).dropna()
        if series.empty:
            return VolatilityRegime.NORMAL

        recent = series.iloc[-1]
        window = series.iloc[-lookback:] if len(series) >= lookback else series
        pct_rank = (window < recent).mean()

        if pct_rank < 0.25:
            return VolatilityRegime.LOW_VOL
        if pct_rank < 0.75:
            return VolatilityRegime.NORMAL
        if pct_rank < 0.95:
            return VolatilityRegime.HIGH_VOL
        return VolatilityRegime.EXTREME

    def get_strategy_weights(self, regime: VolatilityRegime) -> Dict[str, float]:
        if regime == VolatilityRegime.LOW_VOL:
            return {
                "vwap_scalper": 0.35,
                "rsi_divergence": 0.25,
                "bollinger_squeeze": 0.2,
                "ema_crossover": 0.2,
            }
        if regime == VolatilityRegime.HIGH_VOL:
            return {
                "ema_crossover": 0.3,
                "bollinger_squeeze": 0.3,
                "rsi_divergence": 0.2,
                "vwap_scalper": 0.2,
            }
        if regime == VolatilityRegime.EXTREME:
            return {
                "ema_crossover": 0.2,
                "bollinger_squeeze": 0.2,
                "rsi_divergence": 0.1,
                "vwap_scalper": 0.1,
            }
        return {
            "ema_crossover": 0.3,
            "bollinger_squeeze": 0.25,
            "rsi_divergence": 0.2,
            "vwap_scalper": 0.25,
        }

    def get_position_size_multiplier(self, regime: VolatilityRegime) -> float:
        multipliers = {
            VolatilityRegime.LOW_VOL: 1.0,
            VolatilityRegime.NORMAL: 1.0,
            VolatilityRegime.HIGH_VOL: 0.75,
            VolatilityRegime.EXTREME: 0.5,
        }
        return multipliers[regime]
