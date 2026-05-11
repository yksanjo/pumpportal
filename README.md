# 🚪 PumpPortal CLI

> Terminal-based pump.fun explorer. Browse live launches, filter, inspect, and get notified — all from your terminal.

PumpPortal is a self-hosted CLI for the pump.fun community. Built on the free PumpPortal WebSocket, it gives you a Textual-based TUI to watch new launches stream in, filter them by score / deployer / liquidity, and inspect any token in one keystroke. No hosting, no third-party services.

```bash
pumpportal tui          # launch the full terminal UI
pumpportal watch        # plain-text live stream
pumpportal scan -w 60   # collect a 60-second window, then print a ranked report
pumpportal check <mint> # one-shot analysis of any token
```

---

## Quick start

```bash
git clone https://github.com/yksanjo/pumpportal.git
cd pumpportal
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

pumpportal doctor       # sanity check
pumpportal tui
```

Press `q` to quit the TUI. Press `f` to filter, `enter` to inspect a row.

---

## Commands

| Command | Description |
|---------|-------------|
| `pumpportal tui` | Launch the Textual TUI explorer |
| `pumpportal watch` | Plain-text live stream of new launches |
| `pumpportal scan` | Collect tokens for a window, then print a ranked report |
| `pumpportal check <mint>` | One-shot analysis of any pump.fun token |
| `pumpportal doctor` | Check environment |

---

## How it works

- Subscribes to PumpPortal's `subscribeNewToken` channel.
- Scores every launch using the same anti-shill heuristics as [PumpGuard](https://github.com/yksanjo/pumpguard) (deployer history, name quality, supply concentration, liquidity).
- Stores everything in `~/.pumpportal/pumpportal.sqlite` so deployer reputation persists across sessions.

The TUI is built with [Textual](https://textual.textualize.io/) — keyboard-driven, mouse-friendly, runs over SSH.

---

## License

MIT — see [LICENSE](./LICENSE).
