#!/usr/bin/env bash
# Build a x86_64 AppImage. Run on Linux (Ubuntu 22.04 is a good glibc baseline).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ARCH="${ARCH:-x86_64}"
APP_NAME="Wallpane"
VERSION="$(python3 -c "from pathlib import Path; import re; t=Path('pyproject.toml').read_text(); print(re.search(r'^version = \"([^\"]+)\"', t, re.M).group(1))")"

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

rm -rf AppDir
mkdir -p AppDir/usr/bin AppDir/usr/share/applications AppDir/usr/share/icons/hicolor/256x256/apps

cp -a dist/wallpane/. AppDir/usr/bin/
cp packaging/wallpane.desktop AppDir/usr/share/applications/wallpane.desktop
cp packaging/wallpane.png AppDir/usr/share/icons/hicolor/256x256/apps/wallpane.png
cp packaging/wallpane.png AppDir/wallpane.png

# linuxdeploy expects the executable name to match Exec=
if [[ -f AppDir/usr/bin/wallpane ]]; then
  chmod +x AppDir/usr/bin/wallpane
fi

if [[ ! -x linuxdeploy-${ARCH}.AppImage ]]; then
  curl -L -o "linuxdeploy-${ARCH}.AppImage" \
    "https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-${ARCH}.AppImage"
  chmod +x "linuxdeploy-${ARCH}.AppImage"
fi

# Extract to avoid FUSE in CI.
./linuxdeploy-${ARCH}.AppImage --appimage-extract >/dev/null
export LINUXDEPLOY_OUTPUT_VERSION="${VERSION}"
./squashfs-root/AppRun \
  --appdir AppDir \
  --executable AppDir/usr/bin/wallpane \
  --desktop-file AppDir/usr/share/applications/wallpane.desktop \
  --icon-file AppDir/usr/share/icons/hicolor/256x256/apps/wallpane.png \
  --output appimage

mkdir -p dist
mv -f ${APP_NAME}*.AppImage "dist/Wallpane-${VERSION}-${ARCH}.AppImage" 2>/dev/null || \
  mv -f Wallpane*.AppImage "dist/Wallpane-${VERSION}-${ARCH}.AppImage" 2>/dev/null || \
  mv -f wallpane*.AppImage "dist/Wallpane-${VERSION}-${ARCH}.AppImage"

echo "Wrote dist/Wallpane-${VERSION}-${ARCH}.AppImage"
