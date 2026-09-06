#!/usr/bin/env bash
# Compatibility: install-hooks.sh <code-repo> [--wiki PATH]
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [[ $# -eq 0 || "$1" == "--help" || "$1" == "-h" ]]; then
	exec "${PYTHON:-python3}" "$SCRIPT_DIR/wiki.py" hooks --help
fi
REPO="$1"
shift
exec "${PYTHON:-python3}" "$SCRIPT_DIR/wiki.py" hooks --repo "$REPO" "$@"
