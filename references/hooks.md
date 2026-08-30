# Hooks

`scripts/check-drift.sh` does not run by itself.

## Local (per machine)

```bash
bash scripts/install-hooks.sh /path/to/code-repo
```

Installs a guarded block into:

- `post-merge` — `git pull` (merge)
- `post-rewrite` — `git pull --rebase`
- `post-checkout` — branch switch

`.git/hooks` is **not** on GitHub. Rerun install on every clone/device.

## Manual

```bash
bash scripts/check-drift.sh --report
bash scripts/check-drift.sh --repo /path/to/code-repo --mark-stale
```

## Cloud (optional)

Code repo workflow: `templates/github/code-dispatch.yml`
Wiki repo workflow: `templates/github/wiki-drift.yml`

Rename from `*.example` after init. Secrets on the code repo:
`WIKI_REPO` (`owner/llm-wiki`), `WIKI_TOKEN`.
