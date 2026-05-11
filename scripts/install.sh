#!/usr/bin/env bash
set -euo pipefail

PYTHON="${PYTHON:-python3.12}"
INSTALL_DIR="${INSTALL_DIR:-$HOME/pumpportal}"

echo "🚪 Installing PumpPortal..."

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "✗ $PYTHON not found. Install Python 3.10+ first."
  exit 1
fi

if [ -d "$INSTALL_DIR" ]; then
  echo "→ Updating $INSTALL_DIR"
  git -C "$INSTALL_DIR" pull --ff-only
else
  echo "→ Cloning into $INSTALL_DIR"
  git clone https://github.com/yksanjo/pumpportal.git "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"
"$PYTHON" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -e '.[dev]'

echo
echo "✓ Installed."
echo "  Activate:  source $INSTALL_DIR/.venv/bin/activate"
echo "  Run:       pumpportal tui"
