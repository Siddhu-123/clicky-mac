#!/bin/bash
# Clicky for macOS Launcher
# Runs as native Clicky.app so permissions are scoped to com.clicky.mac

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

# Ensure Clicky.app bundle is built
APP_BIN="$DIR/dist/Clicky.app/Contents/MacOS/Clicky"
if [ ! -f "$APP_BIN" ]; then
    echo "Building Clicky.app bundle for scoped permissions..."
    python3 build_app.py
fi

if [ "$1" == "--open" ]; then
    echo "Opening Clicky.app via macOS Finder..."
    open "$DIR/dist/Clicky.app"
elif [ "$1" == "--raw" ]; then
    shift
    echo "Starting Clicky (Raw Python mode)..."
    python3 main.py "$@"
else
    echo "Starting Clicky as native macOS App (TCC: com.clicky.mac)..."
    "$APP_BIN" "$@"
fi
