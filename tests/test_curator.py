"""Tests for the scoring curator."""

from __future__ import annotations

from pumpportal.curator import score_token
from pumpportal.sources.deployer import DeployerProfile
from pumpportal.sources.pumpfun import NewTokenEvent
from pumpportal.sources.token_meta import TokenMetadata


def _event(symbol="TEST", name="Test Token", initial_sol=1.0,
           market_cap_sol=10.0, deployer="w1") -> NewTokenEvent:
    return NewTokenEvent(
        mint="mint_" + symbol.lower(), symbol=symbol, name=name,
        deployer=deployer, pool="pump",
        initial_sol=initial_sol, market_cap_sol=market_cap_sol,
    )


def _meta(**kw) -> TokenMetadata:
    return TokenMetadata(mint="x", holder_count=10, **kw)


def test_clean_token_scores_positive() -> None:
    ev = _event(symbol="MOTH", name="The Last Moth")
    s = score_token(ev, _meta(description="A" * 50), DeployerProfile(wallet="w"))
    assert s.score > 0


def test_shouty_name_penalty() -> None:
    ev = _event(symbol="WIFCAT24", name="WIFCAT24SUPERMOON")
    s = score_token(ev, _meta(), DeployerProfile(wallet="w"))
    assert any("shouty" in n for n in s.notes)


def test_serial_offender_penalty() -> None:
    ev = _event()
    d = DeployerProfile(wallet="bad", prior_launches=5, prior_rugs=4)
    s = score_token(ev, _meta(), d)
    assert s.score < 0
    assert any("serial" in n for n in s.notes)


def test_concentrated_supply_penalty() -> None:
    ev = _event()
    s = score_token(ev, _meta(top_holder_share=0.6), DeployerProfile(wallet="w"))
    assert any("concentrated" in n for n in s.notes)
