"""Configuration — env-var loader with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _env_str(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _default_db_path() -> str:
    return str(Path.home() / ".pumpportal" / "pumpportal.sqlite")


@dataclass
class Config:
    helius_api_key: str = ""
    bitquery_api_key: str = ""
    database_path: str = field(default_factory=_default_db_path)
    log_level: str = "INFO"
    pump_portal_ws_url: str = "wss://pumpportal.fun/api/data"


def get_config() -> Config:
    return Config(
        helius_api_key=_env_str("HELIUS_API_KEY"),
        bitquery_api_key=_env_str("BITQUERY_API_KEY"),
        database_path=_env_str("DATABASE_PATH", _default_db_path()),
        log_level=_env_str("LOG_LEVEL", "INFO"),
    )
