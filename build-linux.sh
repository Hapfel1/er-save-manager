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

# Ship every non-Python file inside the package at its package-relative
# path. Directories cannot be added whole: data/ and fixes/ also hold
# .py modules, which must not be copied as source.
data_flags=""
for f in $(find src/er_save_manager -type f ! -name '*.py' ! -name '*.pyc' ! -path '*/__pycache__/*' | sort); do
    dest=$(dirname "${f#src/}")
    data_flags="$data_flags --add-data $f:$dest"
done

# Windows-only files in resources/ are left out: fonts.py loads
# resources/fonts/windows only on Windows, and icon.ico is the exe icon
# (Tk on X11 cannot read it; gui.py falls back to icon.png).
for f in $(find resources/fonts -maxdepth 1 -type f; find resources/icon -type f ! -name icon.ico); do
    data_flags="$data_flags --add-data $f:$(dirname "$f")"
done

# The excluded stdlib packages (unittest, pydoc, asyncio, ...) are reachable
# only through optional imports in dependencies; nothing imports them at runtime.
# readline (GPL-3.0) is pulled in only by sqlite3.__main__ -> code, the
# `python -m sqlite3` shell, which the app never runs.
echo "Building GUI with PyInstaller..."
# shellcheck disable=SC2086
pyinstaller --clean --noconfirm \
    --name er-save-manager \
    --onedir \
    --icon resources/icon/icon.png \
    --copy-metadata er-save-manager \
    --copy-metadata customtkinterthemes \
    --add-data src/resources:resources \
    --collect-data customtkinterthemes \
    --hidden-import customtkinterthemes \
    --hidden-import PIL._tkinter_finder \
    --hidden-import PIL.ImageTk \
    --hidden-import PIL._imagingtk \
    --collect-submodules er_save_manager \
    --exclude-module tests \
    --exclude-module PIL._avif \
    --exclude-module unittest \
    --exclude-module pydoc \
    --exclude-module doctest \
    --exclude-module pdb \
    --exclude-module setuptools \
    --exclude-module pkg_resources \
    --exclude-module multiprocessing \
    --exclude-module asyncio \
    --exclude-module xmlrpc \
    --exclude-module readline \
    $data_flags \
    --optimize 2 \
    --strip \
    --distpath "dist/linux-$version" \
    run_gui.py

# Remove bundled OpenSSL so system libs are used at runtime
echo "Removing bundled OpenSSL..."
find "dist/linux-$version/er-save-manager" -name "libssl.so*" -delete
find "dist/linux-$version/er-save-manager" -name "libcrypto.so*" -delete

echo "Writing third-party notices..."
python scripts/third_party_notices.py \
    "dist/linux-$version/er-save-manager/THIRD_PARTY_NOTICES.txt" \
    --bundle "dist/linux-$version/er-save-manager"

echo "Build complete: dist/linux-$version/er-save-manager/"