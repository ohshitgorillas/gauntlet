# Copyright 2026 oh shit, gorillas!
"""Red tests: the suppression gate reports a first-bullet comment marker in a `.pyi` file.

Source: the quality-gates design spec under docs/superpowers/specs/.
"Gates", intro paragraph: "Every gate applies to every Python file in the tree" and
"A Python file is a file whose name ends in `.py` or `.pyi`".
"Suppression gate", first bullet: "a `noqa`, `type: ignore`, `pyright: ignore`,
`pragma: no cover` or `pragma: no mutate` comment, found by tokenizing".
"Gates", intro paragraph: "A gate exits 0 with no finding, 1 with one or more findings,
and 2 when its checker could not finish".
"""

from pathlib import Path

import pytest

from gates.check_suppressions import main

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
def test_gate_fails_on_marker_in_pyi_file(tmp_path: Path, marker: str) -> None:
    """Verify gate fails on marker in pyi file."""
    clean = _seed(tmp_path, "clean.py", "value = 1\n")
    marked = _seed(tmp_path, "seeded.pyi", f"value: int  # {marker}\n")

    assert main([clean, marked]) == 1


def test_gate_passes_pyi_file_without_markers(tmp_path: Path) -> None:
    """Verify gate passes pyi file without markers."""
    path = _seed(tmp_path, "clean.pyi", "value: int  # an ordinary comment\n")

    assert main([path]) == 0
