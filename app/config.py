"""Configuration management using Pydantic Settings."""
from __future__ import annotations

from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MT5 Configuration
    MT5_LOGIN: int
    MT5_PASSWORD: str
    MT5_SERVER: str = "Exness-MT5Trial"
    MT5_PATH: str = "C:/Program Files/MetaTrader 5/terminal64.exe"

    # Trading Configuration
    SYMBOLS: str = "BTCUSDm,XAUUSDm,XAGUSDm"
    STARTING_CAPITAL_AED: float = 1000.0
    STARTING_CAPITAL_USD: float = 272.0
    MAX_RISK_PER_TRADE_PERCENT: float = 1.0
    MAX_DAILY_LOSS_PERCENT: float = 5.0
    MAX_OPEN_POSITIONS: int = 6
    AUTO_TRADE: bool = False
    AUTO_ARM: bool = False
    MAGIC_NUMBER: int = 202401
    MAX_LOT_SIZE: float = 0.01
    DEBUG_SIGNALS: bool = False
    SIGNAL_MIN_CONF_LOW: float = 0.55
    SIGNAL_MIN_CONF_NORMAL: float = 0.6
    MIN_STRATEGY_AGREE_LOW: int = 1
    MIN_STRATEGY_AGREE_NORMAL: int = 1
    TREND_FILTER_ENABLED: bool = False
    SYMBOL_MIN_LOTS: str = ""
    SYMBOL_FIXED_LOTS: str = ""
    NEWS_FILTER_ENABLED: bool = False
    FREE_MARGIN_MIN_PERCENT: int = 200

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: str = "http://localhost:5173"
    SECRET_KEY: str = "change-me"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./trades.db"

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    @property
    def symbol_list(self) -> List[str]:
        return [s.strip() for s in self.SYMBOLS.split(",") if s.strip()]

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def symbol_min_lots(self) -> dict:
        pairs = [p.strip() for p in self.SYMBOL_MIN_LOTS.split(",") if p.strip()]
        result = {}
        for pair in pairs:
            if ":" not in pair:
                continue
            sym, val = pair.split(":", 1)
            try:
                result[sym.strip()] = float(val.strip())
            except ValueError:
                continue
        return result

    @property
    def symbol_fixed_lots(self) -> dict:
        pairs = [p.strip() for p in self.SYMBOL_FIXED_LOTS.split(",") if p.strip()]
        result = {}
        for pair in pairs:
            if ":" not in pair:
                continue
            sym, val = pair.split(":", 1)
            try:
                result[sym.strip()] = float(val.strip())
            except ValueError:
                continue
        return result

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
