#!/usr/bin/env bash
# Build an x86_64 AppImage that starts on LMDE 7 without host libfuse2.
# Run on Linux (Ubuntu 22.04 is a good glibc baseline).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ARCH="${ARCH:-x86_64}"
APP_NAME="Wallpane"
VERSION="$(python3 -c "from pathlib import Path; import re; t=Path('pyproject.toml').read_text(); print(re.search(r'^version = \"([^\"]+)\"', t, re.M).group(1))")"
URUNTIME_VERSION="${URUNTIME_VERSION:-0.6.1}"
APPIMAGETOOL_URL="${APPIMAGETOOL_URL:-https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage}"
URUNTIME_URL="${URUNTIME_URL:-https://github.com/VHSgunzo/uruntime/releases/download/v${URUNTIME_VERSION}/uruntime-appimage-squashfs-lite-${ARCH}}"

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt pyinstaller
python3 scripts/make_icon.py

export PYTHONPATH="${ROOT}/src${PYTHONPATH:+:$PYTHONPATH}"

pyinstaller --noconfirm --clean \
  --onedir \
  --name wallpane \
  --paths src \
  --hidden-import wallpane \
  --hidden-import wallpane.gui \
  --hidden-import wallpane.cli \
  --hidden-import wallpane.compose \
  --collect-all PySide6 \
  --collect-all PIL \
  --add-data "src/wallpane/resources:wallpane/resources" \
  src/wallpane/__main__.py

if [[ ! -x dist/wallpane/wallpane ]]; then
  echo "PyInstaller did not produce dist/wallpane/wallpane" >&2
  exit 1
fi

rm -rf AppDir
mkdir -p \
  AppDir/usr/bin \
  AppDir/usr/share/applications \
  AppDir/usr/share/icons/hicolor/256x256/apps

cp -a dist/wallpane/. AppDir/usr/bin/
chmod +x AppDir/usr/bin/wallpane
install -m 0755 packaging/AppRun AppDir/AppRun
cp packaging/wallpane.desktop AppDir/wallpane.desktop
cp packaging/wallpane.desktop AppDir/usr/share/applications/wallpane.desktop
cp packaging/wallpane.png AppDir/wallpane.png
cp packaging/wallpane.png AppDir/usr/share/icons/hicolor/256x256/apps/wallpane.png

# Do not run linuxdeploy against the PyInstaller tree: it rewrites RPATH /
# LD_LIBRARY_PATH and commonly breaks bundled Qt on the target distro.

curl -L --fail -o "appimagetool-${ARCH}.AppImage" "$APPIMAGETOOL_URL"
chmod +x "appimagetool-${ARCH}.AppImage"
curl -L --fail -o uruntime "$URUNTIME_URL"
chmod +x uruntime

# Try FUSE, then extract-and-run so Debian 13 / LMDE 7 work without libfuse2.
if grep -aq 'URUNTIME_EXTRACT=[0-9]' uruntime; then
  sed -i 's|URUNTIME_EXTRACT=[0-9]|URUNTIME_EXTRACT=2|' uruntime
else
  echo "uruntime is missing URUNTIME_EXTRACT marker" >&2
  exit 1
fi

export APPIMAGE_EXTRACT_AND_RUN=1
./appimagetool-${ARCH}.AppImage --appimage-extract >/dev/null

mkdir -p dist
OUT="dist/${APP_NAME}-${VERSION}-${ARCH}.AppImage"
ARCH="$ARCH" VERSION="$VERSION" \
  ./squashfs-root/AppRun --no-appstream --runtime-file "$ROOT/uruntime" AppDir "$OUT"

chmod +x "$OUT"
echo "Wrote $OUT"
