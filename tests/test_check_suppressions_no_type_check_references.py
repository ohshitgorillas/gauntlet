"""Red tests for the suppression gate's finding on every reference to `no_type_check`.

Sources: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item (the ban is on the function, not its spelling: it covers `typing.no_type_check`
and `typing.no_type_check_decorator`, `typing_extensions` included, and any reference to
either is a finding wherever it appears: imported, bound to another name, used as a
decorator or called, so the import line and the assignment line are each a finding); and
"Gates" (exit 1 with one or more findings; the count line
`<gate>: N finding(s) in M Python file(s)` is the last line a finished run prints).
"""

from pathlib import Path

import pytest

from gates.check_suppressions import main
from tests.support.suppressions import find_suppressions

FINDINGS_STATUS = 1
ASSIGNMENT_LINE = 2

REFERENCE_SOURCES = [
    ("from typing import no_type_check\n", [1]),
    ("from typing_extensions import no_type_check_decorator as nocheck\n", [1]),
    (
        "from typing import Any, no_type_check\n\n\ndef seeded(value: Any) -> Any:\n    return value\n",
        [1],
    ),
    ("from typing import no_type_check\nloose = no_type_check\n", [1, 2]),
    ("from typing import no_type_check\n\nloose: object = no_type_check\n", [1, 3]),
    ("from typing_extensions import no_type_check\nloose = no_type_check\n", [1, 2]),
    (
        "from typing import no_type_check\nloose = no_type_check\n\n\n@loose\ndef seeded() -> None:\n    pass\n",
        [1, 2, 5],
    ),
    (
        "from typing import no_type_check_decorator\nchecks = [no_type_check_decorator]\n",
        [1, 2],
    ),
    (
        "from typing import no_type_check\n\n\ndef register(func):\n    return func\n\n\nregister(no_type_check)\n",
        [1, 8],
    ),
    (
        "from typing import no_type_check\n\n\ndef build():\n    return no_type_check\n",
        [1, 5],
    ),
]

MODULE_ATTRIBUTE_SOURCES = [
    "import typing\nloose = typing.no_type_check\n",
    "import typing as t\nloose = t.no_type_check_decorator\n",
    "import typing_extensions as te\nnocheck = te.no_type_check_decorator\n",
]

IMPORT_ONLY_SOURCE = "from typing import no_type_check\n"
IMPORT_AND_ASSIGNMENT_SOURCE = (
    "from typing import no_type_check\nloose = no_type_check\n"
)
ONE_FINDING_COUNT_LINE = "check_suppressions: 1 finding(s) in 1 Python file(s)"
TWO_FINDINGS_COUNT_LINE = "check_suppressions: 2 finding(s) in 1 Python file(s)"


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "seeded.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "lines"), REFERENCE_SOURCES)
def test_every_line_referencing_no_type_check_is_a_finding(
    tmp_path: Path, source: str, lines: list[int]
) -> None:
    """Report the import line, the assignment line and every other line that references the function."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == lines


@pytest.mark.parametrize("source", MODULE_ATTRIBUTE_SOURCES)
def test_assignment_of_the_module_attribute_is_a_finding(
    tmp_path: Path, source: str
) -> None:
    """Report the line that binds the function, reached as a module attribute, to another name, and not the line that imports the module."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == [
        ASSIGNMENT_LINE
    ]


def test_gate_exits_with_findings_status_on_a_bare_import(tmp_path: Path) -> None:
    """Exit with the findings status on a file whose only reference is the import."""
    path = _seed(tmp_path, IMPORT_ONLY_SOURCE)

    assert main([path]) == FINDINGS_STATUS


@pytest.mark.parametrize("source", MODULE_ATTRIBUTE_SOURCES)
def test_gate_exits_with_findings_status_on_an_attribute_assignment(
    tmp_path: Path, source: str
) -> None:
    """Exit with the findings status on a file that binds the function to another name."""
    path = _seed(tmp_path, source)

    assert main([path]) == FINDINGS_STATUS


def test_gate_counts_a_bare_import_as_one_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Count the import line of the function as one finding in the gate's count line."""
    path = _seed(tmp_path, IMPORT_ONLY_SOURCE)
    main([path])

    assert capsys.readouterr().out.splitlines()[-1] == ONE_FINDING_COUNT_LINE


def test_gate_counts_import_and_assignment_lines_as_two_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Count the import line and the assignment line each as a finding in the gate's count line."""
    path = _seed(tmp_path, IMPORT_AND_ASSIGNMENT_SOURCE)
    main([path])

    assert capsys.readouterr().out.splitlines()[-1] == TWO_FINDINGS_COUNT_LINE
