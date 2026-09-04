from pathlib import Path

from wallpane.cli import split_cli_assignment
from wallpane.compose import FitMode


def test_split_assignment_with_mode() -> None:
    key, path, mode = split_cli_assignment("HDMI-1=/tmp/a.jpg:contain")
    assert key == "HDMI-1"
    assert path == Path("/tmp/a.jpg")
    assert mode is FitMode.CONTAIN


def test_split_assignment_default_cover() -> None:
    key, path, mode = split_cli_assignment("DP-1=/home/me/Pictures/wall.png")
    assert key == "DP-1"
    assert path == Path("/home/me/Pictures/wall.png")
    assert mode is FitMode.COVER


def test_split_assignment_colon_in_name_but_not_mode() -> None:
    key, path, mode = split_cli_assignment("eDP-1=/tmp/foo:bar.png")
    assert key == "eDP-1"
    assert path == Path("/tmp/foo:bar.png")
    assert mode is FitMode.COVER
