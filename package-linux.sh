#!/bin/sh
set -e
# Package er-save-manager onedir bundle as AppImage using appimagetool

# Get version from pyproject.toml
version=$(grep --max-count=1 '^version\s*=' pyproject.toml | cut -d '"' -f2)
bundle="dist/linux-$version/er-save-manager"

if [ ! -f "$bundle/er-save-manager" ]; then
    echo "Error: $bundle/er-save-manager not found. Run build-linux.sh first."
    exit 1
fi

# Download appimagetool if not present
ait_url=https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
if [ ! -f appimagetool-x86_64.appimage ]; then
    echo "Downloading appimagetool..."
    curl -fL "$ait_url" -o appimagetool-x86_64.appimage
fi

appdir=build/AppDir

echo "Cleaning $appdir..."
rm -rf "$appdir"
mkdir -p "$appdir/usr/bin"
mkdir -p "$appdir/usr/share/applications"
mkdir -p "$appdir/usr/share/icons/hicolor/256x256/apps"

# Copy entire onedir bundle into usr/bin
cp -r "$bundle/"* "$appdir/usr/bin/"
chmod +x "$appdir/usr/bin/er-save-manager"

# Desktop file and icon
cp resources/linux/er-save-manager.desktop "$appdir/usr/share/applications/"
cp resources/icon/icon.png "$appdir/usr/share/icons/hicolor/256x256/apps/er-save-manager.png"

# AppDir root symlinks required by appimagetool
ln -s usr/bin/er-save-manager "$appdir/AppRun"
ln -s usr/share/applications/er-save-manager.desktop "$appdir/er-save-manager.desktop"
ln -s usr/share/icons/hicolor/256x256/apps/er-save-manager.png "$appdir/er-save-manager.png"
ln -s usr/share/icons/hicolor/256x256/apps/er-save-manager.png "$appdir/.DirIcon"

echo "Creating AppImage..."
chmod +x appimagetool-x86_64.appimage
./appimagetool-x86_64.appimage --appimage-extract-and-run "$appdir" "dist/linux-$version/er-save-manager.AppImage"

echo "AppImage created: dist/linux-$version/er-save-manager.AppImage"
