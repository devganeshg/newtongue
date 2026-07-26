#!/bin/bash
# Linux launcher: run to set up (first run) and open Newtongue.
#   chmod +x start-newtongue.sh && ./start-newtongue.sh
cd "$(dirname "$0")"

echo "=== Newtongue ==="
echo

# 1. Ensure uv (Python package manager) is installed
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv (one-time setup)..."
    if ! curl -LsSf https://astral.sh/uv/install.sh | sh; then
        echo
        echo "ERROR: could not install uv automatically (no internet, or curl/sh blocked)."
        echo "Install it manually: https://docs.astral.sh/uv/getting-started/installation/"
        echo "then re-run this script."
        exit 1
    fi
    export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v uv >/dev/null 2>&1; then
    echo
    echo "ERROR: uv installed but isn't on PATH. Open a new terminal (so it picks up"
    echo "the updated PATH) and re-run this script."
    exit 1
fi

# 2. Install/update Python and dependencies (fast no-op after first run)
echo "Checking dependencies... (first run downloads Python + packages, a few minutes)"
if ! uv sync; then
    echo
    echo "ERROR: dependency installation failed. Common causes:"
    echo "  - No internet connection, or a firewall/proxy blocking pypi.org"
    echo "  - Missing build tools for a package with no prebuilt wheel for your"
    echo "    distro/architecture (try: sudo apt install build-essential, or the"
    echo "    equivalent for your package manager)"
    echo "  - A leftover broken .venv folder from an earlier failed attempt"
    echo "    (delete the .venv folder next to this script, then re-run it)"
    exit 1
fi

# 3. Launch the app; it opens in your browser automatically
echo "Starting... the app will open in your browser. Keep this terminal open."
if ! uv run python app.py; then
    echo
    echo "Newtongue exited with an error (see above). If it mentions ffmpeg, make sure"
    echo "you have an internet connection so it can download ffmpeg automatically"
    echo "on first use, or install it yourself: sudo apt install ffmpeg"
    exit 1
fi
