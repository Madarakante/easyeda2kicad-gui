#!/usr/bin/env bash
# Build the EasyEDA2KiCad desktop app on Linux or macOS (one-folder, windowed).
# Output: dist/EasyEDA2KiCad/EasyEDA2KiCad
#
# PyInstaller cannot cross-compile — run this ON the OS you want to build for.
set -e
cd "$(dirname "$0")"

echo "Cleaning previous build..."
rm -rf build dist

# Regenerate icons if Pillow is available (optional).
if python3 -c "import PIL" 2>/dev/null; then
  python3 make_icon.py || true
fi

echo "Building..."
python3 -m PyInstaller easyeda2kicad_gui.spec --noconfirm

echo
echo "Done. App is at: dist/EasyEDA2KiCad/EasyEDA2KiCad"
echo "Distribute the whole 'dist/EasyEDA2KiCad' folder."
