"""Textual TUI — live pump.fun explorer.

Keys:
  q      quit
  c      clear the table
  f      toggle filter (show only score >= 0.5)
  r      reload from local memory
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import DataTable, Footer, Header, Static

from .config import get_config
from .curator import score_token
from .memory import Memory
from .sources.deployer import profile_from_memory
from .sources.pumpfun import stream_new_tokens
from .sources.token_meta import enrich


COLUMNS = ("time", "symbol", "name", "score", "mcap (SOL)", "deployer")


def _short(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


class PumpPortalApp(App):
    """Live terminal explorer for pump.fun launches."""

    CSS = """
    Screen { background: $surface; }
    #status { padding: 0 1; color: $text-muted; }
    DataTable { height: 1fr; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("c", "clear", "Clear"),
        Binding("f", "toggle_filter", "Filter (score≥0.5)"),
        Binding("r", "reload", "Reload from memory"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.cfg = get_config()
        self.memory = Memory(self.cfg.database_path)
        self.filter_high_only = False
        self.row_count = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Vertical():
            yield Static(self._status_text(), id="status")
            table = DataTable(zebra_stripes=True, cursor_type="row")
            for col in COLUMNS:
                table.add_column(col, key=col)
            yield table
        yield Footer()

    def _status_text(self) -> str:
        flt = "filter: score≥0.5" if self.filter_high_only else "filter: off"
        return (
            f"🚪 PumpPortal — live pump.fun explorer  |  "
            f"{flt}  |  rows: {self.row_count}"
        )

    def _update_status(self) -> None:
        self.query_one("#status", Static).update(self._status_text())

    def on_mount(self) -> None:
        self.run_worker(self._populate_from_memory(), exclusive=False)
        self.run_worker(self._stream_loop(), exclusive=True, name="stream")

    async def _populate_from_memory(self) -> None:
        table = self.query_one(DataTable)
        for row in self.memory.recent_tokens(limit=50):
            self._add_row_from_dict(table, row)

    def _add_row_from_dict(self, table: DataTable, row: dict) -> None:
        if self.filter_high_only and (row.get("score") or 0) < 0.5:
            return
        deployer_record = self.memory.deployer_record(row.get("deployer", ""))
        deployer_label = "🟢 NEW WALLET"
        if deployer_record and deployer_record.get("launch_count", 0) > 0:
            launches = deployer_record["launch_count"]
            rugs = deployer_record["rug_count"]
            rate = rugs / launches if launches else 0.0
            if launches >= 3 and rate >= 0.6:
                deployer_label = "🔴 SERIAL OFFENDER"
            elif rate > 0.3:
                deployer_label = "🟡 RISKY"
            elif launches > 5:
                deployer_label = "🟡 SERIAL LAUNCHER"
            elif rate == 0:
                deployer_label = "🟢 CLEAN"
            else:
                deployer_label = "🟡 MIXED"
        seen = row.get("first_seen_at", "")
        time_str = seen[11:19] if len(seen) > 19 else seen
        table.add_row(
            time_str,
            _short(row.get("symbol") or "", 10),
            _short(row.get("name") or "", 24),
            f"{row.get('score') or 0:+.2f}",
            f"{row.get('market_cap_sol') or 0:.1f}",
            deployer_label,
            key=row.get("mint"),
        )
        self.row_count += 1
        self._update_status()

    async def _stream_loop(self) -> None:
        table = self.query_one(DataTable)
        while True:
            try:
                async for event in stream_new_tokens(self.cfg.pump_portal_ws_url):
                    if self.memory.has_seen_token(event.mint):
                        continue
                    meta = await enrich(
                        event.mint,
                        helius_key=self.cfg.helius_api_key,
                        bitquery_key=self.cfg.bitquery_api_key,
                    )
                    deployer = profile_from_memory(self.memory, event.deployer)
                    scored = score_token(event, meta, deployer)
                    self.memory.record_token(
                        mint=event.mint,
                        symbol=event.symbol,
                        name=event.name,
                        deployer=event.deployer,
                        score=scored.score,
                        market_cap_sol=event.market_cap_sol,
                        initial_sol=event.initial_sol,
                    )
                    self.memory.touch_deployer(event.deployer)
                    if self.filter_high_only and scored.score < 0.5:
                        continue
                    table.add_row(
                        datetime.now(timezone.utc).strftime("%H:%M:%S"),
                        _short(event.symbol, 10),
                        _short(event.name, 24),
                        f"{scored.score:+.2f}",
                        f"{event.market_cap_sol:.1f}",
                        scored.deployer.risk_label,
                        key=event.mint,
                    )
                    self.row_count += 1
                    self._update_status()
            except Exception as e:
                self.notify(f"stream error: {e} — reconnecting", severity="warning")
                await asyncio.sleep(2)

    def action_clear(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        self.row_count = 0
        self._update_status()

    def action_toggle_filter(self) -> None:
        self.filter_high_only = not self.filter_high_only
        self._update_status()
        self.notify(
            f"Filter {'on (score≥0.5)' if self.filter_high_only else 'off'}",
            timeout=2,
        )

    def action_reload(self) -> None:
        self.action_clear()
        self.run_worker(self._populate_from_memory(), exclusive=False)


def run_tui() -> None:
    PumpPortalApp().run()
