from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

XDG_DATA = Path.home() / ".local" / "share" / "wallpane"

CINNAMON_SCHEMA = "org.cinnamon.desktop.background"
GNOME_SCHEMA = "org.gnome.desktop.background"
MATE_SCHEMA = "org.mate.background"
MATE_DESKTOP_SCHEMA = "org.mate.desktop.background"


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


def _gsettings(*args: str) -> subprocess.CompletedProcess[str]:
    if not shutil.which("gsettings"):
        raise WallpaperError("gsettings was not found. Run Wallpane inside a Cinnamon session.")
    return subprocess.run(["gsettings", *args], check=False, capture_output=True, text=True)


def _set(schema: str, key: str, value: str) -> None:
    result = _gsettings("set", schema, key, value)
    if result.returncode != 0:
        raise WallpaperError(result.stderr.strip() or f"gsettings set {schema} {key} failed")


def _try_set(schema: str, key: str, value: str) -> bool:
    result = _gsettings("set", schema, key, value)
    return result.returncode == 0


def file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def output_dir() -> Path:
    path = XDG_DATA
    path.mkdir(parents=True, exist_ok=True)
    return path


def apply_composed_image(image_path: Path, fill_hex: str = "#000000") -> None:
    if os.name == "nt":
        raise WallpaperError("Applying wallpapers is only supported on Linux.")

    image_path = image_path.resolve()
    if not image_path.is_file():
        raise WallpaperError(f"composed image not found: {image_path}")

    uri = file_uri(image_path)
    desktop = detect_desktop()

    if desktop == "mate":
        _try_set(MATE_SCHEMA, "picture-filename", str(image_path))
        _try_set(MATE_DESKTOP_SCHEMA, "picture-filename", str(image_path))
        _try_set(MATE_DESKTOP_SCHEMA, "picture-options", "spanned")
        return

    schema = CINNAMON_SCHEMA if desktop in {"cinnamon", "unknown"} else GNOME_SCHEMA
    try:
        _set(schema, "picture-options", "spanned")
        _try_set(schema, "primary-color", fill_hex)
        _try_set(schema, "color-shading-type", "solid")
        _try_set(schema, "picture-uri-dark", uri)
        _set(schema, "picture-uri", uri)
    except WallpaperError:
        if schema != GNOME_SCHEMA:
            _set(GNOME_SCHEMA, "picture-options", "spanned")
            _try_set(GNOME_SCHEMA, "picture-uri-dark", uri)
            _set(GNOME_SCHEMA, "picture-uri", uri)
        else:
            raise
