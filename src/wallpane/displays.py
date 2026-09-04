from __future__ import annotations

import os
import re
from typing import Callable

from wallpane.compose import Monitor
from wallpane.hostcmd import run_host, which_host

LISTMONITORS_RE = re.compile(
    r"^\s*\d+:\s+\+?\*?(\S+)\s+(\d+)/\d+x(\d+)/\d+\+(-?\d+)\+(-?\d+)\s+(\S+)\s*$"
)
QUERY_RE = re.compile(
    r"^(\S+)\s+connected(?:\s+primary)?\s+(\d+)x(\d+)\+(-?\d+)\+(-?\d+)",
    re.IGNORECASE,
)


class DisplayError(RuntimeError):
    pass


def parse_xrandr_listmonitors(text: str) -> list[Monitor]:
    monitors: list[Monitor] = []
    for line in text.splitlines():
        match = LISTMONITORS_RE.match(line)
        if not match:
            continue
        name, width, height, x, y, output = match.groups()
        key = output or name
        marker = line.split(":", 1)[-1].split()[0]
        primary = "*" in marker
        monitors.append(
            Monitor(
                key=key,
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                primary=primary,
                label=key,
            )
        )
    return monitors


def parse_xrandr_query(text: str) -> list[Monitor]:
    monitors: list[Monitor] = []
    for line in text.splitlines():
        match = QUERY_RE.match(line)
        if not match:
            continue
        name, width, height, x, y = match.groups()
        monitors.append(
            Monitor(
                key=name,
                x=int(x),
                y=int(y),
                width=int(width),
                height=int(height),
                primary=" primary " in f" {line.lower()} ",
                label=name,
            )
        )
    return monitors


def _run(cmd: list[str]) -> str:
    result = run_host(cmd)
    if result.returncode != 0:
        raise DisplayError(result.stderr.strip() or f"{' '.join(cmd)} failed")
    return result.stdout


def list_from_xrandr() -> list[Monitor]:
    if os.name == "nt" or not which_host("xrandr"):
        raise DisplayError("xrandr is not available")
    try:
        monitors = parse_xrandr_listmonitors(_run(["xrandr", "--listmonitors"]))
        if monitors:
            return monitors
    except DisplayError:
        pass
    monitors = parse_xrandr_query(_run(["xrandr", "--query"]))
    if not monitors:
        raise DisplayError("xrandr reported no connected monitors")
    return monitors


def list_from_qt() -> list[Monitor]:
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    created = False
    if app is None:
        from PySide6.QtWidgets import QApplication

        app = QApplication([])
        created = True
    try:
        screens = app.screens()
        primary = app.primaryScreen()
        monitors: list[Monitor] = []
        for index, screen in enumerate(screens):
            geometry = screen.geometry()
            name = screen.name() or f"screen-{index}"
            monitors.append(
                Monitor(
                    key=name,
                    x=geometry.x(),
                    y=geometry.y(),
                    width=max(1, geometry.width()),
                    height=max(1, geometry.height()),
                    primary=screen is primary,
                    label=name,
                )
            )
        if not monitors:
            raise DisplayError("Qt reported no screens")
        return monitors
    finally:
        if created:
            app.quit()


def list_monitors(qt_provider: Callable[[], list[Monitor]] | None = None) -> list[Monitor]:
    """Prefer xrandr on Linux so the canvas matches Cinnamon's X11 framebuffer."""
    if os.name != "nt":
        try:
            return list_from_xrandr()
        except DisplayError:
            pass
    provider = qt_provider or list_from_qt
    return provider()
