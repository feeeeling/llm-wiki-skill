# Ingest / query / maintenance

The full host-independent agreement is [templates/AGENTS.md](../templates/AGENTS.md).
A wiki receives its own copy during init. Read that local copy before acting.
No special slash command, model vendor, or skill directory is assumed.

## Ingest

Preserve the original source snapshot, cite it in compiled pages, update related
knowledge rather than duplicating it, then maintain the index and append-only log.
For code, register a source and review a pinned commit. Advance `compiled_rev` only
when its affected tracked scope is covered; never advance it merely because a diff
was detected. Clearly label inferred claims and unverified implementation details.

## Query

Read the index, check relevant pending tickets, trace claims to sources. If source
access is missing or review remains incomplete, say which snapshot you used and
what is uncertain. The protocol requires review of relevant stale pages; it does
not implement a runtime block on model responses.

## Maintenance

Use `status` for the queue and `check --all` for local Git changes. Resolve tickets
by reviewing source changes and mapped pages, recording the outcome and reviewed
revision, and closing only covered tickets. Unrelated work can proceed independently.
Semantic lint also checks contradictions, orphan pages, broken links and citations.
These semantic operations require a capable maintainer; the CLI does not call an LLM.

## Sync

Inspect local changes and remote/upstream state before pulling. Do not auto-stash,
stage all files, force-push, or discard another writer's work. Push only when the
user has authorized it. Local-only use needs neither remote nor credentials.
