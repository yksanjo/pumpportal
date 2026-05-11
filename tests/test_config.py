"""Tests for config loading."""

from __future__ import annotations

from pumpportal.config import get_config


def test_defaults() -> None:
    cfg = get_config()
    assert cfg.helius_api_key == ""
    assert cfg.pump_portal_ws_url.startswith("wss://")


def test_default_db_path() -> None:
    cfg = get_config()
    assert ".pumpportal" in cfg.database_path
    assert cfg.database_path.endswith(".sqlite")
