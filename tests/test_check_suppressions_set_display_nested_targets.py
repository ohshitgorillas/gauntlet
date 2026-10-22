# Copyright 2026 oh shit, gorillas!
"""Red tests for the suppression gate's no_type_check ban through set displays unpacked into nested targets.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: any reference to `typing.no_type_check` or `typing.no_type_check_decorator`
is a finding wherever it appears, and a use of a name is a finding when any binding of
that name, in the scope Python's scoping rules resolve the use to, is either function.
The value is followed into the targets its items reach when the value of an assignment
is a list, tuple or set display written in place. A set display has no item order, so
each target its items reach takes every one of them; where its items are themselves
displays unpacked into nested targets, each nested target takes every item in turn.

So a nested target position binds the function when the function fills that position
in some item, and a position no item fills with the function binds nothing banned.
Each seeded use spells only the bound name, never `no_type_check`, so only the gate's
resolution of names can report its line.
"""

from pathlib import Path

import pytest

from tests.support.suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


NESTED_TARGET_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "(first, second), (third, fourth) = {(print, no_type_check), (len, print)}",
            "",
            "",
            "one = first(print)",
            "two = second(print)",
            "three = third(print)",
            "four = fourth(print)",
        ),
        [1, 3, 7, 9],
        id="function-in-first-item-reaches-second-position-of-both-targets",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "(first, second), (third, fourth) = {(print, len), (no_type_check, print)}",
            "",
            "",
            "one = first(print)",
            "two = second(print)",
            "three = third(print)",
            "four = fourth(print)",
        ),
        [1, 3, 6, 8],
        id="function-in-last-item-reaches-first-position-of-both-targets",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "[first, second], [third, fourth] = {(len, print), (print, typing.no_type_check_decorator)}",
            "",
            "",
            "one = first(print)",
            "two = second(print)",
            "three = third(print)",
            "four = fourth(print)",
        ),
        [3, 7, 9],
        id="list-targets-take-the-decorator-function-at-its-position",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "(first, (second, third)), (fourth, (fifth, sixth)) = {(print, (len, no_type_check)), (len, (print, print))}",
            "",
            "",
            "one = first(print)",
            "two = second(print)",
            "three = third(print)",
            "four = fourth(print)",
            "five = fifth(print)",
            "six = sixth(print)",
        ),
        [1, 3, 8, 11],
        id="position-two-levels-deep-reaches-both-targets",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "nested_set.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "finding_lines"), NESTED_TARGET_SOURCES)
def test_set_display_items_unpacked_into_nested_targets_bind_each_position_the_function_fills(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report each reference line and each use of a nested target position some set item fills with the function."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
