#!/usr/bin/env bash
# Start the Voice Companion backend for local development.
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
  echo "⚠️  No .env found. Copy .env.example to .env and add your keys:"
  echo "     cp .env.example .env"
fi

echo "▶  http://localhost:8000  (open this in your browser to talk)"

# Show the address a phone on the same Wi-Fi should use.
LAN_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
[ -n "$LAN_IP" ] && echo "▶  http://$LAN_IP:8000   ← use this one in the app on a real iPhone"

# --host 0.0.0.0, not the 127.0.0.1 default. The default accepts connections
# from this Mac only, which is fine for the simulator and means a real iPhone
# can never reach it however correct the address in the app looks. This is a
# local development server on your own network; don't run it on a public one.
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
