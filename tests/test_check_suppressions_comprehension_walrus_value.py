# Copyright 2026 oh shit, gorillas!
"""Red tests for the scope an assignment expression's value is read in, inside a comprehension.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: any reference to `typing.no_type_check` or `typing.no_type_check_decorator`,
`typing_extensions` included, is a finding wherever it appears, so the import line and
the line whose comprehension iterable names the function are each a finding. A use of a
name is a finding when any binding of that name, in the scope Python's scoping rules
resolve the use to, is either function; a `for` target of a comprehension whose iterable
is a list, tuple or set display written in place takes the item its position reaches.
Python's scoping rules read the value of an assignment expression inside a comprehension
in the comprehension's own scope, while its target is bound in the nearest enclosing
scope that is not a comprehension. So a name only the comprehension binds to the function
gives the target the function, and a use of that target is a finding; a name the
comprehension binds to something else shadows an enclosing binding of the function, and
the target's use is then no finding.

Each seeded use of the target spells only the bound name, never `no_type_check`, so only
the gate's resolution of names can report its line.
"""

from pathlib import Path

import pytest

from tests.support.suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "checks = [",
            "    (loose := checked)",
            "    for checked in [no_type_check]",
            "]",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 4, 5, 9],
        id="value-names-the-comprehension-target",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "checks = [",
            "    (loose := checked)",
            "    for checked in (print, typing.no_type_check)",
            "]",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [4, 5, 9],
        id="comprehension-target-over-the-module-attribute",
    ),
    pytest.param(
        _source(
            "from typing_extensions import no_type_check_decorator",
            "",
            "checks = {",
            "    (loose := checked)",
            "    for checked in {no_type_check_decorator}",
            "}",
            "",
            "",
            "unchecked = loose(print)",
        ),
        [1, 4, 5, 9],
        id="set-comprehension-over-the-decorator-function",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "checked = print",
            "checks = [",
            "    (loose := checked)",
            "    for checked in [no_type_check]",
            "]",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 5, 6, 10],
        id="comprehension-target-shadows-an-enclosing-binding-of-another-value",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "",
            "def outer() -> None:",
            "    checks = [",
            "        (loose := checked)",
            "        for checked in [no_type_check]",
            "    ]",
            "",
            "    @loose",
            "    def seeded() -> None:",
            "        pass",
        ),
        [1, 6, 7, 10],
        id="comprehension-in-a-function-scope",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "checks = [",
            "    [(loose := checked) for _ in range(1)]",
            "    for checked in [no_type_check]",
            "]",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 4, 5, 9],
        id="inner-comprehension-value-names-the-outer-target",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "checked = no_type_check",
            "checks = [",
            "    (loose := checked)",
            "    for checked in [print]",
            "]",
            "",
            "",
            "unchecked = loose(print)",
        ),
        [1, 3],
        id="comprehension-target-shadows-an-enclosing-binding-of-the-function",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "walrus_value.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "finding_lines"), SOURCES)
def test_assignment_expression_value_is_read_in_the_comprehension_scope(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the import line, each reference to the function and each use the scoping rules resolve to it, each once and nothing else."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
