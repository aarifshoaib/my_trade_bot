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

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
