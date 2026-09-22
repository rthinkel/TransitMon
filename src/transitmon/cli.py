from __future__ import annotations

import argparse
import curses
import sys
import time

from transitlib import DASHBOARD_COMMANDS, OBDClient


LABELS = {
    "RPM": "RPM",
    "SPEED": "Speed",
    "COOLANT_TEMP": "Coolant",
    "ENGINE_LOAD": "Engine Load",
    "THROTTLE_POS": "Throttle",
    "MAF": "MAF",
    "SHORT_FUEL_TRIM_1": "STFT Bank 1",
    "LONG_FUEL_TRIM_1": "LTFT Bank 1",
    "CONTROL_MODULE_VOLTAGE": "Module Voltage",
    "INTAKE_TEMP": "Intake Air",
    "FUEL_LEVEL": "Fuel Level",
}


class TransitMonApp:
    def __init__(self, stdscr: curses.window, client: OBDClient) -> None:
        self.stdscr = stdscr
        self.client = client
        self.page = 1
        self.scroll = 0
        self.message = ""
        self.supported = client.supported_commands()
        self.supported_names = {item.command for item in self.supported}
        self.dashboard_commands = [name for name in DASHBOARD_COMMANDS if name in self.supported_names]
        self.cache = {name: "---" for name in self.dashboard_commands}
        self.poll_index = 0

    def run(self) -> None:
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.keypad(True)

        while True:
            self.poll_one()
            self.draw()
            key = self.stdscr.getch()
            if key in (ord("q"), ord("Q")):
                return
            if key in (ord("1"), curses.KEY_F1):
                self.page = 1
                self.scroll = 0
            elif key in (ord("2"), curses.KEY_F2):
                self.page = 2
                self.scroll = 0
            elif key in (ord("r"), ord("R")):
                self.reconnect()
            elif self.page == 2 and key == curses.KEY_DOWN:
                self.scroll = min(self.scroll + 1, max(len(self.supported) - 1, 0))
            elif self.page == 2 and key == curses.KEY_UP:
                self.scroll = max(self.scroll - 1, 0)
            time.sleep(0.10)

    def reconnect(self) -> None:
        self.message = "Reconnecting..."
        self.draw()
        try:
            self.client.reconnect()
            self.supported = self.client.supported_commands()
            self.supported_names = {item.command for item in self.supported}
            self.dashboard_commands = [name for name in DASHBOARD_COMMANDS if name in self.supported_names]
            self.cache = {name: "---" for name in self.dashboard_commands}
            self.poll_index = 0
            self.message = "Reconnected"
        except Exception as exc:
            self.message = f"Reconnect failed: {exc}"

    def poll_one(self) -> None:
        if not self.dashboard_commands:
            return
        command = self.dashboard_commands[self.poll_index % len(self.dashboard_commands)]
        self.poll_index += 1
        self.cache[command] = self.client.query(command).text

    def draw(self) -> None:
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()
        if height < 12 or width < 60:
            self._safe_add(0, 0, "TransitMon requires at least a 60x12 terminal.", curses.A_BOLD)
            self._safe_add(2, 0, f"Current: {width}x{height}")
            self._safe_add(height - 1, 0, "Q Quit")
            self.stdscr.refresh()
            return

        status = "CONNECTED" if self.client.connected else "DISCONNECTED"
        header = f"TransitMon v0.1 | OBD {status} | {self.client.effective_port} | {self.client.protocol}"
        self._safe_add(0, 0, header[:width - 1], curses.A_BOLD)
        self._safe_add(1, 0, "-" * (width - 1))

        if self.page == 1:
            self.draw_dashboard(height, width)
        else:
            self.draw_supported(height, width)

        footer_y = height - 2
        self._safe_add(footer_y, 0, "-" * (width - 1))
        footer = "1/F1 Dash  2/F2 Supported PIDs  R Reconnect  Q Quit"
        self._safe_add(height - 1, 0, footer[:width - 1], curses.A_BOLD)
        if self.message:
            self._safe_add(footer_y, max(0, width - len(self.message) - 2), self.message[: max(width - 2, 1)])
        self.stdscr.refresh()

    def draw_dashboard(self, height: int, width: int) -> None:
        self._safe_add(2, 2, "DASHBOARD", curses.A_BOLD)
        if not self.dashboard_commands:
            self._safe_add(4, 2, "No common dashboard PIDs were reported as supported.")
            self._safe_add(5, 2, "Use transitprobe scan to inspect the complete command inventory.")
            return

        rows = [
            ("RPM", "SPEED"),
            ("COOLANT_TEMP", "ENGINE_LOAD"),
            ("INTAKE_TEMP", "THROTTLE_POS"),
            ("MAF", "CONTROL_MODULE_VOLTAGE"),
            ("SHORT_FUEL_TRIM_1", "LONG_FUEL_TRIM_1"),
            ("FUEL_LEVEL", None),
        ]
        left_x = 2
        right_x = max(width // 2, 32)
        y = 4
        for left, right in rows:
            if y >= height - 3:
                break
            self._draw_field(y, left_x, left)
            if right is not None and right_x < width - 18:
                self._draw_field(y, right_x, right)
            y += 2

    def _draw_field(self, y: int, x: int, command: str) -> None:
        label = LABELS.get(command, command)
        value = self.cache.get(command, "---") if command in self.supported_names else "N/A"
        self._safe_add(y, x, f"{label:<18}")
        self._safe_add(y, x + 19, value, curses.A_BOLD)

    def draw_supported(self, height: int, width: int) -> None:
        self._safe_add(2, 2, f"SUPPORTED COMMANDS ({len(self.supported)})", curses.A_BOLD)
        available_rows = max(height - 6, 1)
        max_scroll = max(len(self.supported) - available_rows, 0)
        self.scroll = min(self.scroll, max_scroll)
        visible = self.supported[self.scroll : self.scroll + available_rows]
        for index, item in enumerate(visible):
            y = 4 + index
            text = f"{item.command:<28} {item.description}"
            self._safe_add(y, 2, text[: max(width - 4, 1)])
        if len(self.supported) > available_rows:
            indicator = f"{self.scroll + 1}-{min(self.scroll + available_rows, len(self.supported))}/{len(self.supported)}"
            self._safe_add(2, max(2, width - len(indicator) - 2), indicator)

    def _safe_add(self, y: int, x: int, text: str, attr: int = 0) -> None:
        height, width = self.stdscr.getmaxyx()
        if y < 0 or y >= height or x < 0 or x >= width:
            return
        try:
            self.stdscr.addstr(y, x, text[: max(width - x - 1, 0)], attr)
        except curses.error:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="transitmon", description="Live OBD-II terminal monitor")
    parser.add_argument("--port", help="serial port, e.g. /dev/ttyUSB0; omit for auto-detection")
    parser.add_argument("--mock", action="store_true", help="use the built-in mock vehicle")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    client = OBDClient(port=args.port, mock=args.mock)
    try:
        client.connect()
        curses.wrapper(lambda stdscr: TransitMonApp(stdscr, client).run())
    except (ConnectionError, OSError) as exc:
        print(f"transitmon: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    finally:
        client.close()


if __name__ == "__main__":
    main()
