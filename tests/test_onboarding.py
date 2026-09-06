"""Isolated integration tests; never use real repositories, identity, hooks or network."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "scripts/wiki.py"
SPEC = importlib.util.spec_from_file_location("wiki_tools", CLI)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OnboardingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wiki-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.env = dict(os.environ)
        for key in MODULE.GIT_ENV:
            self.env.pop(key, None)
        self.env.update(
            {
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_AUTHOR_NAME": "Fixture",
                "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                "GIT_COMMITTER_NAME": "Fixture",
                "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
            }
        )
        self.wiki = self.root / "wiki with spaces"
        self.code = self.root / "code with spaces"
        self.run_cli("init", self.wiki)
        self.run_git(self.code, "init", create=True)
        (self.code / "src").mkdir()
        (self.code / "src/app.txt").write_text("first", encoding="utf-8")
        self.base = self.commit_code("base")

    def run_process(self, args, cwd=None, expected=0, env=None):
        result = subprocess.run(
            [str(x) for x in args],
            cwd=cwd or self.root,
            env=env or self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout + result.stderr

    def run_cli(self, *args, **kwargs):
        return self.run_process([sys.executable, CLI, *args], **kwargs)

    def run_git(self, repo, *args, create=False):
        if create:
            repo.mkdir(parents=True)
        return self.run_process(["git", "-C", repo, *args])

    def commit_code(self, message):
        self.run_git(self.code, "add", ".")
        self.run_git(self.code, "commit", "-m", message)
        return self.run_git(self.code, "rev-parse", "HEAD").strip()

    def register(self):
        self.run_cli(
            "register",
            "project",
            "--wiki",
            self.wiki,
            "--repo",
            self.code,
            "--track",
            "src/",
            "--page",
            "wiki/project.md",
        )
        path = self.wiki / "sources/project.json"
        data = json.loads(path.read_text())
        data["compiled_rev"] = self.base
        path.write_text(json.dumps(data), encoding="utf-8")
        (self.wiki / "wiki/project.md").write_text(
            "---\ntitle: demo\n---\nBody\n", encoding="utf-8"
        )

    def change(self):
        (self.code / "src/app.txt").write_text("second", encoding="utf-8")
        return self.commit_code("change")

    def check(self, *args, **kwargs):
        return self.run_cli(
            "check", "--wiki", self.wiki, "--source", "project", *args, **kwargs
        )

    def test_init_no_identity_no_commit(self):
        env = dict(self.env)
        for key in list(env):
            if key.startswith(("GIT_AUTHOR_", "GIT_COMMITTER_")):
                env.pop(key)
        self.run_cli("init", self.root / "identity-free", env=env)
        self.assertEqual(
            self.run_git(self.wiki, "diff", "--cached", "--name-only").strip(), ""
        )
        self.run_process(
            ["git", "-C", self.wiki, "rev-parse", "--verify", "HEAD"], expected=128
        )

    def test_init_preserves_existing_files(self):
        text = (self.wiki / "AGENTS.md").read_text()
        self.run_cli("init", self.wiki, expected=1)
        self.assertEqual((self.wiki / "AGENTS.md").read_text(), text)

    def test_status_discovers_wiki_from_copied_script(self):
        self.run_process([sys.executable, self.wiki / "scripts/wiki.py", "status"])

    def test_clone_keeps_empty_directories(self):
        self.run_git(self.wiki, "add", ".")
        self.run_git(self.wiki, "commit", "-m", "init")
        clone = self.root / "clone"
        self.run_process(["git", "clone", self.wiki, clone])
        for path in ("raw/assets", "raw/sources", "sources", "queue/drift"):
            self.assertTrue((clone / path).is_dir(), path)
        self.run_process([sys.executable, clone / "scripts/wiki.py", "doctor"])

    def test_bindings_do_not_sync(self):
        self.register()
        self.run_git(self.wiki, "add", ".")
        self.assertNotIn(".llm-wiki.local.json", self.run_git(self.wiki, "ls-files"))
        self.assertNotIn(
            str(self.code), (self.wiki / "sources/project.json").read_text()
        )

    def test_new_source_requires_review(self):
        self.run_cli("register", "new", "--wiki", self.wiki, "--repo", self.code)
        output = self.run_cli(
            "check", "--wiki", self.wiki, "--source", "new", expected=1
        )
        self.assertIn("first ingest", output)

    def test_ticket_idempotence_and_exit_code(self):
        self.register()
        self.change()
        self.check()
        first = list((self.wiki / "queue/drift").glob("*.md"))
        self.check("--fail-on-drift", expected=2)
        self.assertEqual(first, list((self.wiki / "queue/drift").glob("*.md")))
        self.assertIn("src/app.txt", first[0].read_text())

    def test_untracked_scope_no_ticket(self):
        self.register()
        (self.code / "unrelated.txt").write_text("outside")
        self.commit_code("outside")
        self.check()
        self.assertFalse(list((self.wiki / "queue/drift").glob("*.md")))

    def test_missing_revision_is_not_fresh(self):
        self.register()
        self.check("--new", "not-a-commit", expected=1)

    def test_stale_frontmatter_correct_and_preserves_mode(self):
        self.register()
        page = self.wiki / "wiki/project.md"
        page.chmod(0o644)
        self.change()
        self.check("--mark-stale")
        self.assertEqual(
            page.read_text(), "---\ntitle: demo\nstatus: stale\n---\nBody\n"
        )
        if os.name != "nt":
            self.assertEqual(page.stat().st_mode & 0o777, 0o644)

    def test_stale_without_frontmatter(self):
        self.assertEqual(
            MODULE.stale_text("Body\n"), "---\nstatus: stale\n---\n\nBody\n"
        )

    @unittest.skipIf(os.name == "nt", "POSIX hook execution; Windows CLI tested separately")
    def test_hook_installs_in_target_and_fires(self):
        self.register()
        self.run_cli("hooks", "--wiki", self.wiki, "--source", "project")
        path = self.code / ".git/hooks/post-merge"
        self.assertTrue(path.is_file())
        self.assertFalse((self.root / ".git/hooks").exists())
        self.change()
        self.run_process(["sh", path, "0"], cwd=self.code)
        self.assertTrue(list((self.wiki / "queue/drift").glob("*.md")))
        self.run_cli("hooks", "--wiki", self.wiki, "--source", "project")

    @unittest.skipIf(os.name == "nt", "POSIX Git hook execution")
    def test_real_merge_triggers_ticket(self):
        self.register()
        branch = self.run_git(self.code, "branch", "--show-current").strip()
        self.run_cli("hooks", "--wiki", self.wiki, "--source", "project")
        self.run_git(self.code, "checkout", "-b", "incoming")
        self.change()
        self.run_git(self.code, "checkout", branch)
        self.assertFalse(list((self.wiki / "queue/drift").glob("*.md")))
        self.run_git(self.code, "merge", "--ff-only", "incoming")
        self.assertTrue(list((self.wiki / "queue/drift").glob("*.md")))

    def test_cloud_signal_validated_and_idempotent(self):
        self.run_git(self.code, "remote", "add", "origin", "https://github.com/example/project.git")
        self.register()
        new = self.change()
        env = dict(self.env, LLM_WIKI_ROOT=str(self.wiki), SOURCE_ID="project",
                   SOURCE_REPOSITORY="example/project", NEW_REV=new)
        command = [sys.executable, ROOT / "scripts/cloud_signal.py"]
        self.run_process(command, env=env)
        ticket = next((self.wiki / "queue/drift").glob("cloud-*.md"))
        content = ticket.read_text().replace('status: "pending"', 'status: "done"')
        ticket.write_text(content)
        self.run_process(command, env=env)
        self.assertEqual(ticket.read_text(), content)
        self.run_process(command, env=dict(env, SOURCE_REPOSITORY="wrong/repo"), expected=1)

    def test_existing_hook_preserved_no_partial_install(self):
        self.register()
        hook = self.code / ".git/hooks/post-rewrite"
        hook.write_text("#!/bin/sh\nexit 0\n")
        self.run_cli("hooks", "--wiki", self.wiki, "--source", "project", expected=1)
        self.assertEqual(hook.read_text(), "#!/bin/sh\nexit 0\n")
        self.assertFalse((self.code / ".git/hooks/post-merge").exists())

    def test_custom_hooks_path(self):
        self.register()
        self.run_git(self.code, "config", "core.hooksPath", ".custom-hooks")
        self.run_cli("hooks", "--wiki", self.wiki, "--source", "project")
        self.assertTrue((self.code / ".custom-hooks/post-merge").is_file())

    def test_bound_on_another_device(self):
        self.register()
        self.run_git(self.wiki, "add", ".")
        self.run_git(self.wiki, "commit", "-m", "registered")
        clone = self.root / "device2-wiki"
        self.run_process(["git", "clone", self.wiki, clone])
        self.run_cli("doctor", "--wiki", clone, expected=1)
        self.run_cli("bind", "project", "--wiki", clone, "--repo", self.code)
        self.run_cli("doctor", "--wiki", clone)

    def test_path_traversal_rejected(self):
        self.run_cli(
            "register",
            "bad",
            "--wiki",
            self.wiki,
            "--repo",
            self.code,
            "--page",
            "../outside.md",
            expected=1,
        )
        self.assertFalse((self.wiki / "sources/bad.json").exists())

    def test_all_scans_bound_sources_despite_unbound_source(self):
        self.register()
        manifest = json.loads((self.wiki / "sources/project.json").read_text())
        manifest["name"] = "a-unbound"
        (self.wiki / "sources/a-unbound.json").write_text(json.dumps(manifest))
        self.change()
        self.run_cli("check", "--wiki", self.wiki, "--all", expected=1)
        self.assertTrue(list((self.wiki / "queue/drift").glob("project-*.md")))

    def test_wrong_remote_binding_rejected(self):
        self.run_git(self.code, "remote", "add", "origin", "https://github.com/example/project.git")
        self.register()
        self.run_git(self.code, "remote", "set-url", "origin", "https://github.com/example/other.git")
        self.run_cli("bind", "project", "--wiki", self.wiki, "--repo", self.code, expected=1)
        self.check(expected=1)

    def test_credential_remote_not_persisted(self):
        self.run_git(self.code, "remote", "add", "origin", "https://placeholder@example.invalid/project.git")
        self.run_cli("register", "secret", "--wiki", self.wiki, "--repo", self.code, expected=1)
        self.assertFalse((self.wiki / "sources/secret.json").exists())

    def test_earlier_unreviewed_changes_not_hidden(self):
        self.register()
        self.change()
        (self.code / "outside.txt").write_text("latest change outside track")
        newest = self.commit_code("outside")
        self.check()
        ticket = next((self.wiki / "queue/drift").glob("*.md")).read_text()
        self.assertIn(self.base, ticket)
        self.assertIn(newest, ticket)
        self.assertIn("src/app.txt", ticket)

    def test_legacy_yaml(self):
        (self.wiki / "sources/legacy.yaml").write_text(
            f"name: legacy\nlocal_paths:\n  - {self.code}\ntrack:\n  - src/\ncompiled_rev: {self.base}\npages:\n  - wiki/overview.md\n"
        )
        self.run_cli("check", "--wiki", self.wiki, "--source", "legacy")


if __name__ == "__main__":
    unittest.main()
