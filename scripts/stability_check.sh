#!/usr/bin/env bash
set -euo pipefail

echo "[check] frontend http://127.0.0.1:3001"
curl -sS -o /dev/null -w "frontend:%{http_code}\n" http://127.0.0.1:3001

echo "[check] backend docs http://127.0.0.1:8001/docs"
curl -sS -o /dev/null -w "backend:%{http_code}\n" http://127.0.0.1:8001/docs
