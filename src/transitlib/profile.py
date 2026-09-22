from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def default_profile_path() -> Path:
    return Path.home() / ".local" / "share" / "transitmon" / "vehicle-profile.json"


@dataclass(slots=True)
class SensorDefinition:
    command: str
    description: str = ""


@dataclass(slots=True)
class VehicleProfile:
    schema_version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    adapter_port: str | None = None
    protocol: str | None = None
    vin: str | None = None
    commands: list[SensorDefinition] = field(default_factory=list)

    @property
    def command_names(self) -> set[str]:
        return {item.command for item in self.commands}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VehicleProfile":
        commands = [SensorDefinition(**item) for item in data.get("commands", [])]
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            created_at=data.get("created_at") or datetime.now(timezone.utc).isoformat(),
            adapter_port=data.get("adapter_port"),
            protocol=data.get("protocol"),
            vin=data.get("vin"),
            commands=commands,
        )

    def save(self, path: Path | str | None = None) -> Path:
        target = Path(path) if path is not None else default_profile_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")
        return target

    @classmethod
    def load(cls, path: Path | str | None = None) -> "VehicleProfile":
        target = Path(path) if path is not None else default_profile_path()
        return cls.from_dict(json.loads(target.read_text(encoding="utf-8")))
