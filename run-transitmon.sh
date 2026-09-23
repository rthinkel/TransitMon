#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV="$ROOT/.venv"
READY="$VENV/.transitmon-v0.1.0-ready"

if ! command -v python3 >/dev/null 2>&1; then
  echo "TransitMon requires Python 3.10 or newer." >&2
  exit 1
fi

if [[ ! -x "$VENV/bin/python" ]]; then
  echo "Creating TransitMon virtual environment..."
  python3 -m venv "$VENV"
fi

if [[ ! -f "$READY" ]]; then
  echo "Installing TransitMon runtime dependencies..."
  if compgen -G "$ROOT/wheels/*" >/dev/null 2>&1; then
    "$VENV/bin/python" -m pip install --disable-pip-version-check \
      --no-index --find-links "$ROOT/wheels" "obd>=0.7.1"
  else
    echo "Offline wheel bundle not found; using pip package index." >&2
    "$VENV/bin/python" -m pip install --disable-pip-version-check "obd>=0.7.1"
  fi
  touch "$READY"
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$VENV/bin/python" -m transitmon.cli "$@"
