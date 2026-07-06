#!/usr/bin/env bash
set -euo pipefail

FRONTEND_URL="${FRONTEND_URL:-https://ai-article-saas.pages.dev}"
BACKEND_URL="${BACKEND_URL:-https://ai-article-saas.onrender.com}"

check_status() {
  local label="$1"
  local url="$2"
  local min_ok="${3:-200}"
  local status
  status="$(curl -sS -o /dev/null -w "%{http_code}" "$url")"
  echo "$label:$status $url"
  if [[ "$status" -lt "$min_ok" || "$status" -ge 500 ]]; then
    echo "[fail] $label returned HTTP $status"
    exit 1
  fi
}

echo "[check] frontend $FRONTEND_URL"
check_status "frontend" "$FRONTEND_URL" 200

echo "[check] frontend api proxy"
check_status "frontend-api-knowledge" "$FRONTEND_URL/api/knowledge-files" 200

echo "[check] backend health"
check_status "backend-health" "$BACKEND_URL/healthz" 200

echo "[check] backend readiness"
check_status "backend-ready" "$BACKEND_URL/readyz" 200

health_json="$(curl -sS "$BACKEND_URL/healthz")"
python3 - "$health_json" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
if not payload.get("persistent_storage_enabled"):
    print("[warn] backend persistent_storage_enabled=false; Render disk/env is not protecting uploaded knowledge files")
else:
    print("[ok] backend persistent storage enabled")

if not payload.get("auth_enabled"):
    print("[warn] backend auth_enabled=false; production users will share the local fallback account")
else:
    print("[ok] backend auth enabled")

db_init = payload.get("database_init") or {}
if db_init.get("state") != "ready":
    print(f"[fail] database_init state is {db_init.get('state')}")
    raise SystemExit(1)
PY
