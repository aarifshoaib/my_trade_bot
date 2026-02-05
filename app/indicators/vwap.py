"""Volume Weighted Average Price."""
from __future__ import annotations

import pandas as pd


def vwap(df: pd.DataFrame) -> pd.Series:
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    cum_vol = df["tick_volume"].cumsum()
    cum_tp_vol = (typical_price * df["tick_volume"]).cumsum()
    return cum_tp_vol / cum_vol.replace(0, pd.NA)
