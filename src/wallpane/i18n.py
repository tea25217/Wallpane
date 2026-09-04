from __future__ import annotations

import locale
from typing import Final

_EN: Final[dict[str, str]] = {
    "app_name": "Wallpane",
    "window_title": "Wallpane — per-display wallpapers",
    "apply": "Apply",
    "preview": "Preview",
    "browse": "Choose image…",
    "clear": "Clear",
    "fill_color": "Letterbox / empty color",
    "fit_mode": "Fit",
    "mode_cover": "Cover (match short side, crop)",
    "mode_contain": "Contain (match long side, letterbox)",
    "mode_stretch": "Stretch (ignore aspect ratio)",
    "mode_center": "Center (original size)",
    "drop_hint": "Drop an image here, or click to choose",
    "primary": "Primary",
    "no_displays": "No displays were detected.",
    "need_image": "Assign at least one image before applying.",
    "applied": "Wallpaper applied.",
    "apply_failed": "Could not apply the wallpaper.",
    "not_linux": "Applying wallpapers is only supported on Linux (LMDE / Cinnamon).",
    "preview_title": "Composed wallpaper",
    "same_all": "Use this image on every display",
    "refresh": "Refresh displays",
    "status_ready": "Drop an image onto each display, pick a fit mode, then Apply.",
    "display_size": "{name}  {width}×{height}",
}

_JA: Final[dict[str, str]] = {
    "app_name": "Wallpane",
    "window_title": "Wallpane — ディスプレイごとの壁紙",
    "apply": "適用",
    "preview": "プレビュー",
    "browse": "画像を選ぶ…",
    "clear": "クリア",
    "fill_color": "余白・未設定の色",
    "fit_mode": "アジャスト",
    "mode_cover": "カバー（短辺に合わせる・はみ出し切り取り）",
    "mode_contain": "フィット（長辺に合わせる・余白）",
    "mode_stretch": "引き延ばす（縦横比を変える）",
    "mode_center": "中央（実寸）",
    "drop_hint": "画像をドロップ、またはクリックして選択",
    "primary": "プライマリ",
    "no_displays": "ディスプレイを検出できませんでした。",
    "need_image": "適用する前に、少なくとも1枚の画像を割り当ててください。",
    "applied": "壁紙を適用しました。",
    "apply_failed": "壁紙を適用できませんでした。",
    "not_linux": "壁紙の適用は Linux（LMDE / Cinnamon）でのみサポートしています。",
    "preview_title": "合成プレビュー",
    "same_all": "この画像を全ディスプレイに使う",
    "refresh": "ディスプレイを再検出",
    "status_ready": "各ディスプレイに画像をドロップし、アジャスト方法を選んで「適用」してください。",
    "display_size": "{name}  {width}×{height}",
}


def _is_japanese() -> bool:
    candidates: list[str | None] = []
    try:
        if hasattr(locale, "LC_MESSAGES"):
            candidates.append(locale.getlocale(locale.LC_MESSAGES)[0])
    except (ValueError, TypeError, locale.Error):
        pass
    try:
        candidates.append(locale.getlocale()[0])
    except (ValueError, TypeError, locale.Error):
        pass
    try:
        candidates.append(locale.getdefaultlocale()[0])
    except (ValueError, TypeError, locale.Error):
        pass
    for candidate in candidates:
        if candidate and candidate.lower().startswith("ja"):
            return True
    return False


_TABLE = _JA if _is_japanese() else _EN


def t(key: str, **kwargs: object) -> str:
    text = _TABLE.get(key) or _EN[key]
    return text.format(**kwargs) if kwargs else text
