# Copyright 2026 oh shit, gorillas!
"""Red tests for the suppression gate's no_type_check ban on sequence patterns over a set subject.

Source: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item: any reference to `typing.no_type_check` or `typing.no_type_check_decorator`,
`typing_extensions` included, is a finding wherever it appears, so the import line and
the match line whose subject names the function are findings. A `match` capture pattern
that takes either function as its value is a binding that is the function, and the value
is followed when the subject is a list, tuple or set display written in place. The line
of a `case` whose capture pattern binds either function is a finding. A set never
matches a sequence pattern, so the captures of a sequence pattern over a set subject
bind nothing: neither their case line nor a use of their names is a finding.

Each seeded use spells only the captured name, never `no_type_check`, so only the gate's
resolution of names could report its line.
"""

from pathlib import Path

import pytest

from tests.support.suppressions import find_suppressions


def _source(*lines: str) -> str:
    return "\n".join(lines) + "\n"


SET_SUBJECT_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match {no_type_check}:",
            "    case [loose]:",
            "        pass",
            "",
            "",
            "@loose",
            "def seeded() -> None:",
            "    pass",
        ),
        [1, 3],
        id="list-sequence-pattern-over-a-one-item-set",
    ),
    pytest.param(
        _source(
            "from typing_extensions import no_type_check_decorator",
            "",
            "match {print, no_type_check_decorator}:",
            "    case (first, loose):",
            "        pass",
            "",
            "",
            "one = first(print)",
            "two = loose(print)",
        ),
        [1, 3],
        id="tuple-sequence-pattern-over-a-two-item-set",
    ),
    pytest.param(
        _source(
            "import typing",
            "",
            "match {typing.no_type_check, len}:",
            "    case [loose, *rest]:",
            "        pass",
            "",
            "",
            "one = loose(print)",
        ),
        [3],
        id="starred-sequence-pattern-over-a-set-holding-the-module-attribute",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match (print, {no_type_check}):",
            "    case (outer, [inner]):",
            "        pass",
            "",
            "",
            "one = outer(print)",
            "two = inner(print)",
        ),
        [1, 3],
        id="sequence-pattern-over-a-set-nested-in-a-tuple-subject",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "",
            "def outer() -> None:",
            "    match {no_type_check}:",
            "        case [loose]:",
            "            pass",
            "    held = loose",
        ),
        [1, 5],
        id="sequence-pattern-over-a-set-in-a-function-scope",
    ),
]

MIXED_SUBJECT_SOURCES = [
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match {no_type_check}:",
            "    case [loose]:",
            "        pass",
            "",
            "match [no_type_check]:",
            "    case [caught]:",
            "        pass",
            "",
            "",
            "one = loose(print)",
            "two = caught(print)",
        ),
        [1, 3, 7, 8, 13],
        id="set-subject-beside-a-list-subject",
    ),
    pytest.param(
        _source(
            "from typing import no_type_check",
            "",
            "match {no_type_check}:",
            "    case [loose]:",
            "        pass",
            "",
            "match (no_type_check,):",
            "    case [caught]:",
            "        pass",
            "",
            "",
            "one = loose(print)",
            "two = caught(print)",
        ),
        [1, 3, 7, 8, 13],
        id="set-subject-beside-a-tuple-subject",
    ),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "set_subject.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(("source", "finding_lines"), SET_SUBJECT_SOURCES)
def test_sequence_pattern_over_a_set_subject_binds_nothing(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report only the reference lines, never the case line of a sequence pattern over a set nor a use of its captures."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines


@pytest.mark.parametrize(("source", "finding_lines"), MIXED_SUBJECT_SOURCES)
def test_only_the_sequence_pattern_over_a_set_subject_binds_nothing(
    tmp_path: Path, source: str, finding_lines: list[int]
) -> None:
    """Report the case line and use of a capture over a list or tuple display and leave out those over a set display."""
    path = _seed(tmp_path, source)

    assert sorted(finding.line for finding in find_suppressions(path)) == finding_lines
