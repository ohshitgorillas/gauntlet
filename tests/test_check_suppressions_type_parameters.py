# Copyright 2026 oh shit, gorillas!
"""Red tests for the suppression gate's no_type_check ban against PEP 695 type parameters.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: a use of a name is a finding when any binding of that name, in the scope
Python's scoping rules resolve the use to, is `typing.no_type_check` or
`typing.no_type_check_decorator`; any reference to either function is a finding wherever
it appears, so the import line and the assignment line are each a finding; and the parse
uses the grammar of the pinned Python, 3.12, whose scoping rules resolve a use inside a
generic function, class or type alias to its type parameter, never to the enclosing
binding of the same name.

A type parameter is bound to a type variable, not to either function, so each use the
scoping rules resolve to one is no finding, while the enclosing binding that names the
function and any use resolved to that binding stay findings.
"""

from pathlib import Path

import pytest

from tests.support.suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check as marker",
            "",
            "",
            "def seeded[marker](value: marker) -> marker:",
            "    @marker",
            "    def inner() -> None:",
            "        pass",
            "",
            "    return value",
        ),
        [1],
        id="generic-function-annotations-and-body",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "marker = typing.no_type_check",
            "",
            "",
            "def seeded[marker](value: marker) -> marker:",
            "    return value",
            "",
            "",
            "@marker",
            "def unchecked() -> None:",
            "    pass",
        ),
        [3, 10],
        id="generic-function-beside-a-module-use-of-the-binding",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check as marker",
            "",
            "",
            "class Box[marker]:",
            "    item: marker",
            "",
            "    def method(self) -> marker:",
            "        @marker",
            "        def inner() -> None:",
            "            pass",
            "",
            "        return self.item",
        ),
        [1],
        id="generic-class-body-and-method",
    ),
    pytest.param(
        _source(
            "from typing_extensions import no_type_check_decorator as marker",
            "",
            "",
            "class Box[marker](list[marker]):",
            "    pass",
        ),
        [1],
        id="generic-class-bases",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check as marker",
            "",
            "type Alias[marker] = list[marker]",
        ),
        [1],
        id="generic-type-alias",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "",
            "def outer() -> None:",
            "    marker = typing.no_type_check",
            "",
            "    def seeded[marker](value: marker) -> marker:",
            "        @marker",
            "        def inner() -> None:",
            "            pass",
            "",
            "        return value",
        ),
        [5],
        id="enclosing-function-binds-the-name",
    ),
]


@pytest.mark.parametrize(("source", "finding_lines"), SOURCES)
def test_use_resolved_to_a_type_parameter_is_no_reference(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the enclosing reference lines and no use the scoping rules resolve to a type parameter."""
    path = tmp_path / "type_parameters.py"
    path.write_text(source, encoding="utf-8")

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
