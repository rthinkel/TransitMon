#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:?TransitMon root path required}"
APP_NAME="${2:-TransitMon}"
VENV="$ROOT/.venv"
READY="$VENV/.transitmon-v0.1.1-ready"

if ! command -v python3 >/dev/null 2>&1; then
  echo "$APP_NAME requires Python 3.10 or newer." >&2
  exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
  echo "$APP_NAME requires Python 3.10 or newer." >&2
  exit 1
fi

# Release bundles vendor all runtime dependencies. No pip, venv, or network
# access is needed in this mode.
if [[ -d "$ROOT/vendor" ]]; then
  export PYTHONPATH="$ROOT/vendor:$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
  export TRANSITMON_PYTHON="$(command -v python3)"
  return 0
fi

# Source checkouts do not contain vendored dependencies. Bootstrap a local
# venv, but detect Debian's common partial-venv/no-pip condition explicitly.
if [[ -x "$VENV/bin/python" ]] && ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  "$VENV/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
fi

if [[ ! -x "$VENV/bin/python" ]] || ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  rm -rf "$VENV"
  echo "Creating TransitMon virtual environment..."
  if ! python3 -m venv "$VENV"; then
    cat >&2 <<'EOF'

TransitMon could not create a usable Python virtual environment.
On Debian/Ubuntu install the required Python packages, then try again:

  sudo apt update
  sudo apt install -y python3-venv python3-pip

Then remove any partial environment and rerun the launcher:

  rm -rf .venv
EOF
    exit 1
  fi
fi

if ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
  cat >&2 <<'EOF'

The virtual environment was created without pip.
On Debian/Ubuntu run:

  sudo apt update
  sudo apt install -y python3-venv python3-pip
  rm -rf .venv

Then run TransitMon again.
EOF
  exit 1
fi

if [[ ! -f "$READY" ]]; then
  echo "Installing TransitMon runtime dependencies..."
  "$VENV/bin/python" -m pip install --disable-pip-version-check "obd>=0.7.1"
  touch "$READY"
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export TRANSITMON_PYTHON="$VENV/bin/python"
