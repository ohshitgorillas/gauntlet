"""Behavior tests for the strike-diff reporter CLI."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "strike-diff.py"

ASSERTION = 'assert banner() == "no rows to show"'

SIBLING = (
    "import pytest\n"
    "\n"
    "\n"
    '@pytest.mark.parametrize("n", [1, 2])\n'
    "def test_y(n):\n"
    "    " + ASSERTION + "\n"
)
TEST_X_WITH_ASSERTION = "\n\ndef test_x():\n    " + ASSERTION + "\n"
TEST_X_REWRITTEN = "\n\ndef test_x():\n    assert banner_kind() == 1\n"
TEST_X_RENAMED = "\n\ndef test_x_renamed():\n    assert banner_kind() == 1\n"

ALTERED_ASSERTION = 'assert banner() == "nothing here"'
TEST_X_ALTERED = "\n\ndef test_x():\n    " + ALTERED_ASSERTION + "\n"
TEST_X_ALTERED_ALONE = "def test_x():\n    " + ALTERED_ASSERTION + "\n"

BASE_TEST_A = SIBLING + TEST_X_WITH_ASSERTION
BASE_TEST_B = "def test_b_one():\n    assert widget_count() == 3\n"
CHANGED_TEST_B = "def test_b_one():\n    assert widget_count() == 4\n"

HEADER = "slug: fixture-block\nmotion: strike\nbrief: none\n\n"

BLOCK_TEST_X = HEADER + (
    "1. strike tests/test_a.py::test_x\n"
    "   rule: docs/testing.md rule 9\n"
    "   assertion: " + ASSERTION + "\n"
)
BLOCK_TEST_X_AS_RENAMED = HEADER + (
    "1. strike tests/test_a.py::test_x\n"
    "   as: tests/test_a.py::test_x_renamed\n"
    "   rule: docs/testing.md rule 9\n"
    "   assertion: " + ASSERTION + "\n"
)
BLOCK_TEST_B_WHOLE = HEADER + (
    "1. strike tests/test_b.py\n"
    "   rule: docs/testing.md rule 9\n"
    "   assertion: assert widget_count() == 3\n"
)

#: a `kind: new` block carrying one collateral row: the `collateral:` line at
#: column zero beneath the behavior lines, the row itself, and the row's two
#: fields indented two spaces under it
COLLATERAL_BLOCK = (
    "slug: fixture-block\n"
    "kind: new\n"
    "brief: none\n"
    "\n"
    "1. The banner names the rows it has, and says so plainly where it has none.\n"
    "   kills: prints the same banner whatever rows it was handed\n"
    "   bite: null stub fails at both inputs (surface new)\n"
    "   existing: none\n"
    "\n"
    "collateral:\n"
    "- tests/test_a.py::test_x\n"
    "  breaks: the keyword the helper passes was renamed\n"
    "  assertion: " + ASSERTION + "\n"
)


def _git(repo, *args):
    env = {
        "PATH": os.environ.get("PATH", ""),
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_AUTHOR_NAME": "Fixture",
        "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
        "GIT_COMMITTER_NAME": "Fixture",
        "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
    }
    done = subprocess.run(
        ["git", *args], cwd=repo, env=env, capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        raise RuntimeError("git " + " ".join(args) + " failed: " + done.stderr)
    return done.stdout.strip()


def _commit(repo, files):
    tests_dir = repo / "tests"
    if tests_dir.exists():
        for stale in tests_dir.iterdir():
            stale.unlink()
    else:
        tests_dir.mkdir(parents=True)
    for name, text in files.items():
        (tests_dir / name).write_text(text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "--allow-empty", "-m", "fixture")
    return _git(repo, "rev-parse", "HEAD")


def _repo(tmp_path, head_files):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    base = _commit(repo, {"test_a.py": BASE_TEST_A, "test_b.py": BASE_TEST_B})
    head = _commit(repo, head_files)
    return repo, base, head


def _report(tmp_path, block, repo, base, head):
    spec = tmp_path / "block.txt"
    spec.write_text(block)
    done = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--spec",
            str(spec),
            "--base",
            base,
            "--head",
            head,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    return done.stdout.splitlines()


def _status_for(lines, target):
    hits = [line.strip() for line in lines if line.split()[-1:] == [target]]
    if len(hits) != 1:
        return "<no single stdout line for " + target + ">"
    return hits[0]


@pytest.mark.parametrize(
    ("head_test_a", "expected"),
    [
        (SIBLING, "OK tests/test_a.py::test_x"),
        (BASE_TEST_A, "UNSATISFIED tests/test_a.py::test_x"),
    ],
    ids=["target-removed", "target-and-assertion-kept"],
)
def test_target_unsatisfied_only_while_its_assertion_survives_in_its_body(
    tmp_path, head_test_a, expected
):
    repo, base, head = _repo(tmp_path, {"test_a.py": head_test_a, "test_b.py": BASE_TEST_B})
    lines = _report(tmp_path, BLOCK_TEST_X, repo, base, head)
    assert _status_for(lines, "tests/test_a.py::test_x") == expected


def test_assertion_left_in_a_sibling_test_does_not_hold_the_target_open(tmp_path):
    repo, base, head = _repo(
        tmp_path,
        {"test_a.py": SIBLING + TEST_X_REWRITTEN, "test_b.py": BASE_TEST_B},
    )
    lines = _report(tmp_path, BLOCK_TEST_X, repo, base, head)
    assert _status_for(lines, "tests/test_a.py::test_x") == "OK tests/test_a.py::test_x"


@pytest.mark.parametrize(
    ("block", "expected"),
    [
        (BLOCK_TEST_B_WHOLE, "UNSATISFIED tests/test_b.py"),
        (BLOCK_TEST_X, "UNNAMED tests/test_b.py"),
    ],
    ids=["named-whole-file", "named-by-no-line"],
)
def test_changed_test_file_is_unnamed_only_when_no_block_line_names_it(tmp_path, block, expected):
    repo, base, head = _repo(tmp_path, {"test_a.py": SIBLING, "test_b.py": CHANGED_TEST_B})
    lines = _report(tmp_path, block, repo, base, head)
    assert _status_for(lines, "tests/test_b.py") == expected


def _collateral_report(tmp_path, block, repo, base, head):
    """Whole stdout of a `--collateral` run over `block`, as a list of lines."""
    spec = tmp_path / "collateral-block.txt"
    spec.write_text(block)
    done = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--collateral",
            "--spec",
            str(spec),
            "--base",
            base,
            "--head",
            head,
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    sys.stderr.write(done.stderr)
    return done.stdout.splitlines()


@pytest.mark.parametrize(
    ("head_test_a", "expected"),
    [
        (SIBLING + TEST_X_WITH_ASSERTION, ["OK tests/test_a.py::test_x"]),
        (SIBLING + TEST_X_ALTERED, ["ALTERED tests/test_a.py::test_x"]),
    ],
    ids=["body-carries-the-assertion", "sibling-carries-it-instead"],
)
def test_collateral_row_reads_its_assertion_in_the_targets_own_body(
    tmp_path, head_test_a, expected
):
    # test_b.py changes across the diff and no row names it, so a `--collateral`
    # run that swept the diff would carry a second line here
    repo, base, head = _repo(tmp_path, {"test_a.py": head_test_a, "test_b.py": CHANGED_TEST_B})
    assert _collateral_report(tmp_path, COLLATERAL_BLOCK, repo, base, head) == expected


@pytest.mark.parametrize(
    ("head_test_a", "expected"),
    [
        (SIBLING, ["MISSING tests/test_a.py::test_x"]),
        (TEST_X_ALTERED_ALONE, ["ALTERED tests/test_a.py::test_x"]),
    ],
    ids=["target-gone-from-the-file", "target-still-there-rewritten"],
)
def test_collateral_row_whose_target_is_gone_is_missing_rather_than_altered(
    tmp_path, head_test_a, expected
):
    repo, base, head = _repo(tmp_path, {"test_a.py": head_test_a, "test_b.py": CHANGED_TEST_B})
    assert _collateral_report(tmp_path, COLLATERAL_BLOCK, repo, base, head) == expected


@pytest.mark.parametrize(
    ("head_test_a", "expected"),
    [
        (SIBLING + TEST_X_RENAMED, "OK tests/test_a.py::test_x_renamed"),
        (SIBLING, "MISSING tests/test_a.py::test_x_renamed"),
    ],
    ids=["replacement-present", "replacement-absent"],
)
def test_replacement_named_by_as_is_missing_only_where_head_lacks_it(
    tmp_path, head_test_a, expected
):
    repo, base, head = _repo(tmp_path, {"test_a.py": head_test_a, "test_b.py": BASE_TEST_B})
    lines = _report(tmp_path, BLOCK_TEST_X_AS_RENAMED, repo, base, head)
    assert _status_for(lines, "tests/test_a.py::test_x_renamed") == expected
