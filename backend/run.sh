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
exec uvicorn app.main:app --reload --port 8000
