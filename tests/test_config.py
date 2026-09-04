from pathlib import Path

from wallpane.compose import Assignment, FitMode
from wallpane.config import AppConfig


def test_to_json_accepts_string_mode(tmp_path: Path) -> None:
    image = tmp_path / "a.png"
    image.write_bytes(b"x")
    config = AppConfig(
        fill="#000000",
        assignments={"HDMI-1": Assignment(path=image, mode="cover")},  # type: ignore[arg-type]
    )
    payload = config.to_json()
    assert payload["assignments"]["HDMI-1"]["mode"] == "cover"


def test_to_json_accepts_enum_mode(tmp_path: Path) -> None:
    image = tmp_path / "a.png"
    image.write_bytes(b"x")
    config = AppConfig(
        fill="#010101",
        assignments={"DP-1": Assignment(path=image, mode=FitMode.CONTAIN)},
    )
    payload = config.to_json()
    assert payload["assignments"]["DP-1"]["mode"] == "contain"
    assert payload["fill"] == "#010101"
