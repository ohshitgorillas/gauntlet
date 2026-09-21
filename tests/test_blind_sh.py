"""Execution tests for the blind agents' command shell, scripts/blind.sh.

Every fixture here is a git checkout the test builds and removes again, so
nothing is read from the ambient working directory (docs/testing.md rule 16).
They are built beside this file rather than in the suite's temporary
directory, because the shell under test runs the paths it is given from a
child process that cannot reach the latter. The block texts asserted as stdout
are the fixture's own, supplied by tests/support/pair_fixture.py, so they are
assertable verbatim.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.pair_fixture import (
    BLOCK_NEW,
    BLOCK_V2,
    ENV,
    GATE,
    GITIGNORE,
    HOOK_MODULES,
    REVIEWER,
    SLUG,
    TARGET,
    _git,
    _pair,
    _repo,
    _venv_shim,
    _worktree,
)

REPO = Path(__file__).resolve().parent.parent
BLIND = REPO / "scripts" / "blind.sh"
FIXTURE_ROOT = Path(__file__).resolve().parent / ".blind-sh-fixtures"

TARGET_NAME = "test_target.py"
TARGET_ARG = ".claude/worktrees/" + SLUG + "-spec/tests/" + TARGET_NAME
PASSING = "def test_target():\n    assert 2 + 2 == 4\n"
FAILING = "def test_target():\n    assert 2 + 2 == 5\n"


@pytest.fixture
def fixture_root(request):
    """An empty directory beside this file, removed again after the test.

    The shell under test enters the paths it is given from a child process
    that cannot reach the suite's temporary directory, so the fixture
    checkouts are built here instead. The name is dot-prefixed, which pytest
    does not collect, and the tree is removed on teardown.
    """
    root = FIXTURE_ROOT / request.node.name.replace("[", "-").replace("]", "")
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _install_blind(root):
    """Land an executable copy of scripts/blind.sh in `root`/scripts.

    Returns the path of the landed copy.
    """
    landed = root / "scripts" / "blind.sh"
    landed.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(BLIND, landed)
    landed.chmod(landed.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return landed


def _shim(root, name, body):
    """Write an executable `name` into `root`/.venv/bin carrying `body`."""
    path = root / ".venv" / "bin" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return path


def _tooling(root):
    """Give `root` a pytest shim and lint shims that always pass.

    The fixture checkout carries no virtualenv of its own. The lint shims are
    the fixture's always-passing gate, so what the `test` verb's exit status
    measures here is the test run and not a linter's opinion of the fixture.
    """
    _venv_shim(root)
    for name in ("ruff", "black", "eslint"):
        _shim(root, name, "#!/bin/sh\nexit 0\n")


def _blind(script, cwd, *args):
    """Run the landed blind.sh at `script` from inside `cwd`.

    Returns the CompletedProcess, so a caller may read either stdout or the
    exit status. Stderr is forwarded to the suite's own.
    """
    env = dict(os.environ)
    env.update(ENV)
    env["HOME"] = str(cwd)
    done = subprocess.run(
        [str(script), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    return done


def _opened_repo(fixture_root):
    """A fixture checkout carrying blind.sh, with its demo spec worktree open.

    Returns the checkout, its spec worktree and the landed blind.sh.
    """
    repo = _repo(fixture_root, BLOCK_NEW, REVIEWER)
    script = _install_blind(repo)
    (repo / "tests" / TARGET_NAME).write_text(PASSING)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "target")
    _pair(repo, "open", SLUG)
    tree = _worktree(repo)
    _tooling(repo)
    _tooling(tree)
    return repo, tree, script


def _test_verb_status(fixture_root, worktree_text, checkout_text):
    """Exit status of `blind.sh test <worktree path>` over the two copies given.

    The worktree's copy of the named file is written `worktree_text` and the
    main checkout's namesake `checkout_text`; the command text is the same in
    either case.
    """
    repo, tree, script = _opened_repo(fixture_root)
    (tree / "tests" / TARGET_NAME).write_text(worktree_text)
    (repo / "tests" / TARGET_NAME).write_text(checkout_text)
    return _blind(script, repo, "test", TARGET_ARG).returncode


@pytest.mark.parametrize(
    ("worktree_text", "checkout_text", "expected"),
    [
        (PASSING, FAILING, 0),
        (FAILING, PASSING, 1),
    ],
    ids=["worktree-copy-passes", "worktree-copy-fails"],
)
def test_test_verb_status_follows_the_worktree_copy_of_the_file_the_path_names(
    fixture_root, worktree_text, checkout_text, expected
):
    assert _test_verb_status(fixture_root, worktree_text, checkout_text) == expected


def _show_stdout_over_worktree(fixture_root, keep_worktree):
    """Stdout of `blind.sh show HEAD <slug>` where the spec branch diverged.

    The spec worktree commits BLOCK_V2 for the slug while the main checkout's
    HEAD keeps BLOCK_NEW. The worktree is removed again before the run unless
    `keep_worktree`.
    """
    repo, tree, script = _opened_repo(fixture_root)
    (tree / "gauntlet" / "specs" / "approved" / (SLUG + ".txt")).write_text(BLOCK_V2)
    _git(tree, "add", "-A")
    _git(tree, "commit", "-m", "diverged block")
    if not keep_worktree:
        _git(repo, "worktree", "remove", "--force", str(tree))
    return _blind(script, repo, "show", "HEAD", SLUG).stdout


@pytest.mark.parametrize(
    ("keep_worktree", "expected"),
    [
        (True, BLOCK_V2),
        (False, BLOCK_NEW),
    ],
    ids=["spec-worktree-on-disk", "spec-worktree-removed"],
)
def test_show_reads_the_spec_worktree_where_it_exists_and_the_checkout_where_it_does_not(
    fixture_root, keep_worktree, expected
):
    assert _show_stdout_over_worktree(fixture_root, keep_worktree) == expected


def _checkout(fixture_root, name, spec_text):
    """A minimal git checkout at fixture_root/`name` committing `spec_text` as the block."""
    approved = fixture_root / name / "gauntlet" / "specs" / "approved"
    approved.mkdir(parents=True)
    (approved / (SLUG + ".txt")).write_text(spec_text)
    root = fixture_root / name
    (root / ".gitignore").write_text(GITIGNORE)
    #: the declaration is the project's own and sits untracked under `.claude/`,
    #: exactly as it does in a real checkout
    (root / ".claude").mkdir(parents=True, exist_ok=True)
    (root / ".claude" / "blind-reads.json").write_text(
        json.dumps({"target_branch": TARGET, "gate_command": GATE})
    )
    _git(root, "init", "-b", "main")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "fixture")
    return root


def _installed_kit(fixture_root):
    """One installed copy of the kit, outside every fixture checkout."""
    kit = fixture_root / "kit"
    script = _install_blind(kit)
    (kit / "hooks").mkdir(parents=True, exist_ok=True)
    for module in HOOK_MODULES:
        shutil.copy2(module, kit / "hooks" / module.name)
    return script


def _show_stdout_from_checkout(fixture_root, name):
    """Stdout of the one installed blind.sh, run from inside checkout `name`.

    Two checkouts carry different committed texts for the same slug and neither
    carries a worktree for it.
    """
    _checkout(fixture_root, "alpha", BLOCK_NEW)
    _checkout(fixture_root, "bravo", BLOCK_V2)
    script = _installed_kit(fixture_root)
    return _blind(script, fixture_root / name, "show", "HEAD", SLUG).stdout


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("alpha", BLOCK_NEW),
        ("bravo", BLOCK_V2),
    ],
    ids=["run-inside-alpha", "run-inside-bravo"],
)
def test_show_reads_the_block_from_the_checkout_the_run_is_inside(fixture_root, name, expected):
    assert _show_stdout_from_checkout(fixture_root, name) == expected
