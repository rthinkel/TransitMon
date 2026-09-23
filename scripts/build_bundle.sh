#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="0.1.1"
NAME="TransitMon-v${VERSION}-linux"
DIST="$ROOT/dist"
BUNDLE="$DIST/$NAME"
ZIP="$DIST/$NAME.zip"

rm -rf "$BUNDLE" "$ZIP" "$ZIP.sha256"
mkdir -p "$BUNDLE/src" "$BUNDLE/man" "$BUNDLE/scripts" "$BUNDLE/vendor"

cp -R "$ROOT/src/." "$BUNDLE/src/"
find "$BUNDLE/src" -type d \( -name '__pycache__' -o -name '*.egg-info' \) -prune -exec rm -rf {} +
find "$BUNDLE/src" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

cp "$ROOT/README.md" "$ROOT/LICENSE" "$BUNDLE/"
cp "$ROOT/run-transitmon.sh" "$ROOT/run-transitprobe.sh" "$BUNDLE/"
cp "$ROOT/scripts/bootstrap_runtime.sh" "$BUNDLE/scripts/"
cp "$ROOT/man/transitmon.1" "$ROOT/man/transitprobe.1" "$BUNDLE/man/"
chmod +x "$BUNDLE/run-transitmon.sh" "$BUNDLE/run-transitprobe.sh" "$BUNDLE/scripts/bootstrap_runtime.sh"

# Vendor runtime dependencies into the release bundle so first launch requires
# only python3. No pip, virtualenv, or Internet access is needed on the vehicle.
python3 -m pip install --disable-pip-version-check \
  --target "$BUNDLE/vendor" "obd>=0.7.1"
find "$BUNDLE/vendor" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$BUNDLE/vendor" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

cat > "$BUNDLE/QUICKSTART.txt" <<'EOF'
TransitMon v0.1.1 Quick Start
=============================

Requirements:
  - Linux (Debian/Raspberry Pi OS recommended)
  - Python 3.10 or newer

No pip, virtual environment, or Internet connection is required for this
release bundle. Runtime Python packages are included in ./vendor.

Run without OBD hardware:
  ./run-transitprobe.sh scan --mock
  ./run-transitmon.sh --mock

With a USB OBD adapter:
  ./run-transitprobe.sh scan --port /dev/ttyUSB0
  ./run-transitmon.sh --port /dev/ttyUSB0

If /dev/ttyUSB0 is permission denied on Debian:
  sudo usermod -aG dialout "$USER"
Then log out and back in.

Man pages are included in ./man. View them without installing:
  man ./man/transitprobe.1
  man ./man/transitmon.1

NOTE FOR SOURCE CHECKOUTS:
A GitHub source checkout does not include ./vendor. The launchers will create a
local .venv and install dependencies. On Debian that requires python3-venv and
python3-pip. The downloadable release bundle does not have this requirement.
EOF

(
  cd "$DIST"
  zip -qr "$NAME.zip" "$NAME"
  sha256sum "$NAME.zip" > "$NAME.zip.sha256"
)

echo "Built: $ZIP"
