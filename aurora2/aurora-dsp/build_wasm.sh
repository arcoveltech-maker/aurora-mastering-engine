#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${SCRIPT_DIR}/../frontend/public/wasm"

mkdir -p "$OUT_DIR"

if ! command -v emcc &>/dev/null; then
  echo "Error: Emscripten (emcc) not found. Source emsdk_env.sh first."
  exit 1
fi

cmake -S "$SCRIPT_DIR" -B "$SCRIPT_DIR/build-wasm" \
  -DCMAKE_TOOLCHAIN_FILE="$EMSDK/upstream/emscripten/cmake/Modules/Platform/Emscripten.cmake" \
  -DAURORA_BUILD_WASM=ON \
  -DAURORA_BUILD_TESTS=OFF \
  -DCMAKE_BUILD_TYPE=Release

cmake --build "$SCRIPT_DIR/build-wasm" --config Release -- -j"$(nproc 2>/dev/null || echo 4)"

cp "$SCRIPT_DIR/build-wasm/aurora_dsp.js"   "$OUT_DIR/"
cp "$SCRIPT_DIR/build-wasm/aurora_dsp.wasm" "$OUT_DIR/"

echo "WASM build complete -> $OUT_DIR"
