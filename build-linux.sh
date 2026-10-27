#!/bin/sh
set -e
# Build er-save-manager as a directory bundle for Linux (packaged as AppImage by package-linux.sh)
#
# Usage with uv:
#     uv sync --dev
#     uv run ./build-linux.sh
#
# Usage with pip (activate venv first):
#     pip install -r requirements-dev.txt
#     ./build-linux.sh
# pyinstaller does not cross-compile. Build results will be wrong on other OSes.
if [ "$(uname)" != Linux ]; then
    echo "This script only works on Linux."
    exit 1
fi

# Get version from pyproject.toml
version=$(grep --max-count=1 '^version\s*=' pyproject.toml | cut -d '"' -f2)

# Locate libreadline.so.8 for bundling - path varies by distro
# (Arch: /usr/lib, Ubuntu/Debian: /lib/x86_64-linux-gnu, etc.)
readline_lib=$(ldconfig -p 2>/dev/null | awk '/libreadline\.so\.8/{print $NF; exit}')
if [ -z "$readline_lib" ]; then
    readline_lib=$(find /usr/lib /lib -name "libreadline.so.8" 2>/dev/null | head -1)
fi

readline_flag=""
if [ -n "$readline_lib" ]; then
    echo "Bundling readline: $readline_lib"
    readline_flag="--add-binary ${readline_lib}:."
else
    echo "Warning: libreadline.so.8 not found, skipping bundle"
fi

# Ship every non-Python file inside the package at its package-relative
# path. Directories cannot be added whole: data/ and fixes/ also hold
# .py modules, which must not be copied as source.
data_flags=""
for f in $(find src/er_save_manager -type f ! -name '*.py' ! -name '*.pyc' ! -path '*/__pycache__/*' | sort); do
    dest=$(dirname "${f#src/}")
    data_flags="$data_flags --add-data $f:$dest"
done

echo "Building GUI with PyInstaller..."
# shellcheck disable=SC2086
pyinstaller --clean --noconfirm \
    --name er-save-manager \
    --onedir \
    --icon resources/icon/icon.png \
    --copy-metadata er-save-manager \
    --copy-metadata customtkinterthemes \
    --add-data src/resources:resources \
    --add-data resources/icon:resources/icon \
    --add-data resources/fonts:resources/fonts \
    --collect-data customtkinterthemes \
    --hidden-import customtkinterthemes \
    --hidden-import PIL._tkinter_finder \
    --hidden-import PIL.ImageTk \
    --hidden-import PIL._imagingtk \
    --collect-submodules er_save_manager \
    --exclude-module tests \
    --exclude-module PIL._avif \
    $data_flags \
    $readline_flag \
    --optimize 2 \
    --strip \
    --distpath "dist/linux-$version" \
    run_gui.py

# Remove bundled OpenSSL so system libs are used at runtime
echo "Removing bundled OpenSSL..."
find "dist/linux-$version/er-save-manager" -name "libssl.so*" -delete
find "dist/linux-$version/er-save-manager" -name "libcrypto.so*" -delete

echo "Build complete: dist/linux-$version/er-save-manager/"