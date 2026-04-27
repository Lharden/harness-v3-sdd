#!/usr/bin/env bash
# Context7 proactive trigger wrapper (versionado no Harness v3 SDD).
# Le JSON do UserPromptSubmit via stdin e delega para Python.
set -uo pipefail

HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="${HOOK_DIR}/context7-trigger.py"

if [[ ! -f "${PY_SCRIPT}" ]]; then
  exit 0
fi

if command -v python >/dev/null 2>&1; then
  PYTHON=python
elif command -v py >/dev/null 2>&1; then
  PYTHON="py -3"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
else
  exit 0
fi

exec ${PYTHON} "${PY_SCRIPT}"
