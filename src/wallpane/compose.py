from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from PIL import Image

Rgb = tuple[int, int, int]


class FitMode(str, Enum):
    """How an image is fitted into a display rectangle."""

    COVER = "cover"
    CONTAIN = "contain"
    STRETCH = "stretch"
    CENTER = "center"


@dataclass(frozen=True)
class Monitor:
    key: str
    x: int
    y: int
    width: int
    height: int
    primary: bool = False
    label: str = ""

    @property
    def display_name(self) -> str:
        return self.label or self.key


@dataclass
class Assignment:
    path: Path
    mode: FitMode = FitMode.COVER


def parse_fit_mode(value: str) -> FitMode:
    normalized = value.strip().lower().replace("-", "_")
    aliases = {
        "zoom": FitMode.COVER,
        "fill": FitMode.COVER,
        "crop": FitMode.COVER,
        "short": FitMode.COVER,
        "fit": FitMode.CONTAIN,
        "scaled": FitMode.CONTAIN,
        "long": FitMode.CONTAIN,
        "letterbox": FitMode.CONTAIN,
        "stretched": FitMode.STRETCH,
        "scale": FitMode.STRETCH,
        "centered": FitMode.CENTER,
        "centre": FitMode.CENTER,
    }
    if normalized in aliases:
        return aliases[normalized]
    return FitMode(normalized)


def as_rgb(image: Image.Image, fill: Rgb) -> Image.Image:
    if image.mode == "RGB":
        return image
    rgba = image.convert("RGBA")
    background = Image.new("RGB", rgba.size, fill)
    background.paste(rgba, mask=rgba.split()[-1])
    return background


def fit_image(
    source: Image.Image,
    size: tuple[int, int],
    mode: FitMode,
    fill: Rgb = (0, 0, 0),
) -> Image.Image:
    dest_w, dest_h = size
    if dest_w < 1 or dest_h < 1:
        raise ValueError("destination size must be positive")

    rgb = as_rgb(source, fill)
    canvas = Image.new("RGB", (dest_w, dest_h), fill)
    src_w, src_h = rgb.size

    if mode is FitMode.STRETCH:
        canvas.paste(rgb.resize((dest_w, dest_h), Image.Resampling.LANCZOS), (0, 0))
        return canvas

    if mode is FitMode.CENTER:
        canvas.paste(rgb, ((dest_w - src_w) // 2, (dest_h - src_h) // 2))
        return canvas

    if mode is FitMode.COVER:
        scale = max(dest_w / src_w, dest_h / src_h)
    else:
        scale = min(dest_w / src_w, dest_h / src_h)

    new_w = max(1, round(src_w * scale))
    new_h = max(1, round(src_h * scale))
    resized = rgb.resize((new_w, new_h), Image.Resampling.LANCZOS)
    canvas.paste(resized, ((dest_w - new_w) // 2, (dest_h - new_h) // 2))
    return canvas


def virtual_desktop(monitors: list[Monitor]) -> tuple[int, int, int, int]:
    if not monitors:
        raise ValueError("at least one monitor is required")
    min_x = min(m.x for m in monitors)
    min_y = min(m.y for m in monitors)
    max_x = max(m.x + m.width for m in monitors)
    max_y = max(m.y + m.height for m in monitors)
    return min_x, min_y, max_x - min_x, max_y - min_y


def compose(
    monitors: list[Monitor],
    assignments: dict[str, Assignment],
    fill: Rgb = (0, 0, 0),
) -> Image.Image:
    min_x, min_y, width, height = virtual_desktop(monitors)
    canvas = Image.new("RGB", (width, height), fill)
    for monitor in monitors:
        assignment = assignments.get(monitor.key)
        if assignment is None:
            continue
        with Image.open(assignment.path) as opened:
            fitted = fit_image(opened, (monitor.width, monitor.height), assignment.mode, fill)
        canvas.paste(fitted, (monitor.x - min_x, monitor.y - min_y))
    return canvas
