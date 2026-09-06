#!/usr/bin/env bash
# Optional cloud notification, not a tracked-path diff.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "${PYTHON:-python3}" "$SCRIPT_DIR/cloud_signal.py"
