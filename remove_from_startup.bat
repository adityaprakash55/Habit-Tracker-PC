@echo off
setlocal
title Remove VoltHabit Widget from Windows Startup

echo ========================================================
echo     VoltHabit - Remove from Windows Startup
echo ========================================================
echo.

set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_DIR%\VoltHabitWidget.lnk"

if exist "%SHORTCUT_PATH%" (
    del /f /q "%SHORTCUT_PATH%"
    echo [OK] Removed shortcut: %SHORTCUT_PATH%
    echo VoltHabit will no longer start automatically on Windows boot.
) else (
    echo [INFO] VoltHabit is not currently in Windows Startup folder.
)

echo.
echo Press any key to exit...
pause >nul
