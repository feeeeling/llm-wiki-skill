# llm-wiki

Local-first [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (Karpathy) packaged as an [Agent Skill](https://agentskills.io). GitHub-syncable. Dual gate so wiki pages do not rot when the underlying git repos move on.

中文说明见下。 English: install the skill, `init` a wiki repo, register code sources, install hooks, push the wiki to GitHub.

## What you install vs what you own

| This skill (public) | Your wiki repo (yours, often private) |
| --------------------- | ---------------------------------------- |
| Protocol + scripts + templates | `wiki/` pages, `raw/` sources, drift tickets |
| Versioned like any other skill | Synced across devices with git |

## Dual gate

1. **Hard (mechanical):** `scripts/check-drift.sh` runs from git hooks / CI / `--report`. It compares `compiled_rev` to `HEAD`, intersects with `track:` paths, and opens a ticket in `queue/drift/`. No LLM.
2. **Soft (agent):** Next read, or an explicit lint command, processes pending tickets: read the diff, update mapped pages, close the ticket.

Git itself is never blocked. Querying a stale wiki is.

## Install the skill

**Pi** (project-local, recommended):

```bash
mkdir -p .agents/skills
ln -s /path/to/llm-wiki-skill .agents/skills/llm-wiki
```

Or copy/clone into `~/.agents/skills/llm-wiki` (global — adds a skill description to every request).

**Claude Code / Codex / other Agent Skills hosts:** clone this repo into that host's skills directory, or use whatever `add-skill` flow you already use.

## Init a wiki

```bash
bash /path/to/llm-wiki-skill/scripts/init-wiki.sh ~/my-wiki
cd ~/my-wiki
git remote add origin git@github.com:<you>/<wiki>.git
git push -u origin main
```

Open that directory in your agent (and optionally Obsidian).

## Register a code repo (optional)

```bash
cp templates/source.yaml ~/my-wiki/sources/my-repo.yaml
# edit git, local_paths, track
bash ~/my-wiki/scripts/install-hooks.sh /path/to/code-repo
```

Hooks live in `.git/hooks` and **do not travel with GitHub**. Run `install-hooks.sh` once per machine per code repo. See [references/hooks.md](references/hooks.md).

## Daily loop

```text
git pull                 # in the code repo → post-merge → drift ticket
git pull                 # in the wiki repo (other devices see the ticket)
ask the wiki /wiki-lint  # agent updates pages, closes ticket, you push wiki
```

Manual status (no LLM):

```bash
bash ~/my-wiki/scripts/check-drift.sh --report
```

## Requirements

`bash`, `git`. No Python/Node runtime.

## License

MIT
