#!/usr/bin/env bash
# Make a fresh cloud container able to run this project's tests and tools.
#
# Without this, every new session on claude.ai/code starts with none of the
# Python dependencies, and the first command that touches them fails. Locally
# this never happens — backend/run.sh builds a venv and the build machine keeps
# it — so the hook is remote-only and leaves a developer's own machine alone.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "${CLAUDE_PROJECT_DIR:-$(dirname "$0")/../..}"

# backend: server + pytest. tools: the art pipeline (numpy, Pillow, httpx).
# Both are installed into the container's own Python rather than a venv — the
# container is single-purpose and throwaway, and a venv here would only need
# activating again in every shell the session opens.
pip install --quiet --disable-pip-version-check --root-user-action=ignore \
    --timeout 120 --retries 5 \
    -r backend/requirements-dev.txt \
    -r tools/requirements.txt

echo "deps ready: backend (+pytest) and tools"
