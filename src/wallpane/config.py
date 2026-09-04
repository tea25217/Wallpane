from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from wallpane.compose import Assignment, FitMode, parse_fit_mode

CONFIG_PATH = Path.home() / ".config" / "wallpane" / "config.json"


@dataclass
class AppConfig:
    fill: str = "#000000"
    assignments: dict[str, Assignment] | None = None

    def to_json(self) -> dict[str, object]:
        data: dict[str, object] = {"fill": self.fill, "assignments": {}}
        stored: dict[str, dict[str, str]] = {}
        for key, assignment in (self.assignments or {}).items():
            stored[key] = {"path": str(assignment.path), "mode": assignment.mode.value}
        data["assignments"] = stored
        return data


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    if not path.is_file():
        return AppConfig(assignments={})
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppConfig(assignments={})

    assignments: dict[str, Assignment] = {}
    for key, value in (raw.get("assignments") or {}).items():
        if not isinstance(value, dict):
            continue
        image = Path(str(value.get("path", "")))
        if not image.is_file():
            continue
        try:
            mode = parse_fit_mode(str(value.get("mode", FitMode.COVER.value)))
        except ValueError:
            mode = FitMode.COVER
        assignments[key] = Assignment(path=image, mode=mode)
    fill = str(raw.get("fill") or "#000000")
    if not fill.startswith("#"):
        fill = "#000000"
    return AppConfig(fill=fill, assignments=assignments)


def save_config(config: AppConfig, path: Path = CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config.to_json(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
