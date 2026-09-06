#!/usr/bin/env python3
"""Convert an authorized cross-repo notification into a review ticket, not a diff."""

import hashlib
import json
import os
import re
import sys

from wiki import (
    WikiError,
    atomic_write,
    normalized_remote,
    safe_path,
    sources,
    wiki_root,
)


def main():
    try:
        wiki = wiki_root(os.environ.get("LLM_WIKI_ROOT"))
        name = os.environ.get("SOURCE_ID", "")
        repository = os.environ.get("SOURCE_REPOSITORY", "")
        new = os.environ.get("NEW_REV", "")
        if not re.fullmatch(r"[0-9a-f]{40}", new):
            raise WikiError("NEW_REV must be a full commit SHA.")
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise WikiError("SOURCE_REPOSITORY must be owner/repo.")
        registered = sources(wiki)
        if name not in registered:
            raise WikiError(f"Unknown source: {name}")
        _, data = registered[name]
        if normalized_remote(data.get("git", "")) != f"github.com/{repository}":
            raise WikiError("Source repository does not match registered URL.")
        old = data.get("compiled_rev")
        if not isinstance(old, str) or not re.fullmatch(r"[0-9a-f]{40}", old):
            raise WikiError("Initial ingest must establish a full compiled_rev first.")
        if old == new:
            print("Source already reviewed at the signalled revision.")
            return 0
        key = hashlib.sha256(f"{name}:{old}:{new}".encode()).hexdigest()[:16]
        path = safe_path(wiki, f"queue/drift/cloud-{name}-{key}.md")
        if path.exists():
            print("Signal already recorded; existing review state preserved.")
            return 0
        meta = {
            "status": "pending", "repo": name, "old_rev": old, "new_rev": new,
            "kind": "remote-signal", "pages": data.get("pages", []),
            "files": [], "requires_local_diff": True,
        }
        header = "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in meta.items())
        atomic_write(path, "---\n" + header + "\n---\n\nRemote notification only: fetch the source when authorized, then compare compiled_rev to new_rev over the registered track paths. No path or semantic check has run in this workflow.\n")
        print(f"Opened {path.name}")
        return 0
    except (WikiError, OSError, ValueError) as exc:
        print(f"llm-wiki: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
