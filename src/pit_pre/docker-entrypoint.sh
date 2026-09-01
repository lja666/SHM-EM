#!/usr/bin/env sh
set -eu

: "${DB_HOST:?DB_HOST is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"
: "${DB_NAME:?DB_NAME is required}"

export PIT_PRE_CONFIG_PATH="${PIT_PRE_CONFIG_PATH:-/tmp/pit-pre-config.json}"
python - <<'PY'
import json
import os
from pathlib import Path

config = {
    "database": {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ.get("DB_PORT", "3306")),
        "user": os.environ["DB_USER"],
        "password": os.environ["DB_PASSWORD"],
        "database": os.environ["DB_NAME"],
        "charset": "utf8mb4",
    },
    "working_directory": "/app",
}
Path(os.environ["PIT_PRE_CONFIG_PATH"]).write_text(
    json.dumps(config, separators=(",", ":")), encoding="utf-8"
)
PY

exec python -m pit_pre \
  --config "$PIT_PRE_CONFIG_PATH" \
  --project-code "${SHM_EM_PROJECT_CODE:-SHM_EM_PUBLIC_SAMPLE}" \
  "$@"
