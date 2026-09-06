# Optional Git hooks

Hooks are a local trigger, not an agent integration. They invoke the same Python
CLI that users can run manually. No hook invokes a model or pushes the wiki.

```bash
python3 scripts/wiki.py hooks --wiki /path/to/wiki --source project
```

The installer resolves the actual hooks directory of the target repo, including
`core.hooksPath` and Git worktrees. It preflights post-merge, post-rewrite and
post-checkout before writing. Existing hooks are never appended to or overwritten
unless their content exactly matches this installation (idempotent reinstall).
A conflict leaves existing hooks intact and asks for manual integration.

For an existing hook manager, add this command to its own supported mechanism:

```bash
python3 /path/to/wiki/scripts/wiki.py check --wiki /path/to/wiki --source project
```

When invoking it from a custom wrapper, preserve the hook manager's exit behavior.
A post-hook cannot undo a completed Git operation. Installed hooks report check
errors visibly but return success so they do not pretend to roll back Git.

## Trigger coverage

- `post-merge`: successful merge, including pulls using merge/fast-forward.
- `post-rewrite`: rebase/amend when Git fires that event.
- `post-checkout`: branch checkout (not individual-file checkout).

Not every possible Git operation triggers these: manual `reset`, fetch alone and
worktree edits are examples. A no-op pull may produce no merge event. Periodically
run `check --all`, especially before trusting a snapshot. Detection uses the reviewed
`compiled_rev`, not ORIG_HEAD or the hook's latest old/new pair.

Hooks embed local paths and Python interpreter locations; reinstall on each device.
If paths move, inspect and remove/replace only your own managed Hook files. No global
Git config is changed. Be careful with a shared `core.hooksPath`: other repos may
use it; the installer refuses conflicting content rather than taking it over.

## Cloud signals (optional)

See [templates/github](../templates/github). Workflow templates are not enabled
by init. The code repo sends a source-revision signal; the wiki opens a pending
review ticket. This cloud path does not run the local tracked-path diff or an LLM.
Reviewers must compare the registered baseline and signalled revision themselves.
Private cross-repo access requires a deliberately scoped token or GitHub App.
