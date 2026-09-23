"""Wire tests for the walk that finds the project's ``blind-reads.json``.

The surface is the reader the scripts use, ``shell_shapes.py --config <key>``,
whose stdout is the value a shell script gets, run with ``CLAUDE_PROJECT_DIR``
unset so the walk is the thing under test rather than the knob.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

WORKTREE_ROOT = Path(__file__).resolve().parents[1]
HOOK_DIR = WORKTREE_ROOT / "hooks"


def _git(cwd, *args):
    subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null"},
    )


class TheWalkFindsTheProjectFromInsideAWorktree(unittest.TestCase):
    """What the reader answers with ``CLAUDE_PROJECT_DIR`` unset, from a worktree.

    A worktree's ``.git`` is a pointer file rather than a directory, so a walk
    that stops at the first ``.git`` stops in the worktree.  The worktree
    carries no ``.claude/blind-reads.json`` of its own -- the declaration is
    committed in the project, and the tree is a checkout of a branch, not a
    second project -- so stopping there reads the declaration as absent, which
    is a fault the reader exits non-zero on rather than a lane moved silently
    back to its kit default.

    The variable is the knob and both scripts export it, so this is the
    fallback rather than the usual path.  It is still the path any other
    ``Bash`` child takes.
    """

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.project = Path(cls.tmp.name) / "project"
        cls.project.mkdir()
        _git(cls.tmp.name, "init", "-q", "-b", "main", "project")
        (cls.project / "README").write_text("x")
        _git(cls.project, "add", "-A")
        _git(cls.project, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
        #: written after the commit, so the worktree gets no copy of it -- which
        #: is the shape the walk stopped on
        (cls.project / ".claude").mkdir()
        (cls.project / ".claude" / "blind-reads.json").write_text(json.dumps({"tests_dir": "spec"}))
        cls.tree = cls.project / ".claude" / "worktrees" / "slug-spec"
        _git(cls.project, "worktree", "add", "-q", "-b", "slug", str(cls.tree))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _run(self, cwd):
        environment = dict(os.environ)
        environment.pop("GAUNTLET", None)
        environment.pop("CLAUDE_PROJECT_DIR", None)
        return subprocess.run(
            [sys.executable, str(HOOK_DIR / "shell_shapes.py"), "--config", "tests_dir"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            env=environment,
        )

    def _tests_dir(self, cwd):
        """(exit status, the one line the reader printed, its stderr)."""
        completed = self._run(cwd)
        return completed.returncode, completed.stdout.strip(), completed.stderr

    def test_the_worktree_carries_no_declaration_of_its_own(self):
        observed = {
            "declaration": (self.tree / ".claude" / "blind-reads.json").exists(),
            "pointer file": (self.tree / ".git").is_file(),
        }
        assert observed == {"declaration": False, "pointer file": True}

    def test_the_main_checkout_reads_its_declaration(self):
        assert self._tests_dir(self.project) == (0, "spec", "")

    def test_the_worktree_reads_the_projects_declaration_and_not_the_default(self):
        assert self._tests_dir(self.tree) == (0, "spec", "")

    def test_a_directory_under_the_worktree_reads_it_too(self):
        deeper = self.tree / "spec" / "unit"
        deeper.mkdir(parents=True, exist_ok=True)
        assert self._tests_dir(deeper) == (0, "spec", "")

    def test_checkout_of_names_the_main_checkout_and_the_tree_holding_the_path(self):
        sys.path.insert(0, str(HOOK_DIR))
        try:
            import lane_declaration
        finally:
            sys.path.remove(str(HOOK_DIR))
        project, tree = self.project.resolve(), self.tree.resolve()
        observed = {
            "from the worktree": lane_declaration.checkout_of(tree / "spec"),
            "from the main checkout": lane_declaration.checkout_of(project / "README"),
        }
        assert observed == {
            "from the worktree": (project, tree),
            "from the main checkout": (project, project),
        }

    def test_outside_any_checkout_there_is_no_project_and_that_is_a_fault(self):
        # No project and no copy beside the kit is no declaration at all.  The
        # reader exits non-zero and names the file, because a `tests_dir` printed
        # here would be substituted into a shell that binds a lane with it.
        completed = self._run(self.tmp.name)
        observed = {
            "status": completed.returncode,
            "stdout": completed.stdout,
            "names the file": "blind-reads.json" in completed.stderr,
        }
        assert observed == {"status": 2, "stdout": "", "names the file": True}
