import os
import subprocess

from PIL import Image

from wallpane.wallpaper import apply_composed_image


def test_detect_cinnamon(monkeypatch) -> None:
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "X-Cinnamon")
    monkeypatch.delenv("DESKTOP_SESSION", raising=False)
    monkeypatch.delenv("CINNAMON_VERSION", raising=False)
    from wallpane.wallpaper import detect_desktop

    assert detect_desktop() == "cinnamon"


def test_detect_unknown(monkeypatch) -> None:
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "")
    monkeypatch.setenv("DESKTOP_SESSION", "")
    monkeypatch.delenv("CINNAMON_VERSION", raising=False)
    from wallpane.wallpaper import detect_desktop

    assert detect_desktop() == "unknown"


def test_file_uri_is_absolute(tmp_path) -> None:
    from wallpane.wallpaper import file_uri

    path = tmp_path / "composed.png"
    path.write_bytes(b"x")
    uri = file_uri(path)
    assert uri.startswith("file://")
    assert os.path.basename(path) in uri


def test_apply_cinnamon_sets_spanned_uri(monkeypatch, tmp_path) -> None:
    from wallpane import wallpaper as wp

    monkeypatch.setattr(wp.os, "name", "posix")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "X-Cinnamon")
    image = tmp_path / "composed.png"
    Image.new("RGB", (4, 4), (10, 20, 30)).save(image)

    calls: list[list[str]] = []

    def fake_run(cmd, check=False, capture_output=True, text=True):
        calls.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(wp.shutil, "which", lambda _: "/usr/bin/gsettings")
    monkeypatch.setattr(wp.subprocess, "run", fake_run)

    apply_composed_image(image, fill_hex="#112233")

    assert calls[0][:3] == ["gsettings", "set", "org.cinnamon.desktop.background"]
    keys = {cmd[3]: cmd[4] for cmd in calls}
    assert keys["picture-options"] == "spanned"
    assert keys["primary-color"] == "#112233"
    assert keys["picture-uri"].startswith("file://")
    assert keys["picture-uri-dark"] == keys["picture-uri"]
