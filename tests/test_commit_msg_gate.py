"""Behavior tests for `scripts/gates/repo/commit-msg.py`'s stdin surface.

The gate reads a commit message from stdin under `-` and checks the subject
prefix against `CLAUDE.md`'s Commits list: `spec:`, `test:`, `feat:`, `fix:`,
`docs:`, `merge:`. Stdin carries no commit to diff, so the approved-spec-path
rule is out of reach here and is exercised instead by the gate's own
`--self-test` against `check_commit` directly.
"""

import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "gates" / "repo" / "commit-msg.py"


def _run(message: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "-"],
        input=message,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("prefix", ["spec:", "test:", "feat:", "fix:", "docs:", "merge:"])
def test_each_recognized_prefix_passes(prefix: str) -> None:
    assert _run(f"{prefix} a clean summary\n").returncode == 0


def test_an_unrecognized_prefix_fails() -> None:
    assert _run("tidy things up\n").returncode == 1


def test_a_prefix_word_without_its_colon_fails() -> None:
    assert _run("feature: add a thing\n").returncode == 1


def test_an_empty_message_fails() -> None:
    assert _run("").returncode == 1


def test_a_failing_message_names_the_recognized_prefixes_on_stdout() -> None:
    assert "spec:" in _run("tidy things up\n").stdout


def test_a_passing_message_prints_nothing() -> None:
    assert _run("fix: correct a thing\n").stdout == ""


def test_a_multiline_body_after_a_good_prefix_still_passes() -> None:
    assert _run("feat: add a thing\n\nA longer body line here.\n").returncode == 0


def test_a_prefix_that_is_only_a_substring_of_the_first_word_fails() -> None:
    assert _run("specs: approved block for foo\n").returncode == 1
