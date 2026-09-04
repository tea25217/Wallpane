from wallpane.displays import parse_xrandr_listmonitors, parse_xrandr_query


LISTMONITORS = """\
Monitors: 2
 0: +*HDMI-1 1920/531x1080/299+0+0  HDMI-1
 1: +DP-1 2560/597x1440/336+1920+-180  DP-1
"""

QUERY = """\
Screen 0: minimum 320 x 200, current 4480 x 1440, maximum 16384 x 16384
HDMI-1 connected primary 1920x1080+0+0 (normal left inverted right x axis y axis) 531mm x 299mm
DP-1 connected 2560x1440+1920+-180 (normal left inverted right x axis y axis) 597mm x 336mm
DP-2 disconnected (normal left inverted right x axis y axis)
"""


def test_parse_listmonitors_geometry_and_primary() -> None:
    monitors = parse_xrandr_listmonitors(LISTMONITORS)
    assert [m.key for m in monitors] == ["HDMI-1", "DP-1"]
    assert monitors[0].primary is True
    assert monitors[1].primary is False
    assert (monitors[0].width, monitors[0].height, monitors[0].x, monitors[0].y) == (1920, 1080, 0, 0)
    assert (monitors[1].width, monitors[1].height, monitors[1].x, monitors[1].y) == (2560, 1440, 1920, -180)


def test_parse_query_ignores_disconnected() -> None:
    monitors = parse_xrandr_query(QUERY)
    assert [m.key for m in monitors] == ["HDMI-1", "DP-1"]
    assert monitors[0].primary is True
    assert monitors[1].y == -180
