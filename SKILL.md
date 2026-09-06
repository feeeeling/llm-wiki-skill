---
name: llm-wiki
description: >
  Build and maintain a local, Git-versioned Markdown knowledge base. Use when
  collecting sources, querying a wiki with citations, reviewing stale knowledge,
  processing drift tickets, or setting up an LLM wiki. Works through ordinary
  file and command access; no particular agent or slash command is required.
---

# LLM Wiki

You are a maintainer of the user's knowledge repository, not an installer for a
particular agent. This skill is optional: the same protocol is usable by a human
or any assistant with local file access. Do not install a specific host.

## Capabilities first

- With local file and terminal access: use the CLI below and read/edit pages.
- With file access only: inspect source configs and tickets as files; ask the user
  to run checks when necessary. Do not claim checks passed without results.
- Text-only chat: request the protocol and relevant sources; produce drafts for
  the user to save. Do not pretend to write files or synchronize GitHub.
- No model, API key, MCP server, Obsidian, or global skill directory is required
  by the mechanical tools. A model is supplied by the user's chosen host.

## Find the wiki

Use the user-provided path, `LLM_WIKI_ROOT`, or a directory containing `AGENTS.md`
and `sources/`. Ask if ambiguous. Read the wiki's `AGENTS.md` before maintaining it.
Do not confuse this skill's templates with the user's knowledge. For an older wiki
without `scripts/wiki.py`, use this skill checkout's CLI with explicit `--wiki` for
checks; ask before migrating its scripts or protocol. Do not install new hooks
until the wiki has the matching Python runtime.

## Entry points

Resolve this skill's root from the location of this SKILL.md. Use Python 3.9+
(`python3`, `python`, or `py -3`, according to the user's environment) and Git.
Never assume the terminal cwd is the wiki. Pass `--wiki` explicitly when uncertain.

| Intent | Action |
| --- | --- |
| Initialize | `python3 <skill>/scripts/wiki.py init <empty-directory>` |
| Diagnose setup | `python3 <wiki>/scripts/wiki.py doctor --wiki <wiki>` |
| List pending | `python3 <wiki>/scripts/wiki.py status --wiki <wiki>` |
| Scan registered code | `python3 <wiki>/scripts/wiki.py check --wiki <wiki> --all` |
| Register source | `python3 <wiki>/scripts/wiki.py register NAME --wiki <wiki> --repo <code>` |
| Bind another device | `python3 <wiki>/scripts/wiki.py bind NAME --wiki <wiki> --repo <code>` |
| Optional hooks | `python3 <wiki>/scripts/wiki.py hooks --wiki <wiki> --source NAME` |
| Ingest, query, maintenance | Follow the wiki's AGENTS.md and [protocol](references/protocol.md) |

`status` never scans code. `check` never calls a model or advances the reviewed
baseline. Initial ingest must establish `compiled_rev`; a newer SHA alone does not
prove that an existing claim is false. Pending relevant tickets require review;
unavailable sources must be reported as unknown.

## Safety and synchronization

Init never overwrites a nonempty directory or commits/pushes automatically.
Machine-specific repo paths are ignored local bindings; share source IDs and URLs.
Hooks are opt-in and must preserve existing user automation. See [hooks](references/hooks.md).
Do not silently edit global config, provision services, or upload private data.
The soft gate is a protocol, not a runtime-enforced guarantee.

Read [onboarding](references/onboarding.md) for installation paths, CLI usage,
GitHub setup, platform requirements, and migration from the shell-only version.
