#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -x "${ROOT_DIR}/.venv/bin/pytest" ]]; then
  exec "${ROOT_DIR}/.venv/bin/pytest" "${ROOT_DIR}/tests" -q
fi

exec pytest "${ROOT_DIR}/tests" -q
