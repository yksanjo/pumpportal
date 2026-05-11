"""PumpPortal WebSocket adapter — streams new pump.fun token deploys."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator

import websockets

logger = logging.getLogger(__name__)


@dataclass
class NewTokenEvent:
    mint: str
    symbol: str
    name: str
    deployer: str
    pool: str
    initial_sol: float
    market_cap_sol: float
    uri: str | None = None
    received_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    raw: dict = field(default_factory=dict)


def _parse(payload: dict) -> NewTokenEvent | None:
    try:
        mint = payload.get("mint")
        if not mint:
            return None
        return NewTokenEvent(
            mint=mint,
            symbol=payload.get("symbol", ""),
            name=payload.get("name", ""),
            deployer=payload.get("traderPublicKey")
            or payload.get("creator")
            or "",
            pool=payload.get("pool", ""),
            initial_sol=float(payload.get("solAmount", 0) or 0),
            market_cap_sol=float(payload.get("marketCapSol", 0) or 0),
            uri=payload.get("uri"),
            raw=payload,
        )
    except (ValueError, TypeError) as e:
        logger.warning("dropping malformed payload: %s — %s", e, payload)
        return None


async def stream_new_tokens(
    ws_url: str,
    *,
    max_events: int | None = None,
    recv_timeout: float = 60.0,
) -> AsyncIterator[NewTokenEvent]:
    sent = 0
    async with websockets.connect(ws_url, ping_interval=20) as ws:
        await ws.send(json.dumps({"method": "subscribeNewToken"}))
        logger.info("subscribed to new-token stream at %s", ws_url)

        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
            except asyncio.TimeoutError:
                await ws.ping()
                continue

            try:
                payload = json.loads(msg)
            except json.JSONDecodeError:
                continue

            event = _parse(payload)
            if event is None:
                continue

            yield event
            sent += 1
            if max_events is not None and sent >= max_events:
                return


async def collect_window(
    ws_url: str,
    *,
    seconds: int,
    max_events: int = 1000,
) -> list[NewTokenEvent]:
    out: list[NewTokenEvent] = []

    async def _consume() -> None:
        async for ev in stream_new_tokens(ws_url, max_events=max_events):
            out.append(ev)

    try:
        await asyncio.wait_for(_consume(), timeout=seconds)
    except asyncio.TimeoutError:
        pass
    return out
