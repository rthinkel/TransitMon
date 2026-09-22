from pathlib import Path

from transitlib import OBDClient, VehicleProfile


def test_mock_scan_and_profile_round_trip(tmp_path: Path) -> None:
    client = OBDClient(mock=True)
    client.connect()
    profile = client.scan_profile()

    assert profile.protocol == "MOCK ISO 15765-4 CAN"
    assert "RPM" in profile.command_names
    assert "COOLANT_TEMP" in profile.command_names

    target = tmp_path / "vehicle-profile.json"
    profile.save(target)
    loaded = VehicleProfile.load(target)

    assert loaded.protocol == profile.protocol
    assert loaded.command_names == profile.command_names


def test_mock_query_rejects_unsupported_command() -> None:
    client = OBDClient(mock=True)
    result = client.query("NOT_A_REAL_PID")
    assert result.is_null is True
    assert result.text == "---"


def test_mock_query_returns_units() -> None:
    client = OBDClient(mock=True)
    result = client.query("RPM")
    assert result.is_null is False
    assert result.unit == "rpm"
