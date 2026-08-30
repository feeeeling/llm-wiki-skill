# Protocol

## Ingest

1. `git pull --rebase` in the wiki repo.
2. `bash scripts/check-drift.sh --report`. Drain `status: pending` tickets first.
3. Read the source (`raw/...` or `git diff old_rev new_rev -- <files>`).
4. Update existing entity/concept pages. Do not fork a second page for the same idea.
5. On contradiction, keep history on the page (old rev claimed A; new rev is B).
6. Use Obsidian wikilinks so the graph works: `[[concepts/auth]]`.
7. Refresh `wiki/index.md`. Append `wiki/log.md`:
   `## [YYYY-MM-DD] ingest | title`
8. Set page `status: current` and `rev`. Set yaml `compiled_rev` when the
   ticket is fully applied. Ticket `status: done`.
9. Commit. Ask the user to `git push`.

Scope to the ticket. Never rebuild the whole wiki for one file.

## Query

1. Dual-gate check (pending tickets / `stale` pages) before answering.
2. Read `wiki/index.md`, then a few pages. Cite them.
3. File expensive answers into `wiki/syntheses/`.

## Lint / `/wiki-lint`

Drain every pending ticket. Then scan for `stale`, `compiled_rev` behind
HEAD, contradictions, orphans, missing citations.
