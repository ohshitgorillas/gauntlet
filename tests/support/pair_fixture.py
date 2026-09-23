"""Fixture repository and block builders shared by the pair.sh behavior tests.

Everything here is imported by tests/test_pair_sh.py and
tests/test_pair_sh_merge.py; neither file builds a fixture repository of its own.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
PAIR = REPO / "scripts" / "pair.sh"
PAIR_PACKAGE = REPO / "scripts" / "pair"
STRIKE_DIFF = REPO / "scripts" / "strike-diff.py"
HOOK_MODULES = sorted((REPO / "hooks").rglob("*.py"))

SLUG = "demo"
TARGET = "main"
GATE = "true"

ENV = {
    "PATH": os.environ.get("PATH", ""),
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "Fixture",
    "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
    "GIT_COMMITTER_NAME": "Fixture",
    "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
}

GITIGNORE = ".venv/\n.claude/\n.pytest_cache/\n__pycache__/\n"

REVIEWER = (
    "READY\n"
    "discriminates: differential on the widget counter\n"
    "1  KEEP  two widgets -> 2, three widgets -> 3\n"
)
DIVERGED_REVIEWER = (
    "READY\n"
    "discriminates: differential on the widget counter\n"
    "1  KEEP  one widget -> 1, four widgets -> 4\n"
)

ASSERTION_X = "assert 2 + 2 == 4"
ASSERTION_B = "assert 5 + 5 == 10"
TEST_A_OTHER = "def test_a_other():\n    assert 3 + 3 == 6\n"
TEST_A = "def test_x():\n    " + ASSERTION_X + "\n\n\n" + TEST_A_OTHER
TEST_B = "def test_b_one():\n    " + ASSERTION_B + "\n"

BODY_NEW = (
    "slug: demo\n"
    "kind: new\n"
    "brief: none\n"
    "\n"
    "1. The widget counter reports two for two widgets and three for three.\n"
    "   kills: reports zero at every input\n"
    "   bite: null stub fails at both inputs (surface new)\n"
    "   existing: none\n"
)


def _block(body):
    return body + "\n--- reviewer ---\n" + REVIEWER


def _strike_body(target, assertion):
    return (
        "slug: demo\n"
        "motion: strike\n"
        "brief: none\n"
        "\n"
        f"1. strike {target}\n"
        "   rule: docs/testing.md rule 9\n"
        f"   assertion: {assertion}\n"
    )


BLOCK_NEW = _block(BODY_NEW)
BLOCK_WHOLE_FILE = _block(_strike_body("tests/test_b.py", ASSERTION_B))
BLOCK_SINGLE_TEST = _block(_strike_body("tests/test_a.py::test_x", ASSERTION_X))


def _git(cwd, *args):
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=dict(ENV), capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise RuntimeError("git " + " ".join(args) + " failed: " + done.stderr)
    return done.stdout.strip()


def _venv_shim(root):
    bindir = root / ".venv" / "bin"
    bindir.mkdir(parents=True, exist_ok=True)
    shim = bindir / "pytest"
    shim.write_text('#!/bin/sh\nexec "' + sys.executable + '" -m pytest "$@"\n')
    shim.chmod(shim.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return shim


def _repo(tmp_path, spec_text, review_text):
    repo = tmp_path / "repo"
    (repo / "tests").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "gauntlet" / "specs" / "approved").mkdir(parents=True)
    (repo / "gauntlet" / "reviews").mkdir(parents=True)
    for source in (PAIR, STRIKE_DIFF):
        landed = repo / "scripts" / source.name
        shutil.copy2(source, landed)
        landed.chmod(landed.stat().st_mode | stat.S_IXUSR)
    shutil.copytree(PAIR_PACKAGE, repo / "scripts" / "pair")
    #: the scripts read every directory, the target branch and the gate through
    #: the hooks' reader, and that reader is a facade over its sibling modules,
    #: so the fixture ships every one of them beside the scripts
    (repo / "hooks").mkdir(parents=True)
    for module in HOOK_MODULES:
        landed = repo / "hooks" / module.relative_to(REPO / "hooks")
        landed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(module, landed)
    #: the declaration is the project's and sits under `.claude/`, which the
    #: fixture's `.gitignore` keeps untracked exactly as a real checkout does
    (repo / ".claude").mkdir(parents=True, exist_ok=True)
    #: the fixture has no `make` and no gate of its own, and the point of the
    #: key is that the command is the project's: a gate that always passes
    #: leaves the merge steps around it as what these tests measure
    (repo / ".claude" / "blind-reads.json").write_text(
        json.dumps({"target_branch": TARGET, "gate_command": GATE})
    )
    (repo / "tests" / "test_a.py").write_text(TEST_A)
    (repo / "tests" / "test_b.py").write_text(TEST_B)
    (repo / "gauntlet" / "specs" / "approved" / "demo.txt").write_text(spec_text)
    (repo / "gauntlet" / "reviews" / "demo.1.txt").write_text(review_text)
    (repo / ".gitignore").write_text(GITIGNORE)
    _git(repo, "init", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "fixture")
    _venv_shim(repo)
    return repo


def _worktree(repo):
    return repo / ".claude" / "worktrees" / "demo-spec"


def _pair(repo, *args):
    env = dict(ENV)
    env["HOME"] = str(repo)
    done = subprocess.run(
        [str(repo / "scripts" / "pair.sh"), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    return done.stdout.splitlines()


def _pair_status(repo, *args):
    """Run pair.sh and return both its stdout lines and its exit status."""
    env = dict(ENV)
    env["HOME"] = str(repo)
    done = subprocess.run(
        [str(repo / "scripts" / "pair.sh"), *args],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    return done.stdout.splitlines(), done.returncode


def _merge_dir(repo):
    return repo / "gauntlet" / "merge"


def _merge_artifacts(repo):
    """The names of the files under gauntlet/merge/ in `repo`, sorted.

    Returns [] where the repository carries no such directory at all.
    """
    directory = _merge_dir(repo)
    if not directory.is_dir():
        return []
    return sorted(entry.name for entry in directory.iterdir())


def _artifact_ordinal(name):
    """The N of a `<slug>.<N>.txt` artifact name, or None where it carries none."""
    parts = name.split(".")
    if len(parts) != 3 or not parts[1].isdigit():
        return None
    return int(parts[1])


def _newest_merge_artifact(repo):
    """The text of the highest-numbered gauntlet/merge/<slug>.<N>.txt file.

    Returns "" where the directory holds no numbered file at all, so that a
    caller reading a section out of it reads an absence rather than raising.
    """
    directory = _merge_dir(repo)
    if not directory.is_dir():
        return ""
    numbered = [
        (_artifact_ordinal(entry.name), entry)
        for entry in directory.iterdir()
        if _artifact_ordinal(entry.name) is not None
    ]
    if not numbered:
        return ""
    return max(numbered, key=lambda pair: pair[0])[1].read_text()


def _gate_line(text):
    """The `gate:` line a merge artifact carries, stripped, or "" where none."""
    for line in text.splitlines():
        if line.strip().startswith("gate:"):
            return line.strip()
    return ""


def _python_listing(directory):
    return {entry.name for entry in directory.iterdir() if entry.suffix == ".py"}


ALPHA_SUITE = (
    "def test_alpha_passes():\n"
    "    assert 2 + 2 == 4\n"
    "\n"
    "\n"
    "def test_alpha_fails():\n"
    "    assert 2 + 2 == 5\n"
)
BRAVO_SUITE = (
    "def test_bravo_passes():\n"
    "    assert 5 + 5 == 10\n"
    "\n"
    "\n"
    "def test_bravo_fails():\n"
    "    assert 5 + 5 == 11\n"
)

SPEC_PATH = "gauntlet/specs/approved/" + SLUG + ".txt"

BODY_V2 = BODY_NEW.replace(
    "reports two for two widgets and three for three",
    "reports four for four widgets and five for five",
)
BLOCK_V2 = _block(BODY_V2)


def _show(tree, spec):
    """The text of a committed object, or "" where the revision names none."""
    done = subprocess.run(
        ["git", "show", spec], cwd=tree, env=dict(ENV), capture_output=True, text=True, check=False
    )
    return done.stdout if done.returncode == 0 else ""
