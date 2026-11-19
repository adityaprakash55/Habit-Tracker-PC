@echo off
setlocal EnableDelayedExpansion
title Add VoltHabit Widget to Windows Startup

echo ========================================================
echo       VoltHabit - Add to Windows Startup
echo ========================================================
echo.

set "SCRIPT_DIR=%~dp0"
set "MAIN_PY=%SCRIPT_DIR%main.py"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_DIR%\VoltHabitWidget.lnk"

:: Check for pythonw.exe (windowless python)
set "PYTHONW_EXE=%LOCALAPPDATA%\Programs\Python\Python311\pythonw.exe"

if not exist "!PYTHONW_EXE!" (
    for /f "tokens=*" %%i in ('where pythonw 2^>nul') do (
        set "PYTHONW_EXE=%%i"
    )
)

if not exist "!PYTHONW_EXE!" (
    for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python*") do (
        if exist "%%d\pythonw.exe" set "PYTHONW_EXE=%%d\pythonw.exe"
    )
)

if not exist "!PYTHONW_EXE!" (
    echo [ERROR] pythonw.exe was not found automatically.
    echo Please ensure Python 3 is installed.
    pause
    exit /b 1
)

echo [OK] Using Pythonw: !PYTHONW_EXE!
echo [OK] Target Script: !MAIN_PY!
echo [OK] Startup Folder: !STARTUP_DIR!
echo.

:: Create shortcut using PowerShell
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut('!SHORTCUT_PATH!'); " ^
    "$s.TargetPath = '!PYTHONW_EXE!'; " ^
    "$s.Arguments = '\"!MAIN_PY!\"'; " ^
    "$s.WorkingDirectory = '!SCRIPT_DIR!'; " ^
    "$s.Description = 'VoltHabit Desktop Floating Widget'; " ^
    "$s.Save()"

if %ERRORLEVEL% EQU 0 (
    echo ========================================================
    echo  SUCCESS: VoltHabit Widget added to Windows Startup!
    echo ========================================================
    echo The widget will now automatically launch silently on boot.
    echo Shortcut: !SHORTCUT_PATH!
) else (
    echo [ERROR] Failed to create startup shortcut.
)

echo.
echo Press any key to exit...
pause >nul
