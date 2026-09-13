"""Behavior tests for the pair.sh spec-lane driver.

The stdout contracts asserted here are documented in docs/agents.md lines
31-42, so the literals are reachable without reading the implementation.
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
PAIR = REPO / "scripts" / "pair.sh"
EXCISION_DIFF = REPO / "scripts" / "excision-diff.py"

SLUG = "demo"

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


def _excision_body(target, assertion):
    return (
        "slug: demo\n"
        "kind: excision\n"
        "brief: none\n"
        "\n"
        f"1. excise {target}\n"
        "   rule: docs/testing.md rule 9\n"
        f"   assertion: {assertion}\n"
    )


BLOCK_NEW = _block(BODY_NEW)
BLOCK_WHOLE_FILE = _block(_excision_body("tests/test_b.py", ASSERTION_B))
BLOCK_SINGLE_TEST = _block(_excision_body("tests/test_a.py::test_x", ASSERTION_X))


def _git(cwd, *args):
    done = subprocess.run(
        ["git", *args], cwd=cwd, env=dict(ENV), capture_output=True, text=True
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
    (repo / "docs" / "gauntlet" / "specs").mkdir(parents=True)
    (repo / "docs" / "gauntlet" / "reviews").mkdir(parents=True)
    for source in (PAIR, EXCISION_DIFF):
        landed = repo / "scripts" / source.name
        shutil.copy2(source, landed)
        landed.chmod(landed.stat().st_mode | stat.S_IXUSR)
    (repo / "tests" / "test_a.py").write_text(TEST_A)
    (repo / "tests" / "test_b.py").write_text(TEST_B)
    (repo / "docs" / "gauntlet" / "specs" / "demo.txt").write_text(spec_text)
    (repo / "docs" / "gauntlet" / "reviews" / "demo.1.txt").write_text(review_text)
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
    )
    sys.stderr.write(done.stderr)
    return done.stdout.splitlines()


def _python_listing(directory):
    return {entry.name for entry in directory.iterdir() if entry.suffix == ".py"}


@pytest.mark.parametrize(
    "review_text,expected",
    [
        (REVIEWER, "OPEN .claude/worktrees/demo-spec"),
        (DIVERGED_REVIEWER, "MISMATCH docs/gauntlet/reviews/demo.1.txt"),
    ],
    ids=["reviewer-section-matches-round-file", "reviewer-section-differs"],
)
def test_open_reports_mismatch_only_where_the_round_file_text_differs(
    tmp_path, review_text, expected
):
    repo = _repo(tmp_path, BLOCK_NEW, review_text)
    assert _pair(repo, "open", SLUG)[:1] == [expected]


@pytest.mark.parametrize(
    "block,expected",
    [
        (BLOCK_WHOLE_FILE, {"test_a.py"}),
        (BLOCK_SINGLE_TEST, {"test_a.py", "test_b.py"}),
    ],
    ids=["whole-file-target", "single-test-target"],
)
def test_red_removes_whole_file_targets_and_keeps_single_test_target_files(
    tmp_path, block, expected
):
    repo = _repo(tmp_path, block, REVIEWER)
    _pair(repo, "open", SLUG)
    _venv_shim(_worktree(repo))
    _pair(repo, "red", SLUG)
    assert _python_listing(_worktree(repo) / "tests") == expected


@pytest.mark.parametrize(
    "block,expected",
    [
        (BLOCK_SINGLE_TEST, "OK tests/test_a.py::test_x"),
        (BLOCK_NEW, "TEST CHECK demo"),
    ],
    ids=["kind-excision", "kind-new"],
)
def test_merge_routes_to_the_mechanical_check_only_for_a_tests_only_kind(
    tmp_path, block, expected
):
    repo = _repo(tmp_path, block, REVIEWER)
    _pair(repo, "open", SLUG)
    worktree = _worktree(repo)
    (worktree / "tests" / "test_a.py").write_text(TEST_A_OTHER)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", "excise test_x")
    assert _pair(repo, "merge", SLUG)[:1] == [expected]


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

RED_TOKENS = (
    "test_alpha_passes",
    "test_alpha_fails",
    "test_bravo_passes",
    "test_bravo_fails",
    "assert 2 + 2 == 5",
    "assert 5 + 5 == 11",
)


def _red_text(tmp_path, suite):
    """Drive open then red over a repo carrying `suite` as its only test file.

    Returns the text of the repository's state/red/<slug>.txt, or the empty
    string where no such file was written.
    """
    repo = _repo(tmp_path, BLOCK_NEW, REVIEWER)
    (repo / "tests" / "test_a.py").unlink()
    (repo / "tests" / "test_b.py").unlink()
    (repo / "tests" / "test_suite.py").write_text(suite)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "single suite")
    _pair(repo, "open", SLUG)
    _venv_shim(_worktree(repo))
    _pair(repo, "red", SLUG)
    saved = repo / "state" / "red" / (SLUG + ".txt")
    return saved.read_text() if saved.is_file() else ""


@pytest.mark.parametrize(
    "suite,expected",
    [
        (
            ALPHA_SUITE,
            {"test_alpha_passes", "test_alpha_fails", "assert 2 + 2 == 5"},
        ),
        (
            BRAVO_SUITE,
            {"test_bravo_passes", "test_bravo_fails", "assert 5 + 5 == 11"},
        ),
    ],
    ids=["alpha-suite", "bravo-suite"],
)
def test_red_saves_output_naming_passing_and_failing_tests_of_the_suite_it_ran(
    tmp_path, suite, expected
):
    red_text = _red_text(tmp_path, suite)
    assert {token for token in RED_TOKENS if token in red_text} == expected
