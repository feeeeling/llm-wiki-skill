#!/usr/bin/env bash
# Compatibility: --report maps to status; all other calls map to check.
# --old is intentionally unsupported: the reviewed baseline is compiled_rev.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODE=check
ARGS=()
for arg in "$@"; do
	if [[ "$arg" == "--report" ]]; then
		MODE=status
	else
		ARGS+=("$arg")
	fi
done
exec "${PYTHON:-python3}" "$SCRIPT_DIR/wiki.py" "$MODE" ${ARGS[@]+"${ARGS[@]}"}
