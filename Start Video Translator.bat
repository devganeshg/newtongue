@echo off
rem Windows launcher: double-click to set up (first run) and open Video Voice Translator.
setlocal
cd /d "%~dp0"

echo === Video Voice Translator ===

rem 1. Ensure uv (Python package manager) is installed
set "PATH=%USERPROFILE%\.local\bin;%PATH%"
where uv >nul 2>nul
if errorlevel 1 (
    echo Installing uv, one-time setup...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)
where uv >nul 2>nul
if errorlevel 1 (
    echo ERROR: could not install uv. Install it from https://docs.astral.sh/uv/ and re-run.
    pause
    exit /b 1
)

rem 2. Install/update Python and dependencies (fast no-op after first run)
echo Checking dependencies...
uv sync
if errorlevel 1 (
    echo ERROR: dependency installation failed. Check your internet connection.
    pause
    exit /b 1
)

rem 3. Launch the app; it opens in your browser automatically
echo Starting... the app will open in your browser. Keep this window open.
uv run python app.py
pause
