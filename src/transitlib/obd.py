from __future__ import annotations

from dataclasses import dataclass
import math
import time
from typing import Any

from .profile import SensorDefinition, VehicleProfile


DASHBOARD_COMMANDS = (
    "RPM",
    "SPEED",
    "COOLANT_TEMP",
    "ENGINE_LOAD",
    "THROTTLE_POS",
    "MAF",
    "SHORT_FUEL_TRIM_1",
    "LONG_FUEL_TRIM_1",
    "CONTROL_MODULE_VOLTAGE",
    "INTAKE_TEMP",
    "FUEL_LEVEL",
)


MOCK_DESCRIPTIONS = {
    "RPM": "Engine RPM",
    "SPEED": "Vehicle speed",
    "COOLANT_TEMP": "Engine coolant temperature",
    "ENGINE_LOAD": "Calculated engine load",
    "THROTTLE_POS": "Throttle position",
    "MAF": "Mass air flow",
    "SHORT_FUEL_TRIM_1": "Short term fuel trim bank 1",
    "LONG_FUEL_TRIM_1": "Long term fuel trim bank 1",
    "CONTROL_MODULE_VOLTAGE": "Control module voltage",
    "INTAKE_TEMP": "Intake air temperature",
}


@dataclass(slots=True)
class QueryValue:
    command: str
    value: str
    unit: str = ""
    is_null: bool = False

    @property
    def text(self) -> str:
        if self.is_null:
            return "---"
        return f"{self.value} {self.unit}".rstrip()


class OBDClient:
    """Shared OBD backend used by transitprobe and transitmon.

    Real mode uses python-OBD. Mock mode deliberately implements the same
    public surface so the UI and probe workflow can be exercised without a car.
    """

    def __init__(self, port: str | None = None, mock: bool = False) -> None:
        self.port = port
        self.mock = mock
        self._connection: Any = None
        self._obd: Any = None

    @property
    def connected(self) -> bool:
        if self.mock:
            return True
        if self._connection is None:
            return False
        try:
            return bool(self._connection.is_connected())
        except Exception:
            return False

    @property
    def protocol(self) -> str:
        if self.mock:
            return "MOCK ISO 15765-4 CAN"
        if self._connection is None:
            return "DISCONNECTED"
        try:
            name = self._connection.protocol_name()
            return str(name or "UNKNOWN")
        except Exception:
            return "UNKNOWN"

    @property
    def effective_port(self) -> str:
        if self.mock:
            return "mock://transit"
        if self._connection is not None:
            try:
                return str(self._connection.port_name() or self.port or "AUTO")
            except Exception:
                pass
        return self.port or "AUTO"

    def connect(self) -> None:
        if self.mock:
            return
        import obd

        self._obd = obd
        self._connection = obd.OBD(portstr=self.port, fast=False)
        if not self.connected:
            raise ConnectionError(
                f"Unable to connect to an OBD adapter on {self.port or 'auto-detected port'}"
            )

    def close(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
            finally:
                self._connection = None

    def reconnect(self) -> None:
        self.close()
        self.connect()

    def supported_commands(self) -> list[SensorDefinition]:
        if self.mock:
            return [
                SensorDefinition(command=name, description=description)
                for name, description in sorted(MOCK_DESCRIPTIONS.items())
            ]
        if not self.connected:
            return []

        items: list[SensorDefinition] = []
        for command in self._connection.supported_commands:
            name = getattr(command, "name", None)
            if not name:
                continue
            description = str(getattr(command, "desc", "") or "")
            items.append(SensorDefinition(command=str(name), description=description))
        items.sort(key=lambda item: item.command)
        return items

    def supports(self, command_name: str) -> bool:
        return command_name in {item.command for item in self.supported_commands()}

    def scan_profile(self) -> VehicleProfile:
        commands = self.supported_commands()
        names = {item.command for item in commands}
        vin: str | None = None
        if "VIN" in names:
            result = self.query("VIN")
            if not result.is_null:
                vin = result.value
        return VehicleProfile(
            adapter_port=self.effective_port,
            protocol=self.protocol,
            vin=vin,
            commands=commands,
        )

    def query(self, command_name: str) -> QueryValue:
        if self.mock:
            return self._mock_query(command_name)
        if not self.connected or self._obd is None:
            return QueryValue(command_name, "---", is_null=True)

        command = getattr(self._obd.commands, command_name, None)
        if command is None or command not in self._connection.supported_commands:
            return QueryValue(command_name, "---", is_null=True)

        try:
            response = self._connection.query(command)
        except Exception:
            return QueryValue(command_name, "---", is_null=True)
        if response is None or response.is_null():
            return QueryValue(command_name, "---", is_null=True)
        return self._normalize_value(command_name, response.value)

    def _normalize_value(self, command_name: str, value: Any) -> QueryValue:
        if value is None:
            return QueryValue(command_name, "---", is_null=True)

        if command_name == "SPEED" and hasattr(value, "to"):
            converted = value.to("mph")
            return QueryValue(command_name, f"{converted.magnitude:.1f}", "mph")
        if command_name in {"COOLANT_TEMP", "INTAKE_TEMP", "AMBIANT_AIR_TEMP", "OIL_TEMP"} and hasattr(value, "to"):
            converted = value.to("degF")
            return QueryValue(command_name, f"{converted.magnitude:.1f}", "°F")

        if hasattr(value, "magnitude"):
            magnitude = value.magnitude
            unit = str(getattr(value, "units", ""))
            if isinstance(magnitude, float):
                rendered = f"{magnitude:.2f}"
            else:
                rendered = str(magnitude)
            friendly_units = {
                "revolutions_per_minute": "rpm",
                "percent": "%",
                "gram / second": "g/s",
                "volt": "V",
            }
            return QueryValue(command_name, rendered, friendly_units.get(unit, unit))

        return QueryValue(command_name, str(value))

    def _mock_query(self, command_name: str) -> QueryValue:
        if command_name not in MOCK_DESCRIPTIONS:
            return QueryValue(command_name, "---", is_null=True)
        t = time.monotonic()
        values: dict[str, tuple[float, str, int]] = {
            "RPM": (820 + 80 * math.sin(t / 2.0), "rpm", 0),
            "SPEED": (0.0, "mph", 1),
            "COOLANT_TEMP": (191 + 2 * math.sin(t / 8.0), "°F", 1),
            "ENGINE_LOAD": (22 + 8 * math.sin(t / 3.0), "%", 1),
            "THROTTLE_POS": (14 + 2 * math.sin(t / 2.5), "%", 1),
            "MAF": (3.8 + 0.4 * math.sin(t / 2.2), "g/s", 2),
            "SHORT_FUEL_TRIM_1": (1.2 + 1.4 * math.sin(t), "%", 1),
            "LONG_FUEL_TRIM_1": (-2.3, "%", 1),
            "CONTROL_MODULE_VOLTAGE": (14.15 + 0.05 * math.sin(t / 4.0), "V", 2),
            "INTAKE_TEMP": (72 + math.sin(t / 10.0), "°F", 1),
        }
        value, unit, precision = values[command_name]
        return QueryValue(command_name, f"{value:.{precision}f}", unit)
