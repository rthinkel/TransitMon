#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="0.1.0"
NAME="TransitMon-v${VERSION}-linux"
DIST="$ROOT/dist"
BUNDLE="$DIST/$NAME"
ZIP="$DIST/$NAME.zip"

rm -rf "$BUNDLE" "$ZIP"
mkdir -p "$BUNDLE/src" "$BUNDLE/man" "$BUNDLE/wheels"

cp -R "$ROOT/src/." "$BUNDLE/src/"
cp "$ROOT/README.md" "$ROOT/LICENSE" "$BUNDLE/"
cp "$ROOT/run-transitmon.sh" "$ROOT/run-transitprobe.sh" "$BUNDLE/"
cp "$ROOT/man/transitmon.1" "$ROOT/man/transitprobe.1" "$BUNDLE/man/"
chmod +x "$BUNDLE/run-transitmon.sh" "$BUNDLE/run-transitprobe.sh"

python3 -m pip download --disable-pip-version-check \
  --dest "$BUNDLE/wheels" "obd>=0.7.1"

cat > "$BUNDLE/QUICKSTART.txt" <<'EOF'
TransitMon v0.1.0 Quick Start
=============================

Requirements:
  - Linux (Debian/Raspberry Pi OS recommended)
  - Python 3.10 or newer
  - python3-venv installed

Run without OBD hardware:
  ./run-transitprobe.sh scan --mock
  ./run-transitmon.sh --mock

With a USB OBD adapter:
  ./run-transitprobe.sh scan --port /dev/ttyUSB0
  ./run-transitmon.sh --port /dev/ttyUSB0

The first launch creates .venv locally and installs dependencies from the
included wheels directory. Internet access is not required.

If /dev/ttyUSB0 is permission denied on Debian:
  sudo usermod -aG dialout "$USER"
Then log out and back in.

Man pages are included in ./man. View them without installing:
  man ./man/transitprobe.1
  man ./man/transitmon.1
EOF

(
  cd "$DIST"
  zip -qr "$NAME.zip" "$NAME"
  sha256sum "$NAME.zip" > "$NAME.zip.sha256"
)

echo "Built: $ZIP"
