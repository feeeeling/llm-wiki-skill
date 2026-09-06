# My wiki

This is your knowledge repository, not the skill's source repository.
Read [AGENTS.md](AGENTS.md) for the maintenance protocol.

## Start here

```bash
python3 scripts/wiki.py doctor
python3 scripts/wiki.py status
```

Open this folder in any local-file-capable assistant or editor and ask:

> Read AGENTS.md and wiki/index.md. Ingest this source with citations, update the
> index and log, and tell me what changed. Do not push until I approve.

If your assistant cannot access local files, paste the protocol and source text,
then review and save its proposed pages yourself. No specific agent is required.

## Optional: register code

```bash
python3 scripts/wiki.py register my-project --repo /path/to/code \
  --track src/ --track README.md --page wiki/concepts/my-project.md
```

Ask your assistant to do the initial ingest. Set `compiled_rev` in the generated
`sources/my-project.json` to the commit actually reviewed, not merely the newest
commit. Doctor/check will report that review is needed until a baseline exists.

```bash
python3 scripts/wiki.py check --all
python3 scripts/wiki.py hooks --source my-project
```

Hooks are optional. Existing hooks are preserved; conflicts require manual integration.

## GitHub and another device

Init does not stage or commit anything. Configure your Git identity if needed, then
review files before committing. After creating an empty private GitHub repository:

```bash
git status
git add AGENTS.md README.md .gitignore .obsidian raw wiki sources queue scripts
git commit -m "Initialize my wiki"
git branch -M main
git remote add origin https://github.com/YOUR_ACCOUNT/YOUR_WIKI.git
git push -u origin main
```

If you enabled optional integration examples, stage those deliberately as well.

On another device: clone, open the folder, then bind code sources to local paths:

```bash
python3 scripts/wiki.py bind my-project --repo /this/device/code
python3 scripts/wiki.py doctor
```

`.llm-wiki.local.json` is ignored by Git. Reinstall hooks on each device if wanted.
No automatic push, background sync, GitHub credentials or model service is configured.

## Obsidian (optional)

Use **Open folder as vault**, select this directory, and open `wiki/overview.md`.
The files can also be read in any Markdown editor. Obsidian does not install Git
sync for you. Its device-specific workspace files are ignored.

## Platforms

Requires Python 3.9+ and Git, no pip packages. Use `python` or `py -3` instead of
`python3` where appropriate on Windows. Local hooks require a POSIX shell supplied
by Git Bash or WSL. Model/API costs, permissions and privacy depend on your host.
