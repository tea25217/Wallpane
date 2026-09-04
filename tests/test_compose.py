from __future__ import annotations

from pathlib import Path

from PIL import Image

from wallpane.compose import Assignment, FitMode, Monitor, compose, fit_image, parse_fit_mode, virtual_desktop


def _solid(size: tuple[int, int], color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", size, color)


def test_parse_fit_mode_aliases() -> None:
    assert parse_fit_mode("zoom") is FitMode.COVER
    assert parse_fit_mode("fit") is FitMode.CONTAIN
    assert parse_fit_mode("stretched") is FitMode.STRETCH
    assert parse_fit_mode("center") is FitMode.CENTER
    assert parse_fit_mode(FitMode.COVER) is FitMode.COVER
    assert parse_fit_mode("FitMode.cover") is FitMode.COVER


def test_cover_crops_to_fill() -> None:
    src = _solid((10, 20), (255, 0, 0))
    out = fit_image(src, (10, 10), FitMode.COVER, fill=(0, 0, 0))
    assert out.size == (10, 10)
    assert out.getpixel((5, 5)) == (255, 0, 0)


def test_cover_accepts_qt_string_mode() -> None:
    src = _solid((10, 20), (255, 0, 0))
    out = fit_image(src, (10, 10), "cover", fill=(0, 0, 0))  # type: ignore[arg-type]
    assert out.getpixel((5, 5)) == (255, 0, 0)


def test_contain_keeps_full_image_and_letterbox() -> None:
    src = _solid((10, 10), (0, 255, 0))
    out = fit_image(src, (20, 10), FitMode.CONTAIN, fill=(0, 0, 255))
    assert out.size == (20, 10)
    assert out.getpixel((0, 5)) == (0, 0, 255)
    assert out.getpixel((10, 5)) == (0, 255, 0)
    assert out.getpixel((19, 5)) == (0, 0, 255)


def test_stretch_fills_and_ignores_aspect() -> None:
    src = _solid((4, 8), (255, 255, 0))
    out = fit_image(src, (8, 4), FitMode.STRETCH, fill=(0, 0, 0))
    assert out.size == (8, 4)
    assert out.getpixel((0, 0)) == (255, 255, 0)
    assert out.getpixel((7, 3)) == (255, 255, 0)


def test_center_does_not_upscale() -> None:
    src = _solid((4, 4), (255, 0, 255))
    out = fit_image(src, (10, 10), FitMode.CENTER, fill=(1, 2, 3))
    assert out.getpixel((0, 0)) == (1, 2, 3)
    assert out.getpixel((5, 5)) == (255, 0, 255)


def test_compose_places_each_monitor(tmp_path: Path) -> None:
    left = tmp_path / "left.png"
    right = tmp_path / "right.png"
    _solid((8, 8), (255, 0, 0)).save(left)
    _solid((8, 8), (0, 0, 255)).save(right)

    monitors = [
        Monitor(key="HDMI-1", x=0, y=0, width=10, height=10, primary=True),
        Monitor(key="DP-1", x=10, y=-2, width=12, height=14),
    ]
    image = compose(
        monitors,
        {
            "HDMI-1": Assignment(left, FitMode.STRETCH),
            "DP-1": Assignment(right, FitMode.STRETCH),
        },
        fill=(0, 0, 0),
    )
    min_x, min_y, width, height = virtual_desktop(monitors)
    assert (min_x, min_y, width, height) == (0, -2, 22, 14)
    assert image.size == (22, 14)
    assert image.getpixel((5, 2 + 5)) == (255, 0, 0)
    assert image.getpixel((10 + 6, 0 + 7)) == (0, 0, 255)
    assert image.getpixel((0, 0)) == (0, 0, 0)
