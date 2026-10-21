"""Red tests for the mutation gate's entry and outcome on the gates core.

Source: the quality gates design spec under docs/superpowers/specs/, "Tests", the "Mutation testing blocks" bullet,
and "Gates", intro, for the empty run, the pin and the count line; the gates core design spec, section 1, project.py
(`key_findings`' line) and section 2, "mutmut (G4) and the backstop".

A run given no Python file that is not a test file prints that nothing was checked, then the count line for no file,
and exits 1. A tree with no `major.minor` pyright `pythonVersion` is unfinished: an error naming the key, then the count
line over the given non-test files, exit 2. A `[tool.mutmut]` key that narrows or widens the scope, or changes mutmut's
own time limit, is a finding naming the key. A finding is the path as given, mutmut's name, its status, then mutmut's
diff with every line break a space, in order of path then name. At the wall-clock cap every unchecked mutant is a
finding and the run exits 1; any other unfinished run prints the checker's error, then every finding, then the count
line, and exits 2.
"""

from pathlib import Path

import pytest

from gates.check_mutation import GATE, Mutant, Mutated, outcome, setting_findings
from gates.core.report import Finding, exit_code, render
from gates.core.runner import run_gate
from tests.support.capture import captured
from tests.support.fake import FakeRunner
from tests.support.project import scaffold

PASSING_TEST = "def test_seeded():\n    pass\n"

CONFTEST = "def pytest_configure(config):\n    pass\n"

SOURCE = "def seeded():\n    return 1\n"

EMPTY_RUNS = [
    pytest.param((), id="none"),
    pytest.param((("tests/test_x.py", PASSING_TEST),), id="test"),
    pytest.param((("tests/x_test.py", PASSING_TEST),), id="sfx"),
    pytest.param((("tmp/tests/test_x.py", PASSING_TEST),), id="nest"),
    pytest.param(
        (("tests/test_x.py", PASSING_TEST), ("tests/conftest.py", CONFTEST)), id="conf"
    ),
    pytest.param((("src/seeded.pyw", SOURCE),), id="pyw"),
    pytest.param((("src/runner", "#!/bin/sh\necho seeded\n"),), id="sh"),
    pytest.param((("src/notes.md", "seeded\n"),), id="md"),
    pytest.param(
        (("tests/test_x.py", PASSING_TEST), ("src/seeded.pyw", SOURCE)), id="mix"
    ),
]

STRICT = '[tool.pyright]\ntypeCheckingMode = "strict"\n'

UNPINNED = [
    pytest.param('[tool.mypy]\npython_version = "3.12"\n', id="table"),
    pytest.param(STRICT, id="nokey"),
    pytest.param(STRICT + '\n[tool.mypy]\npythonVersion = "3.12"\n', id="mypy"),
    pytest.param(STRICT + 'pythonVersion = "3"\n', id="major"),
    pytest.param(STRICT + 'pythonVersion = "3.12.0"\n', id="micro"),
    pytest.param(STRICT + 'pythonVersion = "py312"\n', id="py312"),
    pytest.param(STRICT + 'pythonVersion = "3.x"\n', id="x"),
    pytest.param(STRICT + 'pythonVersion = ""\n', id="empty"),
    pytest.param(STRICT + "pythonVersion = 312\n", id="int"),
]

PINNED = STRICT + 'pythonVersion = "3.12"\n'

SETTING_KEYS = [
    "paths_to_mutate",
    "tests_dir",
    "also_copy",
    "timeout_multiplier",
    "timeout_constant",
]

DIFF = "--- seeded.py\n+++ seeded.py\n@@ -1,2 +1,2 @@\n def seeded():\n-    return 1\n+    return 2\n"

ONE_LINE_DIFF = "--- seeded.py +++ seeded.py @@ -1,2 +1,2 @@  def seeded(): -    return 1 +    return 2 "

SURVIVOR = Mutant(
    given="src/seeded.py",
    name="seeded.x_seeded__mutmut_1",
    status="survived",
    diff=DIFF,
)

UNREACHED = Mutant(
    given="src/b.py", name="b.x_b__mutmut_1", status="no tests", diff=DIFF
)

LATER = Mutant(
    given="src/seeded.py",
    name="seeded.x_seeded__mutmut_2",
    status="survived",
    diff=DIFF,
)

AT_THE_CAP = Mutant(
    given="src/seeded.py",
    name="seeded.x_seeded__mutmut_1",
    status="unchecked at the cap",
    diff=DIFF,
)

KEY_FINDING = Finding("pyproject.toml: tool.mutmut.tests_dir: seeded")


def _line(mutant: Mutant) -> str:
    return f"{mutant.given} {mutant.name} {mutant.status}: {ONE_LINE_DIFF}"


def _count(findings: int, files: int) -> str:
    return f"check_mutation: {findings} finding(s) in {files} Python file(s)"


@pytest.mark.parametrize("files", EMPTY_RUNS)
def test_empty_run(tmp_path: Path, files: tuple[tuple[str, str], ...]) -> None:
    """A run given no Python file that is not a test file prints that nothing was checked, then its count line: exit 1."""
    project = scaffold(tmp_path, dict(files))
    paths = [tmp_path / relative for relative, _ in files]

    output = captured(
        lambda: run_gate(GATE, paths, project=project, process=FakeRunner([]))
    )

    assert (output.result, output.merged) == (
        1,
        [
            f"check_mutation: nothing checked: no Python file that is not a test file among the {len(paths)} file(s) given\n",
            f"{_count(0, 0)}\n",
        ],
    )


@pytest.mark.parametrize("pyproject", UNPINNED)
def test_unpinned(tmp_path: Path, pyproject: str) -> None:
    """A tree with no `major.minor` pyright pythonVersion prints one error naming the key and the file, then its count line: exit 2."""
    files = {"seeded.py": SOURCE, "tests/test_seeded.py": PASSING_TEST}
    project = scaffold(tmp_path, files, pyproject=pyproject)
    paths = [tmp_path / name for name in files]

    output = captured(
        lambda: run_gate(GATE, paths, project=project, process=FakeRunner([]))
    )

    assert (
        output.result,
        len(output.merged),
        "pythonVersion" in output.merged[0],
        "tool.pyright.pythonVersion" in output.merged[0],
        "pyproject.toml" in output.merged[0],
        output.merged[-1],
    ) == (
        2,
        2,
        True,
        True,
        True,
        f"{_count(0, 1)}\n",
    )


@pytest.mark.parametrize("key", SETTING_KEYS)
def test_setting_key(tmp_path: Path, key: str) -> None:
    """A `[tool.mutmut]` key that narrows or widens the scope or changes the time limit is one finding naming the key."""
    project = scaffold(
        tmp_path, {}, pyproject=f'{PINNED}\n[tool.mutmut]\n{key} = ["src"]\n'
    )

    findings = setting_findings(project)

    assert [
        finding.text.startswith(f"pyproject.toml: tool.mutmut.{key}: ")
        for finding in findings
    ] == [True]


def test_no_setting_key(tmp_path: Path) -> None:
    """A `[tool.mutmut]` table holding no such key makes no finding."""
    project = scaffold(
        tmp_path, {}, pyproject=f"{PINNED}\n[tool.mutmut]\ndebug = true\n"
    )

    assert setting_findings(project) == []


def test_finished_clean() -> None:
    """A finished run with no mutant left and no key finding prints only its count line: exit 0."""
    done = outcome([], Mutated())

    assert (exit_code(done), render(GATE.name, done, 2)) == (0, [_count(0, 2)])


def test_finished_findings_in_order() -> None:
    """The key finding, and each mutant not killed by path as given then name, one line each with its diff: exit 1."""
    done = outcome([KEY_FINDING], Mutated(mutants=(LATER, SURVIVOR, UNREACHED)))

    lines = render(GATE.name, done, 2)

    assert (
        exit_code(done),
        len(lines),
        KEY_FINDING.text in lines,
        [line for line in lines if line != KEY_FINDING.text],
    ) == (
        1,
        5,
        True,
        [
            _line(UNREACHED),
            _line(SURVIVOR),
            _line(LATER),
            _count(4, 2),
        ],
    )


def test_at_the_cap() -> None:
    """At the wall-clock cap, the gate's line naming the cap, then each unchecked mutant as a finding: exit 1."""
    done = outcome([], Mutated(mutants=(AT_THE_CAP,), at_cap=True))

    assert (exit_code(done), render(GATE.name, done, 1)) == (
        1,
        [
            "check_mutation: mutmut hit the wall-clock cap of 600 seconds; every mutant it had not checked is a finding",
            _line(AT_THE_CAP),
            _count(1, 1),
        ],
    )


def test_unfinished() -> None:
    """A run the checker did not finish prints its error, then every finding, then the count line: exit 2."""
    error = "mutmut exited 1\nFAILED tests/test_seeded.py::test_seeded"

    done = outcome([KEY_FINDING], Mutated(mutants=(SURVIVOR,), error=error))

    lines = render(GATE.name, done, 1)

    assert (exit_code(done), lines[:2], sorted(lines[2:-1]), lines[-1]) == (
        2,
        [
            "mutmut exited 1",
            "FAILED tests/test_seeded.py::test_seeded",
        ],
        sorted([KEY_FINDING.text, _line(SURVIVOR)]),
        _count(2, 1),
    )
