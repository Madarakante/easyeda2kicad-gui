@echo off
REM Build the EasyEDA2KiCad desktop app (one-folder, windowed).
REM Output: dist\EasyEDA2KiCad\EasyEDA2KiCad.exe
setlocal
cd /d "%~dp0"

echo Cleaning previous build...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Building...
python -m PyInstaller easyeda2kicad_gui.spec --noconfirm
if errorlevel 1 (
    echo.
    echo BUILD FAILED.
    pause
    exit /b 1
)

echo.
echo Done. App is at:  dist\EasyEDA2KiCad\EasyEDA2KiCad.exe
echo Distribute the whole "dist\EasyEDA2KiCad" folder.
pause
