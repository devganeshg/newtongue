@echo off
rem Windows launcher: double-click to set up (first run) and open VoxDub.
setlocal EnableExtensions
cd /d "%~dp0"
chcp 65001 >nul 2>nul

echo === VoxDub ===
echo.

rem 0. Warn early about long install paths: Windows' 260-char path limit can
rem    make dependency installation fail deep inside nested Python packages.
set "HEREPATH=%cd%"
if not "%HEREPATH:~230,1%"=="" (
    echo WARNING: this folder's path is long ^(%HEREPATH%^).
    echo Windows has a 260-character path limit that can make setup fail below.
    echo If it does, move this folder somewhere short like C:\VoxDub and retry.
    echo.
)

rem 1. Ensure uv (Python package manager) is installed
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
    echo Installing uv, one-time setup...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12; irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
where uv >nul 2>nul
if errorlevel 1 (
    echo PowerShell install didn't work; trying winget instead...
    where winget >nul 2>nul
    if not errorlevel 1 (
        winget install --id=astral-sh.uv -e --silent --accept-source-agreements --accept-package-agreements
        set "PATH=%USERPROFILE%\.local\bin;%PATH%"
    )
)
where uv >nul 2>nul
if errorlevel 1 (
    echo.
    echo ERROR: could not install uv automatically.
    echo   This usually means a work/school PC policy is blocking PowerShell
    echo   script downloads, or there is no internet connection.
    echo   Install uv manually from https://docs.astral.sh/uv/getting-started/installation/
    echo   then double-click this file again.
    pause
    exit /b 1
)

rem 2. Install/update Python and dependencies (fast no-op after first run)
echo Checking dependencies... ^(first run downloads Python + packages, a few minutes^)
uv sync
if errorlevel 1 (
    echo.
    echo ERROR: dependency installation failed. Common causes:
    echo   - No internet connection, or a firewall/proxy blocking pypi.org
    echo   - The path warning above ^(move this folder somewhere short and retry^)
    echo   - A leftover broken ".venv" folder from an earlier failed attempt
    echo     ^(delete the ".venv" folder next to this script, then re-run it^)
    pause
    exit /b 1
)

rem 3. Launch the app; it opens in your browser automatically
echo Starting... the app will open in your browser. Keep this window open.
uv run python app.py
if errorlevel 1 (
    echo.
    echo VoxDub exited with an error ^(see above^). If it mentions ffmpeg,
    echo make sure you have an internet connection so it can download ffmpeg
    echo automatically on first use.
)
pause
