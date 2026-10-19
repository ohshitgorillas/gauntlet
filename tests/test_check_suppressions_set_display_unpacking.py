"""Red tests for the suppression gate's no_type_check ban through set displays unpacked into targets.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: any reference to `typing.no_type_check` or `typing.no_type_check_decorator`,
`typing_extensions` included, is a finding wherever it appears, and a use of a name is a
finding when any binding of that name, in the scope Python's scoping rules resolve the
use to, is either function. The value is followed into the targets its items reach when
the value of an assignment is a list, tuple or set display written in place. A set display has no item order, so each target its items reach
takes every one of them. A starred target is bound to a list, never to the function, so a
use of it is no finding.

Each seeded use spells only the bound name, never `no_type_check`, so only the gate's
resolution of names can report its line.
"""

from pathlib import Path

import pytest

from gates.check_suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


SET_DISPLAY_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "first, loose = {print, no_type_check}",
            "",
            "",
            "@first",
            "def seeded() -> None:",
            "    pass",
            "",
            "",
            "@loose",
            "def other() -> None:",
            "    pass",
        ),
        [1, 3, 6, 11],
        id="function-written-last-reaches-both-targets",
    ),
    pytest.param(
        _source(
            "from typing_extensions import no_type_check_decorator",
            "",
            "first, loose = {no_type_check_decorator, print}",
            "",
            "",
            "checked = first(print)",
            "unchecked = loose(print)",
        ),
        [1, 3, 6, 7],
        id="decorator-function-written-first-reaches-both-targets",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "first, middle, last = {print, len, typing.no_type_check}",
            "",
            "",
            "one = first(print)",
            "two = middle(print)",
            "three = last(print)",
        ),
        [3, 6, 7, 8],
        id="module-attribute-reaches-all-three-targets",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "outer, (inner, deep) = print, {len, no_type_check}",
            "",
            "",
            "kept = outer(print)",
            "one = inner(print)",
            "two = deep(print)",
        ),
        [1, 3, 7, 8],
        id="set-nested-in-a-tuple-reaches-only-its-own-targets",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "first, *rest = {print, len, no_type_check}",
            "",
            "",
            "one = first(print)",
            "held = rest",
        ),
        [1, 3, 6],
        id="starred-target-of-a-set-is-never-the-function",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "unpacked_set.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "finding_lines"), SET_DISPLAY_SOURCES)
def test_set_display_unpacked_binds_every_reached_target_to_the_function(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report each reference line and each use of every target a set display holding the function reaches."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
