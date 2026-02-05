"""Bollinger Bands."""
from __future__ import annotations

import pandas as pd


def bollinger_bands(series: pd.Series, period: int = 20, std_mult: float = 2.0) -> pd.DataFrame:
    ma = series.rolling(period).mean()
    std = series.rolling(period).std()
    upper = ma + std_mult * std
    lower = ma - std_mult * std
    return pd.DataFrame({"ma": ma, "upper": upper, "lower": lower})
