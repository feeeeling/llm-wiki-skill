# Drift queue

`check-drift.sh` writes tickets here. Commit them so other devices see rot.

Tickets look like:

```markdown
---
status: pending
repo: my-repo
old_rev: abc
new_rev: def
pages:
  - wiki/concepts/example.md
files:
  - src/foo.ts
---

Code moved abc → def. Mapped wiki pages may be stale.
```

Agent: process `status: pending`, then set `status: done`. Do not delete the file (log trail).
