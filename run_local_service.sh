#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".env" ]; then
  set -o allexport
  source ".env"
  set +o allexport
fi

ENGINE_ARGS=(
  --mode "${AFKO_PIPELINE_MODE:-local}"
  --local-root "${AFKO_LOCAL_REPO_ROOT:-.}"
  --query-limit "${AFKO_QUERY_LIMIT:-2}"
  --start-runtime
)

if [[ "${AFKO_START_AETHORFORGE:-false}" == "1" || "${AFKO_START_AETHORFORGE:-false}" == "true" || "${AFKO_START_AETHORFORGE:-false}" == "yes" ]]; then
  ENGINE_ARGS+=(--start-aethorforge)
fi

python3 afko_engine.py "${ENGINE_ARGS[@]}"
