---
name: llm-wiki
description: >
  Build and maintain a local, git-synced LLM wiki with a dual gate against stale pages.
  Use when initializing a wiki, ingesting sources, answering from the wiki, linting,
  handling drift tickets, installing git hooks, or when the user mentions LLM wiki,
  Karpathy wiki, check-drift, or /wiki-lint.
---

# LLM Wiki

Persistent markdown wiki. The LLM writes `wiki/`; humans curate sources and questions. Knowledge is compiled at ingest time, not re-derived on every query.

This skill is the **maintainer program**. The user's wiki git repo is the **knowledge**. Do not mix them.

## Locate the wiki

Wiki root = directory containing `AGENTS.md` and `sources/`.

Search order: `--wiki` / `$LLM_WIKI_ROOT` / walk up from cwd / ask the user.

If none exists, run init (do not invent a wiki in a random project repo).

## Commands

Resolve `SKILL_DIR` as the directory that contains this `SKILL.md`.

| User intent | Do this |
| ------------- | --------- |
| init / 新建 | `bash "$SKILL_DIR/scripts/init-wiki.sh" <target-dir>` then commit |
| status / 未完成工单 | `bash "<wiki>/scripts/check-drift.sh" --report` |
| 手动消化工单 / lint / `/wiki-lint` | Read `references/protocol.md`, process every `queue/drift/*.md` with `status: pending` |
| ingest 一篇源 | Protocol ingest. Refuse if pending drift exists unless the user wants drift processed first |
| 提问 / 阅读 wiki | `--report` first. Pending or `status: stale` pages → targeted ingest, then answer |
| 给代码仓装硬闸门 | `bash "<wiki>/scripts/install-hooks.sh" <code-repo>` |
| 登记代码仓 | Copy `templates/source.yaml` → `sources/<name>.yaml`, fill `git` / `local_paths` / `track` |

After init, prefer **wiki-local** scripts (`<wiki>/scripts/…`) so hooks do not depend on this skill path.

## Dual gate (non-negotiable)

**Hard gate (mechanical):** `check-drift.sh` only opens tickets under `queue/drift/`. It never calls an LLM and never rewrites wiki prose.

**Soft gate (you):** Before query or ingest, read pending tickets. Update mapped pages from `git diff old_rev new_rev`, then close the ticket (`status: done`), set page `status: current`, move `compiled_rev`.

Details: [references/protocol.md](references/protocol.md), [references/hooks.md](references/hooks.md).

## Layout (wiki repo)

```text
AGENTS.md          schema (soft gate) — you and the user co-evolve this
raw/               immutable non-code sources
wiki/              pages you own; humans rarely edit
sources/*.yaml     code-repo pointers (not a copy of the code)
queue/drift/       pending/done tickets (must be git-committed to sync devices)
scripts/           check-drift.sh, install-hooks.sh
```

## Rules

- `raw/` and tracked code are source of truth. Never modify them.
- Pull `--rebase` the wiki repo before you write; push when a unit of work is done. One writer at a time.
- File good answers back into `wiki/` instead of leaving them in chat.
- Scope ingest to the ticket's files/pages. Do not rebuild the whole wiki.
- If a claim contradicts a newer rev: record the change on the page, do not silently delete the old claim.
- Read [templates/AGENTS.md](templates/AGENTS.md) only when initializing or when the wiki's AGENTS.md is missing sections.
