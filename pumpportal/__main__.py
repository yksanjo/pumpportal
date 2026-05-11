"""PumpPortal CLI — terminal-based pump.fun explorer."""

from __future__ import annotations

import asyncio
import logging
import sys

import click

from .config import get_config
from .curator import score_token
from .memory import Memory
from .sources.deployer import profile_from_memory
from .sources.pumpfun import collect_window, stream_new_tokens
from .sources.token_meta import enrich

logger = logging.getLogger("pumpportal")


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@click.group()
def cli() -> None:
    """🚪 PumpPortal — terminal-based pump.fun explorer."""


@cli.command()
def tui() -> None:
    """Launch the Textual TUI explorer."""
    # Imported lazily so `pumpportal doctor` works even if textual is broken.
    from .tui_app import run_tui
    run_tui()


@cli.command()
@click.option("--max-events", default=0, type=int,
              help="Stop after N events. 0 = forever.")
def watch(max_events: int) -> None:
    """Plain-text live stream of pump.fun launches."""
    cfg = get_config()
    _configure_logging(cfg.log_level)
    memory = Memory(cfg.database_path)

    async def _watch() -> None:
        click.echo("🚪 PumpPortal watching pump.fun... (Ctrl+C to stop)\n")
        seen: set[str] = set()
        async for event in stream_new_tokens(
            cfg.pump_portal_ws_url,
            max_events=max_events or None,
        ):
            if event.mint in seen or memory.has_seen_token(event.mint):
                continue
            seen.add(event.mint)
            meta = await enrich(
                event.mint,
                helius_key=cfg.helius_api_key,
                bitquery_key=cfg.bitquery_api_key,
            )
            deployer = profile_from_memory(memory, event.deployer)
            scored = score_token(event, meta, deployer)
            memory.record_token(
                mint=event.mint, symbol=event.symbol, name=event.name,
                deployer=event.deployer, score=scored.score,
                market_cap_sol=event.market_cap_sol,
                initial_sol=event.initial_sol,
            )
            memory.touch_deployer(event.deployer)
            click.echo(scored.summary_line)

    try:
        asyncio.run(_watch())
    except KeyboardInterrupt:
        click.echo("\n👋 PumpPortal stopped.")


@cli.command()
@click.option("--window", "-w", default=60, type=int,
              help="Collection window in seconds.")
@click.option("--top", default=10, type=int, help="Show top N tokens.")
def scan(window: int, top: int) -> None:
    """Collect tokens for a window, then print a ranked report."""
    cfg = get_config()
    _configure_logging(cfg.log_level)
    memory = Memory(cfg.database_path)

    async def _scan() -> None:
        click.echo(f"🔍 Scanning pump.fun for {window} seconds...\n")
        events = await collect_window(cfg.pump_portal_ws_url, seconds=window)
        click.echo(f"Collected {len(events)} tokens. Scoring...\n")

        scored_tokens = []
        for event in events:
            if memory.has_seen_token(event.mint):
                continue
            meta = await enrich(
                event.mint, helius_key=cfg.helius_api_key,
                bitquery_key=cfg.bitquery_api_key,
            )
            deployer = profile_from_memory(memory, event.deployer)
            scored = score_token(event, meta, deployer)
            memory.record_token(
                mint=event.mint, symbol=event.symbol, name=event.name,
                deployer=event.deployer, score=scored.score,
                market_cap_sol=event.market_cap_sol,
                initial_sol=event.initial_sol,
            )
            memory.touch_deployer(event.deployer)
            scored_tokens.append(scored)

        scored_tokens.sort(key=lambda s: s.score, reverse=True)
        click.echo(f"{'#':<3} {'Score':<7} {'Symbol':<12} {'Name':<28} {'MCap':<8}")
        click.echo("-" * 65)
        for i, s in enumerate(scored_tokens[:top], 1):
            click.echo(
                f"{i:<3} {s.score:<+7.2f} {s.event.symbol[:11]:<12} "
                f"{s.event.name[:26]:<28} {s.event.market_cap_sol:<8.1f}"
            )
        if not scored_tokens:
            click.echo("No new tokens in window.")

    asyncio.run(_scan())


@cli.command()
@click.argument("mint")
def check(mint: str) -> None:
    """One-shot analysis of any pump.fun token by mint address."""
    cfg = get_config()
    _configure_logging(cfg.log_level)

    async def _check() -> None:
        click.echo(f"🔍 Analyzing {mint}...\n")
        meta = await enrich(
            mint, helius_key=cfg.helius_api_key,
            bitquery_key=cfg.bitquery_api_key,
        )
        click.echo(f"Description: {meta.description or '(none)'}")
        click.echo(f"Twitter:     {meta.twitter or '(none)'}")
        click.echo(f"Website:     {meta.website or '(none)'}")
        click.echo(f"Top holder:  {meta.top_holder_share:.1%}")
        click.echo(f"Concentrated: {meta.looks_concentrated}")
        click.echo(f"\nSolscan: https://solscan.io/token/{mint}")

    asyncio.run(_check())


@cli.command()
def doctor() -> None:
    """Check environment and dependencies."""
    click.echo("🩺 PumpPortal Doctor\n")
    py = sys.version_info
    click.echo(f"✓ Python {py.major}.{py.minor}.{py.micro}")

    ok = True
    for mod_name in ("httpx", "websockets", "click", "rich", "textual"):
        try:
            __import__(mod_name)
            click.echo(f"✓ {mod_name}")
        except ImportError:
            click.echo(f"✗ {mod_name} — not installed")
            ok = False

    cfg = get_config()
    click.echo(f"\nConfig:")
    click.echo(f"  Database: {cfg.database_path}")
    click.echo(f"  Helius key: {'✓ set' if cfg.helius_api_key else '○ not set (optional)'}")

    if ok:
        click.echo("\n✓ All good. Run `pumpportal tui` to launch the explorer.")
    else:
        click.echo("\n✗ Some dependencies are missing. Run: pip install -e '.[dev]'")
        sys.exit(1)


if __name__ == "__main__":
    cli()
