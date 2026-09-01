#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

export SHM_EM_DATABASE=${SHM_EM_DATABASE:-shm_em_reproduce_compose}
export SHM_EM_MYSQL_USER=${SHM_EM_MYSQL_USER:-shm_em_reproduce}
export SHM_EM_MYSQL_ROOT_PASSWORD=${SHM_EM_MYSQL_ROOT_PASSWORD:-$(python3 -c 'import secrets; print(secrets.token_hex(24))')}
export SHM_EM_MYSQL_PASSWORD=${SHM_EM_MYSQL_PASSWORD:-$(python3 -c 'import secrets; print(secrets.token_hex(24))')}
export SHM_EM_BACKEND_PORT=${SHM_EM_BACKEND_PORT:-5101}
export SHM_EM_FRONTEND_PORT=${SHM_EM_FRONTEND_PORT:-5173}
export SHM_EM_PROJECT_CODE=${SHM_EM_PROJECT_CODE:-SHM_EM_PUBLIC_SAMPLE}

if [[ ! "$SHM_EM_DATABASE" =~ ^shm_em_reproduce_[A-Za-z0-9_]+$ ]]; then
  echo "Compose reproduction requires an isolated shm_em_reproduce_* database." >&2
  exit 2
fi

cleanup() {
  if [[ "${SHM_EM_KEEP_COMPOSE:-0}" != "1" ]]; then
    docker compose --file compose.yaml down --volumes --remove-orphans >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

docker compose --file compose.yaml down --volumes --remove-orphans
docker compose --file compose.yaml build
docker compose --file compose.yaml up --detach

deadline=$((SECONDS + 300))
until curl --fail --silent "http://127.0.0.1:${SHM_EM_BACKEND_PORT}/api/em/projects/1" >/dev/null; do
  if (( SECONDS >= deadline )); then
    docker compose --file compose.yaml ps
    docker compose --file compose.yaml logs --no-color --tail=200
    echo "Backend readiness deadline exceeded." >&2
    exit 3
  fi
  sleep 2
done

set +e
python3 tools/revision/validate_compose_reference.py \
  --base-url "http://127.0.0.1:${SHM_EM_BACKEND_PORT}"
reference_status=$?
python3 tools/revision/build_cross_platform_comparison.py
comparison_status=$?
set -e

if (( reference_status != 0 || comparison_status != 0 )); then
  echo "Phase 2C Docker/Linux validation stopped; inspect artifacts/revision/portability/." >&2
  exit 4
fi

echo "Phase 2C Docker/Linux reference reproduction passed exactly."
