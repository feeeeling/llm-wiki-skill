#!/usr/bin/env bash
# Used by GitHub Actions in the wiki repo. No LLM.
set -euo pipefail

repo_name="${REPO_NAME:-${D_REPO:-}}"
old_rev="${OLD_REV:-${D_OLD:-}}"
new_rev="${NEW_REV:-${D_NEW:-}}"
files="${FILES:-${D_FILES:-}}"

if [[ -z "$repo_name" || -z "$old_rev" || -z "$new_rev" ]]; then
  echo "need repo_name, old_rev, new_rev" >&2
  exit 1
fi

mkdir -p queue/drift
short="$(printf '%s' "$new_rev" | cut -c1-7)"
out="queue/drift/$(date -u +%Y-%m-%d)-${repo_name}-${short}.md"

{
  echo "---"
  echo "status: pending"
  echo "repo: $repo_name"
  echo "old_rev: $old_rev"
  echo "new_rev: $new_rev"
  echo "created: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "pages: []"
  echo "files:"
  if [[ -n "$files" ]]; then
    printf '%s\n' "$files" | while IFS= read -r line; do
      [[ -n "$line" ]] && echo "  - $line"
    done
  else
    echo "  []"
  fi
  echo "---"
  echo
  echo "Opened by GitHub Action. Process with targeted ingest."
} > "$out"

echo "wrote $out"
