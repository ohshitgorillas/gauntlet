# Copyright 2026 oh shit, gorillas!
"""Red tests: the mypy gate's verdict on a Python file does not depend on the tree's other files.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "A gate's verdict on a Python file is the same whatever other files the tree holds." The same paragraph: a gate exits 0 with no finding, 1 with one or more findings, and 2 when its checker could not finish, and prints each finding on its own line. Applied to the mypy gate of "Types", first bullet.
"""

from pathlib import Path

import pytest

from gates.check_mypy import main

TYPE_ERROR = 'count: int = "none"\n'

WELL_TYPED = "def double(value: int) -> int:\n    return value * 2\n"

SYNTAX_ERROR = "def broken(:\n"

TARGET = "gauntlet/core/decide.py"

TARGET_NAME = "decide.py"

NAMESAKE = "tools/decide.py"

NEIGHBOUR = "tools/broken.py"


def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _lines_naming(capsys: pytest.CaptureFixture[str], name: str) -> list[str]:
    """Each printed line naming the file, from the file name on: the spec leaves open how a line spells the directories before it."""
    captured = capsys.readouterr()
    lines = (captured.out + captured.err).splitlines()
    return [line[line.index(name) :] for line in lines if name in line]


def test_namesake_clean(tmp_path: Path) -> None:
    """Two well-typed files sharing a file name in different directories each pass, so the tree passes."""
    files = [_seed(tmp_path, TARGET, WELL_TYPED), _seed(tmp_path, NAMESAKE, WELL_TYPED)]

    assert main(files) == 0


def test_namesake_finding(tmp_path: Path) -> None:
    """A type error beside a well-typed file of the same name is one finding, not a checker that could not finish."""
    files = [_seed(tmp_path, TARGET, TYPE_ERROR), _seed(tmp_path, NAMESAKE, WELL_TYPED)]

    assert main(files) == 1


def test_syntax_neighbour(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A file with a syntax error elsewhere in the tree leaves the findings on a type error in another file unchanged."""
    target = _seed(tmp_path, TARGET, TYPE_ERROR)
    neighbour = _seed(tmp_path, NEIGHBOUR, SYNTAX_ERROR)
    main([target])
    alone = _lines_naming(capsys, TARGET_NAME)
    assert alone

    main([target, neighbour])

    assert _lines_naming(capsys, TARGET_NAME) == alone
