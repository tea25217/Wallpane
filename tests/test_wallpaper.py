import os
import subprocess

from PIL import Image

from wallpane.hostcmd import sanitized_env
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


def test_sanitized_env_drops_appimage_libraries(monkeypatch) -> None:
    monkeypatch.setenv("LD_LIBRARY_PATH", "/tmp/appimage-libs")
    monkeypatch.setenv("GSETTINGS_SCHEMA_DIR", "/tmp/fake-schemas")
    monkeypatch.setenv("PYTHONHOME", "/tmp/py")
    env = sanitized_env()
    assert "LD_LIBRARY_PATH" not in env
    assert "GSETTINGS_SCHEMA_DIR" not in env
    assert "PYTHONHOME" not in env
    assert env["PATH"].startswith("/usr/bin:/bin:/usr/local/bin:")


def test_apply_cinnamon_sets_spanned_uri(monkeypatch, tmp_path) -> None:
    from wallpane import wallpaper as wp

    monkeypatch.setattr(wp.os, "name", "posix")
    monkeypatch.setenv("XDG_CURRENT_DESKTOP", "X-Cinnamon")
    image = tmp_path / "composed.png"
    Image.new("RGB", (4, 4), (10, 20, 30)).save(image)

    stored: dict[tuple[str, str], str] = {}
    calls: list[list[str]] = []

    def fake_which(name: str) -> str | None:
        if name == "gsettings":
            return "/usr/bin/gsettings"
        return None

    def fake_run(argv: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(list(argv))
        if len(argv) > 1 and argv[1] == "set":
            stored[(argv[2], argv[3])] = argv[4]
            return subprocess.CompletedProcess(argv, 0, "", "")
        if len(argv) > 1 and argv[1] == "get":
            value = stored.get((argv[2], argv[3]), "")
            return subprocess.CompletedProcess(argv, 0, f"'{value}'\n", "")
        return subprocess.CompletedProcess(argv, 1, "", "unexpected")

    monkeypatch.setattr(wp, "which_host", fake_which)
    monkeypatch.setattr(wp, "run_host", fake_run)
    monkeypatch.setattr(wp, "log_apply", lambda _message: None)

    apply_composed_image(image, fill_hex="#112233")

    schemas = {cmd[2] for cmd in calls if len(cmd) > 2}
    assert "org.gnome.desktop.background" not in schemas
    cinnamon_sets = {
        cmd[3]: cmd[4]
        for cmd in calls
        if len(cmd) > 4 and cmd[1] == "set" and cmd[2] == "org.cinnamon.desktop.background"
    }
    assert cinnamon_sets["picture-options"] == "spanned"
    assert cinnamon_sets["primary-color"] == "#112233"
    assert cinnamon_sets["picture-uri"].startswith("file://")
    assert cinnamon_sets["picture-uri-dark"] == cinnamon_sets["picture-uri"]
    assert any(cmd[3] == "slideshow-enabled" and cmd[4] == "false" for cmd in calls if len(cmd) > 4)
