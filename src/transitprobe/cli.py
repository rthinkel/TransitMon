from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

from transitlib import DASHBOARD_COMMANDS, OBDClient, default_profile_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="transitprobe",
        description="Discover and inspect OBD-II data exposed by the vehicle.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan = subparsers.add_parser("scan", help="scan supported OBD-II commands and save a profile")
    scan.add_argument("--port", help="serial port, e.g. /dev/ttyUSB0; omit for auto-detection")
    scan.add_argument("--output", type=Path, default=default_profile_path())
    scan.add_argument("--mock", action="store_true", help="use the built-in mock vehicle")

    live = subparsers.add_parser("live", help="display live values for common supported commands")
    live.add_argument("--port", help="serial port, e.g. /dev/ttyUSB0; omit for auto-detection")
    live.add_argument("--interval", type=float, default=1.0, help="seconds between updates")
    live.add_argument("--count", type=int, default=0, help="number of updates; 0 means until Ctrl-C")
    live.add_argument("--mock", action="store_true", help="use the built-in mock vehicle")

    return parser


def make_client(args: argparse.Namespace) -> OBDClient:
    client = OBDClient(port=args.port, mock=args.mock)
    client.connect()
    return client


def cmd_scan(args: argparse.Namespace) -> int:
    client = make_client(args)
    try:
        profile = client.scan_profile()
        saved = profile.save(args.output)
        print("TransitProbe v0.1")
        print(f"Adapter : {profile.adapter_port or 'unknown'}")
        print(f"Protocol: {profile.protocol or 'unknown'}")
        print(f"VIN     : {profile.vin or 'not reported'}")
        print(f"Commands: {len(profile.commands)} supported")
        print()
        for item in profile.commands:
            description = f" - {item.description}" if item.description else ""
            print(f"  {item.command}{description}")
        print()
        print(f"Profile written to {saved}")
        return 0
    finally:
        client.close()


def cmd_live(args: argparse.Namespace) -> int:
    client = make_client(args)
    try:
        supported = {item.command for item in client.supported_commands()}
        commands = [name for name in DASHBOARD_COMMANDS if name in supported]
        if not commands:
            print("No common live dashboard commands were reported as supported.", file=sys.stderr)
            return 2

        iteration = 0
        while args.count <= 0 or iteration < args.count:
            print("\x1b[2J\x1b[H", end="")
            print("TransitProbe live")
            print(f"Port: {client.effective_port}    Protocol: {client.protocol}")
            print("-" * 64)
            for command in commands:
                value = client.query(command)
                print(f"{command:<28} {value.text}")
            iteration += 1
            if args.count <= 0 or iteration < args.count:
                time.sleep(max(args.interval, 0.1))
        return 0
    except KeyboardInterrupt:
        print()
        return 0
    finally:
        client.close()


def main() -> None:
    args = build_parser().parse_args()
    try:
        if args.command == "scan":
            raise SystemExit(cmd_scan(args))
        if args.command == "live":
            raise SystemExit(cmd_live(args))
    except (ConnectionError, OSError) as exc:
        print(f"transitprobe: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
