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
    (repo / "gauntlet" / "specs" / "approved").mkdir(parents=True)
    (repo / "gauntlet" / "reviews").mkdir(parents=True)
    for source in (PAIR, EXCISION_DIFF):
        landed = repo / "scripts" / source.name
        shutil.copy2(source, landed)
        landed.chmod(landed.stat().st_mode | stat.S_IXUSR)
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
    )
    sys.stderr.write(done.stderr)
    return done.stdout.splitlines()


def _python_listing(directory):
    return {entry.name for entry in directory.iterdir() if entry.suffix == ".py"}


@pytest.mark.parametrize(
    "review_text,expected",
    [
        (REVIEWER, "OPEN .claude/worktrees/demo-spec"),
        (DIVERGED_REVIEWER, "MISMATCH gauntlet/reviews/demo.1.txt"),
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


TEST_A_BASE = "def test_x():\n    " + ASSERTION_X + "\n"
TEST_B_TWO = "def test_b_two():\n    assert 7 + 7 == 14\n"
TEST_B_GREW = TEST_B + "\n\n" + TEST_B_TWO

MERGE_ARTIFACT = "state/merge/" + SLUG + ".txt"
MERGE_HEADINGS = ("test files:", "diff:", "red output:")

BRIEF_NEW = ("TEST CHECK demo", "merge output: " + MERGE_ARTIFACT, "END TEST CHECK", 5)
BRIEF_EXCISION = (
    "OK tests/test_a.py::test_x",
    None,
    "OK tests/test_a.py::test_x",
    1,
)

DIFF_TOKENS = ("+def test_b_two():", "+def test_a_other():")
NAME_TOKENS = ("tests/test_a.py", "tests/test_b.py")
MERGE_RED_TOKENS = ("test_alpha_fails", "test_bravo_fails")


def _brief_shape(lines):
    """Project `pair.sh merge` stdout onto the marker lines docs/agents.md:46 names.

    Returns the first line, the fourth line (None where stdout is shorter than
    four lines), the last line, and how many lines were printed.
    """
    if not lines:
        return (None, None, None, 0)
    return (lines[0], lines[3] if len(lines) > 3 else None, lines[-1], len(lines))


def _section(text, heading):
    """Return the body under `heading` in a state/merge/<slug>.txt artifact.

    The three headings and their order are documented at docs/agents.md line 48.
    Returns None where the artifact carries no line naming that heading.
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if line.strip() == heading:
            start = index + 1
            break
    if start is None:
        return None
    body = []
    for line in lines[start:]:
        if line.strip() in MERGE_HEADINGS:
            break
        body.append(line)
    return "\n".join(body)


def _red_section_marks(text):
    """Classify the `red output:` section of a merge artifact by what it names.

    Returns `("no heading",)` where the section is missing, `("empty",)` where it
    carries no content, and otherwise the failing-test names of the fixture
    suites that appear in it, sorted.
    """
    body = _section(text, "red output:")
    if body is None:
        return ("no heading",)
    if not body.strip():
        return ("empty",)
    return tuple(sorted(token for token in MERGE_RED_TOKENS if token in body))


def _merge(tmp_path, changes, base=None, suite=None, block=BLOCK_NEW):
    """Drive open, an optional red run, a test commit and merge for the demo slug.

    `base` maps a name under tests/ to its text in the repository before the
    worktree is cut; `changes` maps a name under tests/ to its text in the spec
    worktree, and those are the files the merge sees change. `suite` is the text
    of an extra tests/test_suite.py, whose red run is saved to state/red, or None
    to leave no saved red log. Returns the stdout lines of `pair.sh merge` and
    the text of state/merge/<slug>.txt, empty where no such file was written.
    """
    repo = _repo(tmp_path, block, REVIEWER)
    for name, text in (base or {}).items():
        (repo / "tests" / name).write_text(text)
    if suite is not None:
        (repo / "tests" / "test_suite.py").write_text(suite)
    if base or suite is not None:
        _git(repo, "add", "-A")
        _git(repo, "commit", "-m", "base tests")
    _pair(repo, "open", SLUG)
    worktree = _worktree(repo)
    for name, text in changes.items():
        (worktree / "tests" / name).write_text(text)
    _git(worktree, "add", "-A")
    _git(worktree, "commit", "-m", "spec tests")
    if suite is not None:
        _venv_shim(worktree)
        _pair(repo, "red", SLUG)
    lines = _pair(repo, "merge", SLUG)
    artifact = repo / "state" / "merge" / (SLUG + ".txt")
    return lines, artifact.read_text() if artifact.is_file() else ""


@pytest.mark.parametrize(
    "block,changes,suite,expected",
    [
        (BLOCK_SINGLE_TEST, {"test_a.py": TEST_A_OTHER}, None, BRIEF_EXCISION),
        (BLOCK_NEW, {"test_a.py": TEST_A_OTHER}, None, BRIEF_NEW),
        (
            BLOCK_NEW,
            {"test_a.py": TEST_A_OTHER, "test_b.py": TEST_B_GREW},
            ALPHA_SUITE,
            BRIEF_NEW,
        ),
    ],
    ids=["kind-excision", "kind-new-one-file", "kind-new-two-files-and-a-red-log"],
)
def test_merge_prints_the_five_line_brief_for_kind_new_whatever_it_merged(
    tmp_path, block, changes, suite, expected
):
    lines, _ = _merge(tmp_path, changes, suite=suite, block=block)
    assert _brief_shape(lines) == expected


@pytest.mark.parametrize(
    "changes,expected",
    [
        ({"test_b.py": TEST_B_GREW}, {"+def test_b_two():"}),
        ({"test_a.py": TEST_A}, {"+def test_a_other():"}),
    ],
    ids=["diff-adds-test-b-two", "diff-adds-test-a-other"],
)
def test_merge_artifact_diff_section_carries_the_lines_that_merge_added(
    tmp_path, changes, expected
):
    _, artifact = _merge(tmp_path, changes, base={"test_a.py": TEST_A_BASE})
    body = _section(artifact, "diff:") or ""
    assert {token for token in DIFF_TOKENS if token in body} == expected


@pytest.mark.parametrize(
    "changes,expected",
    [
        (
            {"test_a.py": TEST_A, "test_b.py": TEST_B_GREW},
            {"tests/test_a.py", "tests/test_b.py"},
        ),
        ({"test_a.py": TEST_A}, {"tests/test_a.py"}),
    ],
    ids=["two-files-changed", "one-file-changed"],
)
def test_merge_artifact_test_files_section_names_the_files_the_merge_changed(
    tmp_path, changes, expected
):
    _, artifact = _merge(tmp_path, changes, base={"test_a.py": TEST_A_BASE})
    body = _section(artifact, "test files:") or ""
    assert {name for name in NAME_TOKENS if name in body} == expected


@pytest.mark.parametrize(
    "suite,expected",
    [
        (ALPHA_SUITE, ("test_alpha_fails",)),
        (BRAVO_SUITE, ("test_bravo_fails",)),
        (None, ("empty",)),
    ],
    ids=["alpha-suite-red-log", "bravo-suite-red-log", "no-red-log-on-disk"],
)
def test_merge_artifact_red_output_section_carries_the_red_run_on_disk(
    tmp_path, suite, expected
):
    _, artifact = _merge(tmp_path, {"test_a.py": TEST_A_OTHER}, suite=suite)
    assert _red_section_marks(artifact) == expected
