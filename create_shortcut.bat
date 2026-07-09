@echo off
REM Create a Desktop shortcut to the built EasyEDA2KiCad app.
setlocal
cd /d "%~dp0"

set "TARGET=%~dp0dist\EasyEDA2KiCad\EasyEDA2KiCad.exe"
set "ICON=%~dp0app.ico"

if not exist "%TARGET%" (
    echo Build the app first: run build.bat
    pause
    exit /b 1
)

powershell -NoProfile -Command ^
  "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\EasyEDA2KiCad.lnk');" ^
  "$s.TargetPath='%TARGET%';" ^
  "$s.WorkingDirectory='%~dp0dist\EasyEDA2KiCad';" ^
  "$s.IconLocation='%ICON%';" ^
  "$s.Description='Import LCSC/EasyEDA parts into KiCad';" ^
  "$s.Save();"

echo Desktop shortcut created: EasyEDA2KiCad.lnk
pause
