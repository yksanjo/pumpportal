"""Tests for SQLite memory layer."""

from __future__ import annotations

from pumpportal.memory import Memory


def test_record_and_check_token(memory: Memory) -> None:
    assert not memory.has_seen_token("m1")
    memory.record_token("m1", "S", "Sym", "w1", 0.5, market_cap_sol=10.0)
    assert memory.has_seen_token("m1")


def test_recent_tokens(memory: Memory) -> None:
    for i in range(5):
        memory.record_token(f"mint{i}", f"S{i}", f"Sym {i}", "w", 0.1 * i)
    recent = memory.recent_tokens(limit=3)
    assert len(recent) == 3


def test_deployer_tracking(memory: Memory) -> None:
    assert memory.deployer_record("w") is None
    memory.touch_deployer("w")
    rec = memory.deployer_record("w")
    assert rec["launch_count"] == 1
    assert rec["rug_count"] == 0
    memory.touch_deployer("w", is_rug=True)
    rec = memory.deployer_record("w")
    assert rec["launch_count"] == 2
    assert rec["rug_count"] == 1
