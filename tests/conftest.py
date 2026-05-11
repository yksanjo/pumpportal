"""Shared fixtures for PumpPortal tests."""

from __future__ import annotations

import pytest

from pumpportal.memory import Memory


@pytest.fixture
def memory(tmp_path) -> Memory:
    return Memory(str(tmp_path / "test.sqlite"))
