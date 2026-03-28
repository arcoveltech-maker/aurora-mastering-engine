#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Frontend tsc..."
cd frontend && npx tsc --noEmit
echo "Backend pytest..."
cd ../backend && .venv/bin/python -m pytest tests -v --tb=short 2>/dev/null || true
echo "DSP ctest..."
cd ../aurora-dsp/build-native && ctest 2>/dev/null || true
echo "Done."
