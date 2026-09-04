from __future__ import annotations

import os
from pathlib import Path

from wallpane.hostcmd import log_apply, run_host, which_host

XDG_DATA = Path.home() / ".local" / "share" / "wallpane"

CINNAMON_SCHEMA = "org.cinnamon.desktop.background"
CINNAMON_SLIDESHOW_SCHEMA = "org.cinnamon.desktop.background.slideshow"
GNOME_SCHEMA = "org.gnome.desktop.background"
MATE_SCHEMA = "org.mate.background"
MATE_DESKTOP_SCHEMA = "org.mate.desktop.background"

_GI_APPLY = r"""
import sys
import gi
gi.require_version("Gio", "2.0")
from gi.repository import Gio

uri, fill, schema = sys.argv[1], sys.argv[2], sys.argv[3]
settings = Gio.Settings.new(schema)
keys = set(settings.list_keys())
if "picture-options" in keys:
    settings.set_string("picture-options", "spanned")
if "primary-color" in keys:
    settings.set_string("primary-color", fill)
if "color-shading-type" in keys:
    settings.set_string("color-shading-type", "solid")
if "picture-uri-dark" in keys:
    settings.set_string("picture-uri-dark", uri)
if "picture-uri" in keys:
    settings.set_string("picture-uri", "")
    settings.set_string("picture-uri", uri)
try:
    slide = Gio.Settings.new(schema + ".slideshow")
    if "slideshow-enabled" in slide.list_keys():
        slide.set_boolean("slideshow-enabled", False)
except Exception:
    pass
Gio.Settings.sync()
"""


class WallpaperError(RuntimeError):
    pass


def detect_desktop() -> str:
    names = os.environ.get("XDG_CURRENT_DESKTOP", "")
    tokens = {part.strip().upper() for part in names.replace(":", ";").split(";") if part.strip()}
    desktop = os.environ.get("DESKTOP_SESSION", "").upper()
    if "CINNAMON" in tokens or "X-CINNAMON" in tokens or "CINNAMON" in desktop:
        return "cinnamon"
    if "MATE" in tokens or "MATE" in desktop:
        return "mate"
    if "GNOME" in tokens or "GNOME" in desktop:
        return "gnome"
    if os.environ.get("CINNAMON_VERSION"):
        return "cinnamon"
    return "unknown"


def _gsettings(*args: str):
    binary = which_host("gsettings")
    if not binary:
        raise WallpaperError("gsettings was not found. Run Wallpane inside a Cinnamon session.")
    return run_host([binary, *args])


def _set(schema: str, key: str, value: str) -> None:
    result = _gsettings("set", schema, key, value)
    log_apply(f"gsettings set {schema} {key} rc={result.returncode} err={result.stderr.strip()!r}")
    if result.returncode != 0:
        raise WallpaperError(result.stderr.strip() or f"gsettings set {schema} {key} failed")


def _try_set(schema: str, key: str, value: str) -> bool:
    try:
        _set(schema, key, value)
        return True
    except WallpaperError:
        return False


def _get(schema: str, key: str) -> str:
    result = _gsettings("get", schema, key)
    return result.stdout.strip().strip("'\"")


def file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def output_dir() -> Path:
    path = XDG_DATA
    path.mkdir(parents=True, exist_ok=True)
    return path


def _apply_with_gi(uri: str, fill_hex: str, schema: str) -> None:
    python = which_host("python3")
    if not python:
        raise WallpaperError("system python3 not found")
    result = run_host([python, "-c", _GI_APPLY, uri, fill_hex, schema])
    log_apply(f"python3 gi apply rc={result.returncode} err={result.stderr.strip()!r}")
    if result.returncode != 0:
        raise WallpaperError(result.stderr.strip() or "Gio.Settings apply failed")


def _apply_with_gsettings(uri: str, fill_hex: str, schema: str, *, disable_slideshow: bool) -> None:
    _set(schema, "picture-options", "spanned")
    _try_set(schema, "primary-color", fill_hex)
    _try_set(schema, "color-shading-type", "solid")
    _try_set(schema, "picture-uri-dark", uri)
    # Toggle so Cinnamon notices a change even if it cached the previous URI.
    _try_set(schema, "picture-uri", "")
    _set(schema, "picture-uri", uri)
    if disable_slideshow:
        _try_set(CINNAMON_SLIDESHOW_SCHEMA, "slideshow-enabled", "false")


def _verify(schema: str, uri: str) -> None:
    try:
        current = _get(schema, "picture-uri")
    except WallpaperError as exc:
        raise WallpaperError(f"applied wallpaper could not be read back: {exc}") from exc
    if Path(uri).name not in current and uri not in current:
        raise WallpaperError(
            f"Cinnamon still has {current!r} instead of {uri!r}. "
            "gsettings may have written to a different session."
        )


def apply_composed_image(image_path: Path, fill_hex: str = "#000000") -> None:
    if os.name == "nt":
        raise WallpaperError("Applying wallpapers is only supported on Linux.")

    image_path = image_path.resolve()
    if not image_path.is_file():
        raise WallpaperError(f"composed image not found: {image_path}")

    uri = file_uri(image_path)
    desktop = detect_desktop()
    log_apply(f"apply desktop={desktop} uri={uri}")

    if desktop == "mate":
        _try_set(MATE_SCHEMA, "picture-filename", str(image_path))
        _try_set(MATE_DESKTOP_SCHEMA, "picture-filename", str(image_path))
        _try_set(MATE_DESKTOP_SCHEMA, "picture-options", "spanned")
        return

    if desktop == "gnome":
        schema = GNOME_SCHEMA
        disable_slideshow = False
    else:
        # LMDE / unknown: Cinnamon only. Do not silently write GNOME keys.
        schema = CINNAMON_SCHEMA
        disable_slideshow = True

    try:
        _apply_with_gi(uri, fill_hex, schema)
    except WallpaperError as gi_error:
        log_apply(f"gi apply failed: {gi_error}; falling back to gsettings")
        _apply_with_gsettings(uri, fill_hex, schema, disable_slideshow=disable_slideshow)

    _verify(schema, uri)
