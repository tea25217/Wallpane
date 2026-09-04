from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# Variables the AppImage / PyInstaller runtime injects. They break host
# tools such as gsettings and xrandr if inherited by subprocesses.
_UNSET = (
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "PYTHONHOME",
    "PYTHONPATH",
    "PYTHONNOUSERSITE",
    "QT_PLUGIN_PATH",
    "QT_QPA_PLATFORM_PLUGIN_PATH",
    "QT_QPA_PLATFORM",
    "QT_DEBUG_PLUGINS",
    "GI_TYPELIB_PATH",
    "GIO_MODULE_DIR",
    "GSETTINGS_SCHEMA_DIR",
    "GTK_PATH",
    "GTK_DATA_PREFIX",
    "GDK_PIXBUF_MODULE_FILE",
    "GST_PLUGIN_PATH",
    "APPDIR",
)


def sanitized_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in _UNSET}
    path = env.get("PATH", "/usr/bin:/bin")
    env["PATH"] = "/usr/bin:/bin:/usr/local/bin:" + path
    return env


def which_host(name: str) -> str | None:
    return shutil.which(name, path=sanitized_env().get("PATH", "/usr/bin:/bin"))


def run_host(argv: list[str]) -> subprocess.CompletedProcess[str]:
    env = sanitized_env()
    command = list(argv)
    if command and not os.path.isabs(command[0]):
        located = which_host(command[0])
        if located:
            command[0] = located
    return subprocess.run(command, check=False, capture_output=True, text=True, env=env)


def log_apply(message: str) -> None:
    path = Path.home() / ".cache" / "wallpane" / "apply.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(message.rstrip() + "\n")
    except OSError:
        pass
