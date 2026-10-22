"""Red tests for the suppression gate passing a `no_type_check` name not bound to the typing function.

Sources: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item (the ban is on the function, not its spelling: it covers `typing.no_type_check`
and `typing.no_type_check_decorator`, `typing_extensions` included, and any reference to
either is a finding, so the import line is a finding); first two items (a `# fmt: skip`
comment is a finding, seeded here so a file whose import is not a finding still carries
one known finding); and "Gates" (the count line `<gate>: N finding(s) in M Python file(s)`
is the last line a finished run prints).
"""

from pathlib import Path

import pytest

from gates.check_suppressions import main
from tests.support.suppressions import find_suppressions

ONE_FINDING_COUNT_LINE = "check_suppressions: 1 finding(s) in 1 Python file(s)"
TWO_FINDINGS_COUNT_LINE = "check_suppressions: 2 finding(s) in 1 Python file(s)"

PARAMETER_SOURCE = "value = 1  # fmt: skip\nfrom typing import no_type_check\n\n\ndef apply(no_type_check):\n    return no_type_check(apply)\n"
DECORATOR_PARAMETER_SOURCE = "value = 1  # fmt: skip\nfrom typing import no_type_check_decorator\n\n\ndef apply(no_type_check_decorator):\n    return no_type_check_decorator\n"
LOCAL_SOURCE = "from typing import no_type_check\n\n\ndef apply():\n    no_type_check = 1\n    return no_type_check\n"
COMPREHENSION_SOURCE = "from typing import no_type_check\n\nloose = [no_type_check for no_type_check in range(3)]\n"

SHADOWED_LINES = [
    (PARAMETER_SOURCE, [1, 2]),
    (DECORATOR_PARAMETER_SOURCE, [1, 2]),
    (LOCAL_SOURCE, [1]),
    (COMPREHENSION_SOURCE, [1]),
]

SHADOWED_COUNT_LINES = [
    (PARAMETER_SOURCE, TWO_FINDINGS_COUNT_LINE),
    (DECORATOR_PARAMETER_SOURCE, TWO_FINDINGS_COUNT_LINE),
    (LOCAL_SOURCE, ONE_FINDING_COUNT_LINE),
    (COMPREHENSION_SOURCE, ONE_FINDING_COUNT_LINE),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "shadowed.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "lines"), SHADOWED_LINES)
def test_name_that_shadows_the_typing_function_is_no_finding(
    tmp_path: Path, source: str, lines: list[int]
) -> None:
    """Report the seeded comment and the typing import, not a reference to a name a parameter, a local assignment in a function or a comprehension target has taken from the typing function."""
    path = _seed(tmp_path, source)

    assert sorted({finding.line for finding in find_suppressions(path)}) == lines


@pytest.mark.parametrize(("source", "count_line"), SHADOWED_COUNT_LINES)
def test_gate_does_not_count_a_name_that_shadows_the_typing_function(
    tmp_path: Path, source: str, count_line: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """Count the seeded comment and the typing import as the findings, not the shadowing name's references."""
    path = _seed(tmp_path, source)
    main([path])

    assert capsys.readouterr().out.splitlines()[-1] == count_line
