#!/usr/bin/env bash
# Scaffold a wiki git repo from this skill's templates.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: init-wiki.sh <target-dir> [--force]

Creates a self-contained wiki repo (AGENTS.md, wiki/, raw/, sources/,
queue/drift/, scripts/). Copies check-drift.sh and install-hooks.sh into
the wiki so git hooks do not depend on the skill install path.
EOF
}

TARGET="${1:-}"
FORCE=0
shift || true
while [[ $# -gt 0 ]]; do
  case "$1" in
    --force) FORCE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

[[ -n "$TARGET" ]] || { usage >&2; exit 1; }

die() { echo "init-wiki: $*" >&2; exit 1; }

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
[[ -f "$SKILL_DIR/SKILL.md" ]] || die "run this from the skill scripts/ directory"

mkdir -p "$TARGET"
TARGET="$(cd "$TARGET" && pwd)"

if [[ -f "$TARGET/AGENTS.md" && $FORCE -ne 1 ]]; then
  die "already initialized: $TARGET (pass --force to overwrite templates)"
fi

mkdir -p "$TARGET/raw/sources" "$TARGET/raw/assets" \
  "$TARGET/wiki" "$TARGET/sources" "$TARGET/queue/drift" "$TARGET/scripts"

cp "$SKILL_DIR/templates/AGENTS.md" "$TARGET/AGENTS.md"
cp "$SKILL_DIR/scripts/check-drift.sh" "$TARGET/scripts/check-drift.sh"
cp "$SKILL_DIR/scripts/install-hooks.sh" "$TARGET/scripts/install-hooks.sh"
cp "$SKILL_DIR/scripts/gh-write-drift.sh" "$TARGET/scripts/gh-write-drift.sh"
chmod +x "$TARGET/scripts/"*.sh

cp "$SKILL_DIR/templates/source.yaml" "$TARGET/sources/example.yaml.disabled"
cp "$SKILL_DIR/templates/drift-ticket.md" "$TARGET/queue/drift/README.md"

if [[ -d "$SKILL_DIR/templates/github" ]]; then
  mkdir -p "$TARGET/.github/workflows"
  cp "$SKILL_DIR/templates/github/"*.yml "$TARGET/.github/workflows/" 2>/dev/null || true
  for f in "$TARGET/.github/workflows/"*.yml; do
    [[ -f "$f" ]] || continue
    mv "$f" "${f}.example"
  done
fi

if [[ -d "$SKILL_DIR/templates/obsidian" ]]; then
  mkdir -p "$TARGET/.obsidian"
  cp "$SKILL_DIR/templates/obsidian/"*.json "$TARGET/.obsidian/"
fi

if [[ ! -f "$TARGET/wiki/overview.md" ]]; then
  cat > "$TARGET/wiki/overview.md" <<'EOF'
# Overview

Home page for Obsidian. The agent keeps this current.

- Catalog: [[index]]
- Timeline: [[log]]
- Concepts, entities, and syntheses appear here as they are ingested.

Open **Graph view** (Ctrl/Cmd+G) to see links.
EOF
fi

if [[ ! -f "$TARGET/wiki/index.md" ]]; then
  cat > "$TARGET/wiki/index.md" <<'EOF'
# Index

Catalog of wiki pages. The agent updates this on every ingest.

Start at [[overview]].

| Page | Summary | Updated |
|------|---------|---------|
| [[overview]] | Home | |
| [[log]] | Operation log | |
EOF
fi

if [[ ! -f "$TARGET/wiki/log.md" ]]; then
  cat > "$TARGET/wiki/log.md" <<EOF
# Log

Append-only. Prefix every entry with \`## [YYYY-MM-DD] kind | title\`.

## [$(date +%Y-%m-%d)] init | wiki created
EOF
fi

if [[ ! -f "$TARGET/README.md" ]]; then
  cat > "$TARGET/README.md" <<EOF
# Wiki

LLM-maintained knowledge base. Schema: \`AGENTS.md\`.

\`\`\`bash
bash scripts/check-drift.sh --report
bash scripts/install-hooks.sh /path/to/code-repo
\`\`\`

Enable a code source: copy \`sources/example.yaml.disabled\` to \`sources/<name>.yaml\`.
EOF
fi

if [[ ! -f "$TARGET/.gitignore" ]]; then
  cat > "$TARGET/.gitignore" <<'EOF'
.DS_Store
*.swp
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/cache
.trash/
EOF
fi

if [[ ! -d "$TARGET/.git" ]]; then
  git -C "$TARGET" init -b main >/dev/null
  git -C "$TARGET" add .
  git -C "$TARGET" commit -m "init llm-wiki" >/dev/null
fi

echo "wiki ready: $TARGET"
echo "next: git remote add origin <github>; register sources/*.yaml; install-hooks.sh"
