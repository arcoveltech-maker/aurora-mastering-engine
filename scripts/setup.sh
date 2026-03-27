#!/usr/bin/env bash
# Aurora dev setup
set -euo pipefail
echo "Aurora setup: create venv, install deps, create frontend node_modules..."
cd "$(dirname "$0")/.."
python3 -m venv backend/.venv 2>/dev/null || true
"$PWD/backend/.venv/bin/pip" install -r backend/requirements.txt 2>/dev/null || true
cd frontend && npm install
echo "Done."
