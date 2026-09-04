from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from wallpane import __version__
from wallpane.compose import Assignment, FitMode, compose, parse_fit_mode
from wallpane.displays import DisplayError, list_monitors
from wallpane.wallpaper import WallpaperError, apply_composed_image, detect_desktop, output_dir

_MODE_HINTS = {mode.value for mode in FitMode} | {
    "zoom",
    "fill",
    "crop",
    "short",
    "fit",
    "scaled",
    "long",
    "letterbox",
    "stretched",
    "scale",
    "centered",
    "centre",
}


def split_cli_assignment(text: str) -> tuple[str, Path, FitMode]:
    if "=" not in text:
        raise argparse.ArgumentTypeError("expected DISPLAY=PATH[:mode]")
    key, rest = text.split("=", 1)
    path_text = rest
    mode = FitMode.COVER
    if ":" in rest:
        prefix, suffix = rest.rsplit(":", 1)
        if suffix.lower() in _MODE_HINTS:
            path_text = prefix
            try:
                mode = parse_fit_mode(suffix)
            except ValueError:
                path_text = rest
                mode = FitMode.COVER
    return key, Path(path_text).expanduser(), mode


def parse_cli_assignment(text: str) -> tuple[str, Assignment]:
    key, path, mode = split_cli_assignment(text)
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"image not found: {path}")
    return key, Assignment(path=path, mode=mode)


def _print_monitors() -> int:
    try:
        monitors = list_monitors()
    except DisplayError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for monitor in monitors:
        flag = "*" if monitor.primary else " "
        print(f"{flag} {monitor.key:12} {monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wallpane",
        description="Set a different wallpaper on each display (LMDE / Cinnamon).",
    )
    parser.add_argument("--version", action="version", version=f"wallpane {__version__}")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("gui", help="open the GUI (default)")
    sub.add_parser("list", help="list detected displays")

    apply_p = sub.add_parser("apply", help="compose and apply wallpapers from the CLI")
    apply_p.add_argument(
        "assignments",
        nargs="+",
        metavar="DISPLAY=PATH[:mode]",
        help="e.g. HDMI-1=~/Pictures/a.jpg:cover DP-1=~/Pictures/b.png:contain",
    )
    apply_p.add_argument("--fill", default="#000000", help="letterbox color (default: #000000)")

    args = parser.parse_args(argv)
    command = args.command or "gui"

    if command == "list":
        return _print_monitors()

    if command == "apply":
        try:
            monitors = list_monitors()
        except DisplayError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        assigned: dict[str, Assignment] = {}
        for item in args.assignments:
            key, assignment = parse_cli_assignment(item)
            assigned[key] = assignment

        unknown = [key for key in assigned if key not in {m.key for m in monitors}]
        if unknown:
            print(f"error: unknown display(s): {', '.join(unknown)}", file=sys.stderr)
            return 1

        fill = _hex_to_rgb(args.fill)
        image = compose(monitors, assigned, fill)
        dest = output_dir() / f"composed-{int(time.time())}.png"
        image.save(dest, format="PNG")
        try:
            apply_composed_image(dest, fill_hex=_normalize_hex(args.fill))
        except WallpaperError as exc:
            print(f"error: {exc}", file=sys.stderr)
            print(f"(desktop={detect_desktop()}, wrote {dest})", file=sys.stderr)
            return 1
        print(dest)
        return 0

    from wallpane.gui import run_gui

    return run_gui()


def _normalize_hex(value: str) -> str:
    text = value.strip()
    if not text.startswith("#"):
        text = f"#{text}"
    if len(text) != 7:
        raise argparse.ArgumentTypeError("fill color must be #RRGGBB")
    return text.upper()


def _hex_to_rgb(value: str) -> tuple[int, int, int]:
    text = _normalize_hex(value).lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


if __name__ == "__main__":
    raise SystemExit(main())
