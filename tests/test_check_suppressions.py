# Copyright 2026 oh shit, gorillas!
"""Red tests for the suppression gate's comment markers."""

from pathlib import Path

import pytest

from gates.check_suppressions import main
from tests.support.suppressions import find_suppressions

MARKERS = [
    "noqa",
    "type: ignore",
    "pyright: ignore",
    "pragma: no cover",
    "pragma: no mutate",
]


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize("marker", MARKERS)
def test_gate_fails_on_marker_comment(tmp_path: Path, marker: str) -> None:
    """Verify gate fails on marker comment."""
    path = _seed(tmp_path, "seeded.py", f"value = 1  # {marker}\n")

    assert main([path]) == 1


@pytest.mark.parametrize(
    "comment",
    ["noqa: E501", "type: ignore[misc]", "pyright: ignore[reportUnknownMemberType]"],
)
def test_gate_fails_on_marker_comment_with_rule_code(
    tmp_path: Path, comment: str
) -> None:
    """Verify gate fails on marker comment with rule code."""
    path = _seed(tmp_path, "seeded.py", f"value = 1  # {comment}\n")

    assert main([path]) == 1


def test_gate_passes_file_without_markers(tmp_path: Path) -> None:
    """Verify gate passes file without markers."""
    path = _seed(tmp_path, "clean.py", "value = 1  # an ordinary comment\n")

    assert main([path]) == 0


def test_gate_passes_marker_text_inside_string_literal(tmp_path: Path) -> None:
    """Verify gate passes marker text inside string literal."""
    path = _seed(tmp_path, "literal.py", 'value = "# noqa"\nother = "# type: ignore"\n')

    assert main([path]) == 0


def test_gate_fails_when_any_listed_file_carries_a_marker(tmp_path: Path) -> None:
    """Verify gate fails when any listed file carries a marker."""
    first = _seed(tmp_path, "first.py", "value = 1\n")
    dirty = _seed(tmp_path, "dirty.py", "value = 1  # pragma: no cover\n")
    last = _seed(tmp_path, "last.py", "value = 1\n")

    assert main([first, dirty, last]) == 1


def test_find_reports_comment_line_but_not_string_line(tmp_path: Path) -> None:
    """Verify find reports comment line but not string line."""
    path = _seed(tmp_path, "mixed.py", 'value = "# noqa"\nother = 2  # noqa\n')

    assert [found.line for found in find_suppressions(path)] == [2]
