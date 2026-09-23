#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=scripts/bootstrap_runtime.sh
source "$ROOT/scripts/bootstrap_runtime.sh" "$ROOT" "TransitMon"

exec "$TRANSITMON_PYTHON" -m transitmon.cli "$@"
