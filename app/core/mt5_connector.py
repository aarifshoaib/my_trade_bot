"""MT5 Connection Manager - Singleton Pattern."""
from __future__ import annotations

import threading
from typing import Optional

import MetaTrader5 as mt5

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MT5Connector:
    """Thread-safe singleton MT5 connection manager with auto-reconnect."""

    _instance: Optional["MT5Connector"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "MT5Connector":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
                cls._instance._credentials = None
            return cls._instance

    def initialize(
        self,
        login: Optional[int] = None,
        password: Optional[str] = None,
        server: Optional[str] = None,
        path: Optional[str] = None,
    ) -> bool:
        """Initialize MT5 terminal and login to Exness account."""
        login = login or settings.MT5_LOGIN
        password = password or settings.MT5_PASSWORD
        server = server or settings.MT5_SERVER
        path = path or settings.MT5_PATH

        self._credentials = (login, password, server, path)

        if not mt5.initialize(path=path):
            logger.error("mt5_initialize_failed", error=mt5.last_error())
            return False

        if not mt5.login(login=login, password=password, server=server):
            logger.error("mt5_login_failed", error=mt5.last_error())
            mt5.shutdown()
            return False

        account_info = mt5.account_info()
        if account_info:
            logger.info(
                "mt5_connected",
                account=account_info.login,
                balance=account_info.balance,
                currency=account_info.currency,
                server=account_info.server,
            )

        for symbol in settings.symbol_list:
            info = mt5.symbol_info(symbol)
            if info is None:
                logger.warning("symbol_not_found", symbol=symbol)
                continue
            if not info.visible:
                if not mt5.symbol_select(symbol, True):
                    logger.warning("symbol_select_failed", symbol=symbol, error=mt5.last_error())

        self._initialized = True
        return True

    def ensure_connected(self) -> bool:
        """Check connection and reconnect if needed."""
        if not self._initialized or mt5.terminal_info() is None:
            logger.warning("mt5_disconnected_reconnecting")
            if self._credentials:
                login, password, server, path = self._credentials
                return self.initialize(login, password, server, path)
            return self.initialize()
        return True

    def is_connected(self) -> bool:
        return self._initialized and mt5.terminal_info() is not None

    def get_account_info(self) -> Optional[dict]:
        if not self.ensure_connected():
            return None

        info = mt5.account_info()
        if info is None:
            return None
        free_margin = getattr(info, "free_margin", None)
        if free_margin is None:
            free_margin = getattr(info, "margin_free", None)
        return {
            "login": info.login,
            "balance": info.balance,
            "equity": info.equity,
            "margin": info.margin,
            "free_margin": free_margin,
            "currency": info.currency,
            "server": info.server,
            "leverage": info.leverage,
        }

    def shutdown(self) -> None:
        mt5.shutdown()
        self._initialized = False
        logger.info("mt5_shutdown")


mt5_connector = MT5Connector()
