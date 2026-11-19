@echo off
setlocal EnableDelayedExpansion

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
    start pythonw "%~dp0main.py"
) else (
    start "" "!PYTHONW_EXE!" "%~dp0main.py"
)
