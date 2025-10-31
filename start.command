#!/usr/bin/env bash
set -euo pipefail

# --- locate repo root (folder of this script) ---
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"

echo "Starting CreditRater (auto-clean backend)…"

# --- kill any process on port 5051 (macOS) ---
if lsof -Pi :5051 -sTCP:LISTEN -t >/dev/null ; then
  PID=$(lsof -Pi :5051 -sTCP:LISTEN -t | tr '\n' ' ')
  echo "Killing existing backend on port 5051 (PID: $PID)…"
  kill -9 $PID || true
fi

# --- set up venv & deps ---
cd "$HERE/backend"
if [ ! -d ".venv" ]; then
  echo "Creating Python venv…"
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "Installing/validating Python dependencies…"
pip install --upgrade pip >/dev/null
pip install -r requirements.txt >/dev/null

# --- run backend ---
echo "Launching backend on http://127.0.0.1:5051 …"
# Run in background so the script can open the browser
uvicorn server:app --host 127.0.0.1 --port 5051 --reload > "$HERE/backend/.server.log" 2>&1 &

# Give it a moment to boot
sleep 1

# --- open browser ---
open "http://127.0.0.1:5051/app"

echo "Backend logs at backend/.server.log"
echo "Press Ctrl+C to stop (if you launched this from a terminal)."
