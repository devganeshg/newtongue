#!/bin/bash
# Linux launcher: run to set up (first run) and open Video Voice Translator.
#   chmod +x start-video-translator.sh && ./start-video-translator.sh
set -e
cd "$(dirname "$0")"

echo "=== Video Voice Translator ==="

# 1. Ensure uv (Python package manager) is installed
export PATH="$HOME/.local/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv (one-time setup)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# 2. Install/update Python and dependencies (fast no-op after first run)
echo "Checking dependencies..."
uv sync

# 3. Launch the app; it opens in your browser automatically
echo "Starting... the app will open in your browser. Keep this terminal open."
exec uv run python app.py
