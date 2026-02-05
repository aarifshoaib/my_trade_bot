"""Base strategy interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.models.enums import SignalDirection


@dataclass
class SignalResult:
    direction: SignalDirection
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    strategy_name: str
    symbol: str
    timeframe: str
    reasoning: str
    metadata: dict


class BaseStrategy(ABC):
    def __init__(self, symbol: str, params: Optional[dict] = None):
        self.symbol = symbol
        self.params = params or self.default_params()

    @abstractmethod
    def default_params(self) -> dict:
        raise NotImplementedError

    @abstractmethod
    def generate_signal(
        self,
        bars_m1: pd.DataFrame,
        bars_m5: pd.DataFrame,
        bars_m15: pd.DataFrame,
        tick_data: Optional[dict] = None,
    ) -> SignalResult:
        raise NotImplementedError

    @abstractmethod
    def calculate_sl_tp(
        self,
        direction: SignalDirection,
        entry_price: float,
        atr_value: float,
    ) -> tuple[float, float]:
        raise NotImplementedError
