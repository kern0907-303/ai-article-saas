#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[clean] remove AppleDouble files (._*)"
find "$ROOT_DIR" \
  -path "$ROOT_DIR/backend/.venv" -prune -o \
  -name '._*' -type f -delete || true

echo "[clean] remove frontend cache (.next)"
rm -rf "$ROOT_DIR/frontend/.next"

echo "[clean] done"
