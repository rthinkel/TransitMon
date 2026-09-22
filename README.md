# TransitMon

TransitMon is a small Linux-first OBD-II toolkit intended for a headless Debian Raspberry Pi installed in a vehicle and accessed over SSH.

v0.1 contains three pieces:

- `transitprobe` — discovers the standard OBD-II PIDs the vehicle actually reports as supported and writes a reusable vehicle profile.
- `transitmon` — a simple curses TUI that displays live data from supported PIDs.
- `transitlib` — the shared OBD/profile library used by both programs.

The initial target is a 2012 Ford Transit Connect using a wired USB ELM327/STN-compatible adapter such as the OBDLink EX. v0.1 intentionally limits itself to standard OBD-II PIDs; Ford enhanced-module probing can be added after real hardware results are available.

## Install on Debian

```bash
sudo apt update
sudo apt install -y python3 python3-venv
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

If the adapter appears as `/dev/ttyUSB0`, your user may need serial-port access:

```bash
sudo usermod -aG dialout "$USER"
```

Log out and back in after changing group membership.

## Probe the vehicle first

```bash
transitprobe scan --port /dev/ttyUSB0
```

The default profile is written to:

```text
~/.local/share/transitmon/vehicle-profile.json
```

To watch a small set of discovered values live:

```bash
transitprobe live --port /dev/ttyUSB0
```

## Run TransitMon

```bash
transitmon --port /dev/ttyUSB0
```

Keys:

- `1` / `F1`: dashboard
- `2` / `F2`: supported-PID list
- `r`: reconnect
- `q`: quit

## No adapter yet? Use mock mode

```bash
transitprobe scan --mock
transitprobe live --mock
transitmon --mock
```

Mock mode exists so the Pi/T410 software can be installed and exercised before the OBD cable is available.

## Design principle

TransitMon does not assume a sensor exists merely because OBD-II defines it. `transitprobe` asks the ECU which standard PIDs it supports and saves that inventory. The final dashboard can then be refined using actual results from the specific vehicle.

## v0.1 scope

Included:

- USB serial OBD connection through `python-OBD`
- supported-PID discovery
- JSON vehicle profiles
- live probe mode
- curses TUI
- mock backend
- graceful handling of unsupported/null responses

Deferred until hardware discovery data is available:

- Ford enhanced PIDs/modules (BCM/GEM, ABS, IPC, etc.)
- HS-CAN/MS-CAN module inventory
- raw SocketCAN capture
- persistent logging/SQLite
- daemon/client split
