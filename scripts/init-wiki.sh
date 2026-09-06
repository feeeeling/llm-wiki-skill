#!/usr/bin/env bash
# Compatibility entry point; the portable CLI is wiki.py.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "${PYTHON:-python3}" "$SCRIPT_DIR/wiki.py" init "$@"
