#!/usr/bin/env bash
# Mechanical hard gate: open or report drift tickets. Never calls an LLM.
# Bash 3.2 compatible (macOS /bin/bash).
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: check-drift.sh [options]

Compare a registered code repo's compiled_rev to HEAD (or --old/--new),
intersect with track: paths, and write queue/drift/<ticket>.md.

Options:
  --wiki DIR       Wiki root (AGENTS.md + sources/)
  --repo DIR       Code repo to check (default: cwd)
  --old REV        Old commit (default: compiled_rev)
  --new REV        New commit (default: HEAD)
  --report         List pending tickets only; do not write
  --mark-stale     Set status: stale on mapped wiki pages
  --fail-on-drift  Exit 2 when pending tickets exist
  -h, --help

Exit codes: 0 ok, 1 error, 2 pending drift (--fail-on-drift)
EOF
}

WIKI=""
REPO=""
OLD=""
NEW=""
REPORT=0
MARK_STALE=0
FAIL_ON_DRIFT=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --wiki) WIKI="${2:-}"; shift 2 ;;
    --repo) REPO="${2:-}"; shift 2 ;;
    --old) OLD="${2:-}"; shift 2 ;;
    --new) NEW="${2:-}"; shift 2 ;;
    --report) REPORT=1; shift ;;
    --mark-stale) MARK_STALE=1; shift ;;
    --fail-on-drift) FAIL_ON_DRIFT=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 1 ;;
  esac
done

die() { echo "check-drift: $*" >&2; exit 1; }

is_wiki_root() {
  [[ -f "$1/AGENTS.md" && -d "$1/sources" ]]
}

discover_wiki() {
  if [[ -n "${LLM_WIKI_ROOT:-}" ]] && is_wiki_root "$LLM_WIKI_ROOT"; then
    printf '%s\n' "$LLM_WIKI_ROOT"
    return 0
  fi
  local dir
  dir="$(pwd)"
  while [[ "$dir" != "/" ]]; do
    if is_wiki_root "$dir"; then
      printf '%s\n' "$dir"
      return 0
    fi
    dir="$(dirname "$dir")"
  done
  return 1
}

yaml_scalar() {
  local file="$1" key="$2"
  awk -v k="$key" '
    $0 ~ "^" k ":" {
      sub("^" k ":[[:space:]]*", "")
      gsub("\r$", "")
      gsub(/^["'\'']|["'\'']$/, "")
      print
      exit
    }
  ' "$file"
}

yaml_list() {
  local file="$1" key="$2"
  awk -v k="$key" '
    $0 ~ "^" k ":" { inlist=1; next }
    inlist && /^[A-Za-z0-9_]+:/ { exit }
    inlist && /^[[:space:]]*-[[:space:]]*/ {
      sub(/^[[:space:]]*-[[:space:]]*/, "")
      gsub("\r$", "")
      gsub(/^["'\'']|["'\'']$/, "")
      if ($0 != "") print
    }
  ' "$file"
}

ticket_status() {
  awk '
    BEGIN { in_fm=0 }
    /^---[[:space:]]*$/ {
      if (in_fm==0) { in_fm=1; next }
      exit
    }
    in_fm && $0 ~ /^status:[[:space:]]*/ {
      sub(/^status:[[:space:]]*/, "")
      gsub(/^["'\'']|["'\'']$/, "")
      print
      exit
    }
  ' "$1"
}

list_pending() {
  local dir="$1"
  local found=0
  local f status
  local oldn
  oldn="$(shopt -p nullglob || true)"
  shopt -s nullglob
  for f in "$dir"/queue/drift/*.md; do
    [[ "$(basename "$f")" == "README.md" ]] && continue
    status="$(ticket_status "$f" || true)"
    if [[ "$status" == "pending" ]]; then
      found=1
      printf '%s\n' "$f"
    fi
  done
  eval "$oldn" 2>/dev/null || shopt -u nullglob
  [[ $found -eq 1 ]]
}

normalize_git_url() {
  local u="$1"
  u="${u%.git}"
  u="${u#git@github.com:}"
  u="${u#https://github.com/}"
  u="${u#ssh://git@github.com/}"
  printf '%s\n' "$u"
}

code_remote() {
  git -C "$1" remote get-url origin 2>/dev/null || true
}

realpath_portable() {
  if command -v realpath >/dev/null 2>&1; then
    realpath "$1"
  else
    python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$1"
  fi
}

match_source_file() {
  local wiki="$1" repo="$2"
  local f giturl path nrepo npath cremote
  nrepo="$(realpath_portable "$repo")"
  cremote="$(normalize_git_url "$(code_remote "$repo")")"
  local oldn
  oldn="$(shopt -p nullglob || true)"
  shopt -s nullglob
  for f in "$wiki"/sources/*.yaml "$wiki"/sources/*.yml; do
    [[ -f "$f" ]] || continue
    giturl="$(normalize_git_url "$(yaml_scalar "$f" git)")"
    if [[ -n "$cremote" && -n "$giturl" && "$cremote" == "$giturl" ]]; then
      printf '%s\n' "$f"
      eval "$oldn" 2>/dev/null || shopt -u nullglob
      return 0
    fi
    while IFS= read -r path; do
      [[ -z "$path" ]] && continue
      path="${path/#\~/$HOME}"
      if [[ -d "$path" ]]; then
        npath="$(realpath_portable "$path")"
        if [[ "$npath" == "$nrepo" ]]; then
          printf '%s\n' "$f"
          eval "$oldn" 2>/dev/null || shopt -u nullglob
          return 0
        fi
      fi
    done < <(yaml_list "$f" local_paths)
  done
  eval "$oldn" 2>/dev/null || shopt -u nullglob
  return 1
}

mark_pages_stale() {
  local wiki="$1"
  shift
  local page tmp
  for page in "$@"; do
    [[ -z "$page" ]] && continue
    case "$page" in
      /*) ;;
      *) page="$wiki/$page" ;;
    esac
    [[ -f "$page" ]] || continue
    tmp="$(mktemp)"
    awk '
      BEGIN { fm=0; seen=0 }
      /^---[[:space:]]*$/ {
        print
        if (fm==0) { fm=1; next }
        if (fm==1 && seen==0) { print "status: stale"; seen=1 }
        fm=2
        next
      }
      fm==1 && /^status:[[:space:]]*/ {
        print "status: stale"; seen=1; next
      }
      { print }
    ' "$page" > "$tmp"
    mv "$tmp" "$page"
  done
}

write_ticket() {
  local wiki="$1" srcfile="$2" old="$3" new="$4"
  local name short ticket rel f
  local files_count=0 pages_count=0
  name="$(yaml_scalar "$srcfile" name)"
  [[ -n "$name" ]] || name="$(basename "$srcfile" .yaml)"
  name="${name%.yml}"
  short="$(git -C "$REPO" rev-parse --short "$new")"
  mkdir -p "$wiki/queue/drift"

  local oldn
  oldn="$(shopt -p nullglob || true)"
  shopt -s nullglob
  for f in "$wiki/queue/drift/"*"-${name}-${short}.md"; do
    if [[ "$(ticket_status "$f")" == "pending" ]]; then
      echo "already pending: $f"
      eval "$oldn" 2>/dev/null || shopt -u nullglob
      return 0
    fi
  done
  eval "$oldn" 2>/dev/null || shopt -u nullglob

  local files_tmp pages_tmp
  files_tmp="$(mktemp)"
  pages_tmp="$(mktemp)"
  git -C "$REPO" diff --name-only "$old" "$new" -- "${TRACK_PATHS[@]}" \
    > "$files_tmp" || true
  yaml_list "$srcfile" pages > "$pages_tmp" || true

  if [[ ! -s "$files_tmp" ]]; then
    rm -f "$files_tmp" "$pages_tmp"
    echo "no tracked path changes ($name $old..$new)"
    return 0
  fi

  ticket="$wiki/queue/drift/$(date +%Y-%m-%d)-${name}-${short}.md"
  {
    printf '%s\n' "---"
    printf '%s\n' "status: pending"
    printf '%s\n' "repo: $name"
    printf '%s\n' "old_rev: $old"
    printf '%s\n' "new_rev: $new"
    printf '%s\n' "created: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '%s\n' "pages:"
    if [[ ! -s "$pages_tmp" ]]; then
      printf '%s\n' "  []"
    else
      while IFS= read -r rel; do
        [[ -z "$rel" ]] && continue
        printf '  - %s\n' "$rel"
        pages_count=$((pages_count + 1))
      done < "$pages_tmp"
    fi
    printf '%s\n' "files:"
    while IFS= read -r rel; do
      [[ -z "$rel" ]] && continue
      printf '  - %s\n' "$rel"
      files_count=$((files_count + 1))
    done < "$files_tmp"
    printf '%s\n' "---"
    printf '\n'
    printf 'Code moved %s -> %s. Mapped wiki pages may be stale.\n' "$old" "$new"
    printf '\nClose by targeted ingest, then compiled_rev: %s.\n' "$new"
  } > "$ticket"

  echo "opened $ticket ($files_count files)"
  if [[ $MARK_STALE -eq 1 && -s "$pages_tmp" ]]; then
    local pages_args
    pages_args=""
    while IFS= read -r rel; do
      [[ -n "$rel" ]] && mark_pages_stale "$wiki" "$rel"
    done < "$pages_tmp"
  fi
  rm -f "$files_tmp" "$pages_tmp"
}

check_one() {
  local srcfile="$1"
  local name compiled track_line
  name="$(yaml_scalar "$srcfile" name)"
  compiled="$(yaml_scalar "$srcfile" compiled_rev)"
  if [[ -z "$compiled" || "$compiled" == "null" \
        || "$compiled" == "REPLACE_AFTER_FIRST_INGEST" ]]; then
    echo "skip $srcfile: compiled_rev not set (ingest once first)"
    return 0
  fi

  local old new
  old="${OLD:-$compiled}"
  new="${NEW:-HEAD}"
  old="$(git -C "$REPO" rev-parse "$old")"
  new="$(git -C "$REPO" rev-parse "$new")"

  if [[ "$old" == "$new" ]]; then
    echo "up to date: ${name:-$srcfile}"
    return 0
  fi

  TRACK_PATHS=()
  while IFS= read -r track_line; do
    [[ -n "$track_line" ]] && TRACK_PATHS+=("$track_line")
  done < <(yaml_list "$srcfile" track)

  if [[ ${#TRACK_PATHS[@]} -eq 0 ]]; then
    echo "skip $srcfile: empty track: list" >&2
    return 0
  fi

  write_ticket "$WIKI" "$srcfile" "$old" "$new"
}

if [[ -z "$WIKI" ]]; then
  WIKI="$(discover_wiki)" \
    || die "could not find wiki root. Pass --wiki"
fi
WIKI="$(realpath_portable "$WIKI")"
is_wiki_root "$WIKI" || die "not a wiki root: $WIKI"

if [[ $REPORT -eq 1 ]]; then
  echo "wiki: $WIKI"
  if list_pending "$WIKI"; then
    echo "(pending tickets above)"
    [[ $FAIL_ON_DRIFT -eq 1 ]] && exit 2
    exit 0
  fi
  echo "no pending drift tickets"
  exit 0
fi

if [[ -z "$REPO" ]]; then
  if git rev-parse --show-toplevel >/dev/null 2>&1; then
    REPO="$(git rev-parse --show-toplevel)"
  else
    die "pass --repo DIR"
  fi
fi
REPO="$(realpath_portable "$REPO")"
git -C "$REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || die "not a git repo: $REPO"

srcfile=""
if ! srcfile="$(match_source_file "$WIKI" "$REPO")"; then
  die "no sources/*.yaml matches $REPO"
fi

check_one "$srcfile"

if [[ $FAIL_ON_DRIFT -eq 1 ]]; then
  if list_pending "$WIKI" >/dev/null; then
    exit 2
  fi
fi
