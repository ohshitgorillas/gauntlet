"""Red tests for the suppression gate's no_type_check ban through for targets.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: a use of a name is a finding when any binding of that name, in the scope
Python's scoping rules resolve the use to, is `typing.no_type_check` or
`typing.no_type_check_decorator`, `typing_extensions` included, and a `for` target
that takes either function as its value is a binding that is the function. Any
reference to either function is a finding wherever it appears, so the import line and
the line whose `for` iterable names the function are findings too, and a line with no
reference and no use of a bound name is not one.

Each seeded use spells only the bound name, never `no_type_check`, so only the gate's
resolution of names can report its line.
"""

from pathlib import Path

import pytest

from tests.support.suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


FOR_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "for loose in [no_type_check]:",
            "    pass",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 3, 7],
        id="for-over-a-list-holding-the-function",
    ),
    pytest.param(
        _source(
            "from typing_extensions import no_type_check_decorator",
            "",
            "for loose in (print, no_type_check_decorator):",
            "    pass",
            "",
            "",
            "unchecked = loose(print)",
        ),
        [1, 3, 7],
        id="for-over-a-tuple-where-a-later-item-is-the-decorator-function",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            'for label, loose in [("seeded", no_type_check)]:',
            "    pass",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 3, 7],
        id="for-target-unpacked-from-a-pair",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "for loose in [typing.no_type_check]:",
            "    pass",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [3, 7],
        id="for-over-the-module-attribute",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "",
            "def outer() -> None:",
            "    for loose in [no_type_check]:",
            "        pass",
            "",
            "    @loose",
            "    def seeded() -> None:",
            "        pass",
        ),
        [1, 5, 8],
        id="for-target-in-a-function-scope",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "checks = [",
            "    loose",
            "    for loose in [no_type_check]",
            "]",
        ),
        [1, 4, 5],
        id="comprehension-for-target",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "captured.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "finding_lines"), FOR_SOURCES)
def test_for_target_taking_the_function_reaches_the_use(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the import line, the for line that names the function and the use line, each once and nothing else."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
