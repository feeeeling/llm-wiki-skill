#!/usr/bin/env python3
"""Host-independent LLM wiki tools. Python 3.9+ and Git; no pip packages."""

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

VERSION = 2
HOOK_MARKER = "# llm-wiki managed hook v2"
HOOK_NAMES = ("post-merge", "post-rewrite", "post-checkout")
GIT_ENV = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_COMMON_DIR",
    "GIT_PREFIX",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


class WikiError(Exception):
    """An actionable configuration or operation error."""


def git(repo, *args):
    env = {k: v for k, v in os.environ.items() if k not in GIT_ENV}
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        env=env,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise WikiError(result.stderr.decode(errors="replace").strip())
    return result.stdout.decode("utf-8")


def root_path(value):
    return Path(value).expanduser().resolve()


def is_wiki(path):
    return (path / "AGENTS.md").is_file() and (path / "sources").is_dir()


def wiki_root(explicit=None):
    requested = explicit or os.environ.get("LLM_WIKI_ROOT")
    if requested:
        path = root_path(requested)
        if not is_wiki(path):
            raise WikiError(f"Not a wiki: {path}. Run init or pass --wiki PATH.")
        return path
    cwd = Path.cwd().resolve()
    for path in (cwd, *cwd.parents, Path(__file__).resolve().parent.parent):
        if is_wiki(path):
            return path
    raise WikiError("Wiki not found. Pass --wiki PATH or set LLM_WIKI_ROOT.")


def safe_path(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or not path.resolve().is_relative_to(
        root.resolve()
    ):
        raise WikiError(f"Path must stay inside {root}: {relative}")
    if path.is_symlink():
        raise WikiError(f"Refusing to replace symlink: {path}")
    return path


def atomic_write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise WikiError(f"Refusing to replace symlink: {path}")
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as tmp:
        tmp.write(content)
        temp_path = Path(tmp.name)
    try:
        temp_path.chmod(path.stat().st_mode & 0o777 if path.exists() else 0o644)
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def write_json(path, data):
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read_json(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise WikiError(f"Expected a JSON object: {path}")
    return data


def legacy_source(path):
    """Read the old documented scalar/block-list YAML subset, never eval YAML."""
    data = {}
    key = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or line.strip() == "---":
            continue
        if line.startswith("  - ") and key and isinstance(data[key], list):
            data[key].append(line[4:].strip().strip("\"'"))
            continue
        match = re.fullmatch(r"([a-z_]+):\s*(.*)", line)
        if not match:
            raise WikiError(f"Unsupported legacy YAML in {path}; migrate it to JSON.")
        key, value = match.groups()
        if not value or value == "[]":
            data[key] = []
        elif value in ("null", "~"):
            data[key] = None
        else:
            data[key] = value.strip("\"'")
    return data


def validate_source(data, path):
    name = data.get("name")
    if not isinstance(name, str) or not re.fullmatch(
        r"[a-zA-Z0-9][a-zA-Z0-9_-]*", name
    ):
        raise WikiError(f"Invalid source name in {path}; use letters, digits, - or _.")
    if not isinstance(data.get("git", ""), str):
        raise WikiError(f"git must be a URL string: {path}")
    if data.get("compiled_rev") == []:
        data["compiled_rev"] = None  # Empty scalar in legacy YAML.
    if data.get("compiled_rev") is not None and not isinstance(data["compiled_rev"], str):
        raise WikiError(f"compiled_rev must be a string or null: {path}")
    for field in ("track", "pages", "local_paths"):
        values = data.get(field, [])
        if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
            raise WikiError(f"{field} must be a string array: {path}")
    for item in data.get("track", []):
        if (
            not item
            or Path(item).is_absolute()
            or ".." in Path(item).parts
            or item.startswith(":")
        ):
            raise WikiError(f"Unsafe track path: {item}")
    if not data.get("track"):
        raise WikiError(f"Empty track list in {path}")
    return data


def sources(wiki):
    result = {}
    for path in sorted((wiki / "sources").iterdir()):
        if path.suffix not in (".json", ".yaml", ".yml"):
            continue
        data = read_json(path) if path.suffix == ".json" else legacy_source(path)
        validate_source(data, path)
        if data["name"] in result:
            raise WikiError(f"Duplicate source name: {data['name']}")
        for page in data.get("pages", []):
            safe_path(wiki, page)
        result[data["name"]] = (path, data)
    return result


def local_bindings(wiki):
    path = wiki / ".llm-wiki.local.json"
    return read_json(path) if path.exists() else {}


def normalized_remote(url):
    return re.sub(
        r"^(git@github.com:|https://github.com/|ssh://git@github.com/)",
        "github.com/",
        url.rstrip("/").removesuffix(".git"),
    )


def remote(repo):
    try:
        return git(repo, "remote", "get-url", "origin").strip()
    except WikiError:
        return ""


def portable_remote(url):
    """Do not publish local paths or credentials from a developer's origin URL."""
    if re.fullmatch(r"[\w.-]+@[\w.-]+:[\w./-]+", url):
        return url
    parsed = urlsplit(url)
    if parsed.scheme not in ("http", "https", "ssh", "git"):
        return ""
    if parsed.password or parsed.query or parsed.fragment or (
        parsed.username and parsed.scheme != "ssh"
    ):
        raise WikiError("Origin URL contains credentials/query data. Use a clean remote URL before registration.")
    return url


def validate_repo(data, repo):
    repo = root_path(git(root_path(repo), "rev-parse", "--show-toplevel").strip())
    expected = data.get("git")
    actual = remote(repo)
    if expected and normalized_remote(expected) != normalized_remote(actual):
        raise WikiError(f"Repository origin does not match source {data['name']}; check the binding/remote URL.")
    return repo


def source_repo(wiki, data):
    binding = local_bindings(wiki).get(data["name"])
    candidates = ([binding] if binding else []) + data.get("local_paths", [])
    for value in candidates:
        if isinstance(value, str) and root_path(value).is_dir():
            return validate_repo(data, root_path(value))
    raise WikiError(
        f"Source {data['name']} is unbound on this device. Run bind NAME --repo PATH."
    )


def select_source(wiki, name=None, repo=None):
    registered = sources(wiki)
    if name:
        if name not in registered:
            raise WikiError(f"Unknown source: {name}. Run register first.")
        path, data = registered[name]
        return path, data, validate_repo(data, repo) if repo else source_repo(wiki, data)
    if not repo:
        raise WikiError("Specify --source NAME or --repo PATH, or use --all.")
    target = root_path(repo)
    url = remote(target)
    matches = []
    for path, data in registered.values():
        same_remote = bool(
            url
            and data.get("git")
            and normalized_remote(url) == normalized_remote(data["git"])
        )
        try:
            same_path = source_repo(wiki, data) == target
        except WikiError:
            same_path = False
        if same_path or same_remote:
            matches.append((path, data, target))
    if len(matches) != 1:
        raise WikiError(
            "No unique source for repo; register/bind it, or specify --source NAME."
        )
    return matches[0]


def commit_rev(repo, rev):
    if not isinstance(rev, str) or not rev or rev.startswith("-"):
        raise WikiError(f"Invalid revision: {rev!r}")
    return git(repo, "rev-parse", "--verify", f"{rev}^{{commit}}").strip()


def pending(wiki):
    result = []
    for path in sorted((wiki / "queue/drift").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
        if match and re.search(r"^status:\s*[\"']?pending[\"']?\s*$", match[1], re.M):
            result.append(path)
    return result


def stale_text(text):
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
    if not match:
        return "---\nstatus: stale\n---\n\n" + text
    body = match[1]
    if re.search(r"^status:.*$", body, re.M):
        body = re.sub(r"^status:.*$", "status: stale", body, flags=re.M)
    else:
        body += "\nstatus: stale"
    return "---\n" + body + "\n---\n" + text[match.end() :]


def check_one(wiki, data, repo, mark_stale=False, new="HEAD"):
    baseline = data.get("compiled_rev")
    if not baseline or baseline == "REPLACE_AFTER_FIRST_INGEST":
        raise WikiError(
            f"{data['name']}: first ingest required; set compiled_rev only after reviewing pages."
        )
    old = commit_rev(repo, baseline)
    new = commit_rev(repo, new)
    changed = git(
        repo,
        "diff",
        "--name-only",
        "--no-renames",
        "-z",
        old,
        new,
        "--",
        *data["track"],
    )
    files = [name for name in changed.split("\0") if name]
    if not files:
        print(f"{data['name']}: no tracked changes")
        return
    # Baseline is part of the key: a hook's latest event must not hide earlier changes.
    key = hashlib.sha256(f"{data['name']}:{old}:{new}".encode()).hexdigest()[:16]
    path = safe_path(wiki, f"queue/drift/{data['name']}-{key}.md")
    if not path.exists():
        meta = {
            "status": "pending",
            "repo": data["name"],
            "old_rev": old,
            "new_rev": new,
            "created": dt.datetime.now(dt.timezone.utc).isoformat(),
            "pages": data.get("pages", []),
            "files": files,
        }
        header = "\n".join(
            f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in meta.items()
        )
        atomic_write(
            path,
            "---\n"
            + header
            + "\n---\n\nReview the source at new_rev; do not advance compiled_rev until the affected pages are reviewed.\n",
        )
        print(f"Opened {path.name} ({len(files)} files)")
    else:
        print(f"Already recorded: {path.name}")
    if mark_stale and path in pending(wiki):
        for page in data.get("pages", []):
            target = safe_path(wiki, page)
            if target.is_file():
                atomic_write(target, stale_text(target.read_text(encoding="utf-8")))


def init_wiki(args):
    target = root_path(args.target)
    if target.exists() and any(target.iterdir()):
        raise WikiError(
            "Target is not empty; init never overwrites files. Choose an empty directory."
        )
    skill = Path(__file__).resolve().parent.parent
    if not (skill / "templates/AGENTS.md").is_file():
        raise WikiError("Run init using the skill checkout, not a copied wiki runtime.")
    if not shutil.which("git"):
        raise WikiError("Git is required; install it before initialization.")
    target.mkdir(parents=True, exist_ok=True)
    for directory in (
        "raw/sources",
        "raw/assets",
        "sources",
        "queue/drift",
        "wiki",
        ".obsidian",
    ):
        (target / directory).mkdir(parents=True, exist_ok=True)
    shutil.copy2(skill / "templates/AGENTS.md", target / "AGENTS.md")
    shutil.copytree(
        skill / "scripts",
        target / "scripts",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    shutil.copytree(
        skill / "templates/obsidian", target / ".obsidian", dirs_exist_ok=True
    )
    for directory in ("raw/sources", "raw/assets", "sources", "queue/drift"):
        atomic_write(target / directory / ".gitkeep", "")
    shutil.copy2(
        skill / "templates/source.json", target / "sources/example.json.disabled"
    )
    shutil.copy2(skill / "templates/WIKI_README.md", target / "README.md")
    atomic_write(
        target / "wiki/overview.md",
        "# Overview\n\nYour knowledge starts here.\n\n- [[index]]\n- [[log]]\n",
    )
    atomic_write(
        target / "wiki/index.md",
        "# Index\n\n- [[overview]] — Home\n- [[log]] — Operations\n",
    )
    atomic_write(
        target / "wiki/log.md",
        "# Log\n\nAppend entries as `## [YYYY-MM-DD] kind | title`.\n",
    )
    atomic_write(
        target / ".gitignore",
        ".DS_Store\n.llm-wiki.local.json\n__pycache__/\n.obsidian/workspace*.json\n.obsidian/cache/\n.trash/\n",
    )
    git(target, "init")
    print(
        f"Wiki created: {target}\nNo commit, remote, hooks, or model configured automatically.\nNext: read README.md, then run doctor."
    )


def bind_repo(wiki, name, repo):
    _, data = sources(wiki)[name]
    repo = validate_repo(data, repo)
    bindings = local_bindings(wiki)
    bindings[name] = str(repo)
    write_json(wiki / ".llm-wiki.local.json", bindings)
    # Exclude the machine binding even for legacy wiki repos.
    exclude = Path(git(wiki, "rev-parse", "--git-path", "info/exclude").strip())
    if not exclude.is_absolute():
        exclude = wiki / exclude
    text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    if ".llm-wiki.local.json" not in text.splitlines():
        atomic_write(exclude, text + "\n.llm-wiki.local.json\n")
    print(f"Bound {name} on this device: {repo}")


def register(args):
    wiki = wiki_root(args.wiki)
    data = {
        "name": args.name,
        "git": portable_remote(remote(root_path(args.repo))),
        "track": args.track or ["."],
        "compiled_rev": None,
        "pages": args.page or [],
    }
    validate_source(data, "registration")
    if args.name in sources(wiki):
        raise WikiError("Source already exists; use bind on another device.")
    for page in data["pages"]:
        safe_path(wiki, page)
    git(root_path(args.repo), "rev-parse", "--show-toplevel")
    git(wiki, "rev-parse", "--git-dir")
    local_bindings(wiki)  # Validate local JSON before persisting the manifest.
    manifest = safe_path(wiki, f"sources/{args.name}.json")
    if manifest.exists():
        raise WikiError(f"Existing manifest preserved: {manifest}")
    write_json(manifest, data)
    bind_repo(wiki, args.name, args.repo)
    print(
        "Registered. Ask your agent to ingest this source; record the reviewed SHA in compiled_rev afterwards."
    )


def hooks_dir(repo):
    path = Path(git(repo, "rev-parse", "--git-path", "hooks").strip())
    return path if path.is_absolute() else repo / path


def hook_content(wiki, source, name):
    command = shlex.join(
        [
            sys.executable,
            str(wiki / "scripts/wiki.py"),
            "check",
            "--wiki",
            str(wiki),
            "--source",
            source,
        ]
    )
    guard = '[ "${3:-0}" = "1" ] || exit 0\n' if name == "post-checkout" else ""
    return (
        "#!/bin/sh\n"
        + HOOK_MARKER
        + "\n"
        + guard
        + "unset "
        + " ".join(GIT_ENV)
        + "\n"
        + command
        + '\nresult=$?\nif [ "$result" != "0" ]; then\n  echo "llm-wiki: detection failed; run doctor/check manually." >&2\nfi\nexit 0\n'
    )


def install_hooks(args):
    wiki = wiki_root(args.wiki)
    if not (wiki / "scripts/wiki.py").is_file():
        raise WikiError("Wiki runtime is missing; migrate scripts/wiki.py before installing hooks.")
    _, data, repo = select_source(wiki, args.source, args.repo)
    repo = root_path(git(repo, "rev-parse", "--show-toplevel").strip())
    bind_repo(wiki, data["name"], repo)
    directory = hooks_dir(repo)
    # Preflight all hooks. Never append shell to an existing Python hook or exit 0.
    for name in HOOK_NAMES:
        path = directory / name
        if path.is_symlink() or (
            path.exists()
            and path.read_text(encoding="utf-8")
            != hook_content(wiki, data["name"], name)
        ):
            raise WikiError(
                f"Existing hook preserved: {path}. Integrate the check command manually; no hooks changed."
            )
    for name in HOOK_NAMES:
        path = directory / name
        atomic_write(path, hook_content(wiki, data["name"], name))
        path.chmod(0o755)
        print(f"Installed {path}")


def doctor(args):
    wiki = wiki_root(args.wiki)
    problems = []
    print(
        f"Python {sys.version.split()[0]} | {git(wiki, '--version').strip()}\nWiki: {wiki}"
    )
    if not remote(wiki):
        print("INFO: no Git remote (local-only use is fine).")
    if not git(wiki, "status", "--porcelain").strip():
        print("Git working tree: clean")
    else:
        print("INFO: uncommitted files; commit deliberately before syncing.")
    for directory in ("raw", "wiki", "sources", "queue/drift"):
        if not (wiki / directory).is_dir():
            problems.append(f"Missing {directory}/; create it before ingest.")
    for _, data in sources(wiki).values():
        try:
            repo = source_repo(wiki, data)
            if (
                not data.get("compiled_rev")
                or data["compiled_rev"] == "REPLACE_AFTER_FIRST_INGEST"
            ):
                raise WikiError(f"{data['name']}: initial ingest not completed.")
            commit_rev(repo, data["compiled_rev"])
            installed = all(
                (hooks_dir(repo) / n).is_file()
                and (hooks_dir(repo) / n).read_text(encoding="utf-8") == hook_content(wiki, data["name"], n)
                and os.access(hooks_dir(repo) / n, os.X_OK)
                for n in HOOK_NAMES
            )
            print(
                f"{data['name']}: source accessible; hooks {'installed' if installed else 'not installed (manual check available)'}"
            )
        except WikiError as exc:
            problems.append(str(exc))
    print(f"Pending tickets: {len(pending(wiki))}")
    for message in problems:
        print("ACTION: " + message)
    return 1 if problems else 0


def check(args):
    wiki = wiki_root(args.wiki)
    if args.all and (args.source or args.repo):
        raise WikiError("Use --all or a specific --source/--repo, not both.")
    if not args.all:
        _, data, repo = select_source(wiki, args.source, args.repo)
        check_one(wiki, data, repo, args.mark_stale, args.new)
    else:
        failed = False
        for _, data in sources(wiki).values():
            try:
                check_one(wiki, data, source_repo(wiki, data), args.mark_stale, args.new)
            except (WikiError, OSError, ValueError) as exc:
                failed = True
                print(f"ACTION: {data['name']}: {exc}", file=sys.stderr)
        if failed:
            return 1
    return 2 if args.fail_on_drift and pending(wiki) else 0


def status(args):
    wiki = wiki_root(args.wiki)
    tickets = pending(wiki)
    for path in tickets:
        print(path.relative_to(wiki))
    print(
        f"{len(tickets)} pending ticket(s). Status does not scan code; use check --all."
    )
    return 2 if args.fail_on_drift and tickets else 0


def parser():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    init = commands.add_parser(
        "init", help="Create a wiki in an empty directory (no auto-commit)"
    )
    init.add_argument("target")
    init.set_defaults(handler=init_wiki)
    for name, handler in (
        ("register", register),
        ("bind", None),
        ("check", check),
        ("status", status),
        ("doctor", doctor),
        ("hooks", install_hooks),
    ):
        sub = commands.add_parser(name)
        sub.add_argument(
            "--wiki",
            help="Wiki path; otherwise discover from cwd/script or LLM_WIKI_ROOT",
        )
        sub.set_defaults(handler=handler)
        if name in ("register", "bind"):
            sub.add_argument("name")
            sub.add_argument("--repo", required=True)
        if name == "register":
            sub.add_argument(
                "--track",
                action="append",
                help="Git pathspec to track; repeatable, default '.'",
            )
            sub.add_argument(
                "--page", action="append", help="Affected wiki page; repeatable"
            )
        if name in ("check", "hooks"):
            sub.add_argument("--source")
            sub.add_argument("--repo")
        if name == "check":
            sub.add_argument("--all", action="store_true")
            sub.add_argument("--new", default="HEAD")
            sub.add_argument("--mark-stale", action="store_true")
        if name in ("status", "check"):
            sub.add_argument(
                "--fail-on-drift",
                action="store_true",
                help="Exit 2 if tickets are pending",
            )
    return cli


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "bind":
            wiki = wiki_root(args.wiki)
            if args.name not in sources(wiki):
                raise WikiError("Source not registered. Use register for a new source.")
            bind_repo(wiki, args.name, args.repo)
            return 0
        return args.handler(args) or 0
    except (WikiError, OSError, ValueError, UnicodeError) as exc:
        print(f"llm-wiki: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
