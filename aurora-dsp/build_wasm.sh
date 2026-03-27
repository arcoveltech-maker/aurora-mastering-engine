#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p build-wasm
cd build-wasm
emcmake cmake .. -DAURORA_BUILD_WASM=ON -DAURORA_BUILD_TESTS=OFF
emmake make
if [ -f aurora_dsp.js ]; then
  sha256sum aurora_dsp.wasm > aurora_dsp.wasm.sha256 2>/dev/null || true
  mkdir -p ../frontend/public/wasm 2>/dev/null || true
  cp -f aurora_dsp.wasm aurora_dsp.js ../frontend/public/wasm/ 2>/dev/null || true
fi
echo "WASM build done."
