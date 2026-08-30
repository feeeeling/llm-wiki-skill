#!/usr/bin/env bash
# Install post-merge / post-rewrite / post-checkout hooks into a code repo.
# Hooks are NOT versioned by git; run once per machine per code repo.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install-hooks.sh <code-repo> [--wiki DIR]

Writes git hooks that call <wiki>/scripts/check-drift.sh --repo <code-repo>.
Does not replace existing hooks; it appends a guarded block if missing.
EOF
}

CODE="${1:-}"
WIKI=""
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --wiki) WIKI="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

[[ -n "$CODE" ]] || { usage >&2; exit 1; }

die() { echo "install-hooks: $*" >&2; exit 1; }

is_wiki_root() { [[ -f "$1/AGENTS.md" && -d "$1/sources" ]]; }

realpath_portable() {
  if command -v realpath >/dev/null 2>&1; then
    realpath "$1"
  else
    python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
  fi
}

discover_wiki() {
  if [[ -n "${LLM_WIKI_ROOT:-}" ]] && is_wiki_root "$LLM_WIKI_ROOT"; then
    printf '%s\n' "$LLM_WIKI_ROOT"
    return
  fi
  local dir
  dir="$(cd "$(dirname "$0")/.." && pwd)"
  if is_wiki_root "$dir"; then
    printf '%s\n' "$dir"
    return
  fi
  dir="$(pwd)"
  while [[ "$dir" != "/" ]]; do
    if is_wiki_root "$dir"; then
      printf '%s\n' "$dir"
      return
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}

if [[ -z "$WIKI" ]]; then
  WIKI="$(discover_wiki)" || die "pass --wiki DIR"
fi
WIKI="$(realpath_portable "$WIKI")"
CODE="$(realpath_portable "$CODE")"
is_wiki_root "$WIKI" || die "not a wiki root: $WIKI"
git -C "$CODE" rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not a git repo: $CODE"

HOOKS="$(git -C "$CODE" rev-parse --git-path hooks)"
SCRIPT="$WIKI/scripts/check-drift.sh"
[[ -f "$SCRIPT" ]] || die "missing $SCRIPT (run init-wiki.sh so the wiki has scripts/)"
chmod +x "$SCRIPT" 2>/dev/null || true

MARKER="# llm-wiki-drift"

write_hook() {
  local name="$1"
  local extra="$2"
  local path="$HOOKS/$name"
  mkdir -p "$HOOKS"
  if [[ -f "$path" ]] && grep -q "$MARKER" "$path"; then
    echo "already installed: $path"
    return
  fi
  if [[ ! -f "$path" ]]; then
    printf '%s\n' "#!/bin/sh" > "$path"
    chmod +x "$path"
  fi
  cat >> "$path" <<EOF

$MARKER
# Auto-appended by llm-wiki install-hooks.sh. Safe to delete this block.
$extra
WIKI_ROOT="$WIKI"
DRIFT="\$WIKI_ROOT/scripts/check-drift.sh"
if [ -x "\$DRIFT" ]; then
  if [ -n "\${old:-}" ] && [ -n "\${new:-}" ]; then
    "\$DRIFT" --wiki "\$WIKI_ROOT" --repo "$CODE" --old "\$old" --new "\$new" --mark-stale >/dev/null 2>&1 || true
  else
    "\$DRIFT" --wiki "\$WIKI_ROOT" --repo "$CODE" --mark-stale >/dev/null 2>&1 || true
  fi
fi
# end llm-wiki-drift
EOF
  chmod +x "$path"
  echo "installed $path"
}

# post-merge: ORIG_HEAD is previous tip when git sets it
write_hook post-merge "old=\${ORIG_HEAD:-}; new=HEAD"

# rebase / pull --rebase
write_hook post-rewrite "old=\${ORIG_HEAD:-}; new=HEAD"

# branch checkout only (3rd arg = 1)
write_hook post-checkout "$(cat <<'EOS'
if [ "${3:-0}" != "1" ]; then
  exit 0
fi
old=${1:-}
new=${2:-}
EOS
)"

printf '%s\n' "$WIKI" > "$HOOKS/llm-wiki-root"
echo "hooks installed for $CODE → $WIKI"
echo "remember: .git/hooks is local; rerun this script on each machine."
