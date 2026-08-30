<!-- llm-wiki-schema: v1 -->

# LLM Wiki schema

You maintain this wiki. Humans curate sources and ask questions. Do not modify `raw/` or tracked code repositories.

Wiki root = this directory (contains `AGENTS.md` and `sources/`).

## Dual gate

Hard gate: `scripts/check-drift.sh` opens tickets in `queue/drift/`. It never edits prose.

Soft gate: you. Before **query** or **ingest**:

1. Run `bash scripts/check-drift.sh --report` (or read `queue/drift/*.md`).
2. If any ticket has `status: pending`, process those tickets first (targeted ingest on `files` / `pages`), then answer.
3. If a wiki page has `status: stale` or its `rev` is behind `sources/<name>.yaml` `compiled_rev`, ingest that slice first.

Refuse to answer from stale pages as if they were current. Say you are updating, then update.

Manual override: user says `/wiki-lint` or "process drift" → drain all pending tickets even if they did not ask a content question.

## Layout

- `raw/` — immutable non-code sources (articles, notes, converted PDFs). You read, never write.
- `wiki/` — pages you own. Prefer `wiki/sources/`, `wiki/entities/`, `wiki/concepts/`, `wiki/syntheses/`.
- Link with Obsidian wikilinks (`[[concepts/auth]]`) so Graph view works. Home: `wiki/overview.md`.
- `wiki/index.md` — catalog; update on every ingest.
- `wiki/log.md` — append-only. Entry prefix: `## [YYYY-MM-DD] ingest|query|lint|drift | title`
- `sources/*.yaml` — pointers to **code** repos (not copies). See `sources/example.yaml.disabled`.
- `queue/drift/` — git-sync the tickets so other devices see rot.

## Page frontmatter

```yaml
---
sources:
  - repo: my-repo          # or path under raw/
    paths: [src/auth.ts]
    rev: abcdef
status: current            # current | stale | needs-review
updated: YYYY-MM-DD
---
```

## Ingest

1. `git pull --rebase` this wiki repo first. One writer at a time.
2. Drain pending drift (or include this source's drift in the same pass).
3. Read the source (raw file or `git diff old_rev new_rev -- <files>`).
4. Update existing entity/concept pages; do not fork a second page for the same idea.
5. On contradiction: keep the history ("until rev X we claimed A; from rev Y it is B").
6. Refresh `wiki/index.md`. Append `wiki/log.md`.
7. Set mapped pages `status: current` and `rev`. Set yaml `compiled_rev` to the new HEAD when the ticket is fully applied.
8. Close the ticket: `status: done`.
9. `git add` / commit / remind the user to `git push`.

Scope to the ticket. Never rebuild the whole wiki because one file changed.

## Query

1. Dual-gate check above.
2. Read `wiki/index.md`, then the few relevant pages.
3. Cite wiki pages (and raw/rev when claims depend on code).
4. File a durable answer into `wiki/syntheses/` when the answer would be expensive to redo.

## Lint

Look for: pending drift, `stale` pages, `compiled_rev` behind origin/HEAD, contradictions, orphans, missing citations, concepts mentioned without a page.

## GitHub / devices

- Pull wiki before write; push after a coherent unit of work.
- Do not hand-merge two LLM rewrites of the same page — re-ingest from `raw` / code rev instead.
- Hooks are local (`.git/hooks`). If drift never appears after a pull in a code repo, run `scripts/install-hooks.sh` on this machine.
