"""Red tests for the reach of the mypy gate over the tree.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", first paragraph: every gate applies to every Python file in the tree, `gauntlet/`, `tests/`, gate scripts and any hook or tool script, and no path is excluded. A Python file is a file whose name ends in `.py`, or an extensionless file whose first line is a shebang that names python; a `.pyw` file is not one. Applied to the mypy gate of "Types", first bullet. The gate is handed the tree's files by path. A shebang naming `python3` or `python3.N` names python.
"""

from pathlib import Path

import pytest

from gates.check_mypy import main

SHEBANG = "#!/usr/bin/env python\n"

SCRIPT = "tools/release"

TYPE_ERROR = 'count: int = "none"\n'

WELL_TYPED = "def double(value: int) -> int:\n    return value * 2\n"

TREE_FILES = [
    "gauntlet/core/decide.py",
    "gauntlet/seams/runner.py",
    "tests/test_decide.py",
    "gates/check_sample.py",
    ".claude/hooks/guard.py",
    "tools/sweep.py",
    SCRIPT,
]

LOCATIONS = [
    pytest.param("gauntlet/core/decide.py", id="core"),
    pytest.param("gauntlet/seams/runner.py", id="seams"),
    pytest.param("tests/test_decide.py", id="tests"),
    pytest.param("gates/check_sample.py", id="gates"),
    pytest.param(".claude/hooks/guard.py", id="hook"),
    pytest.param("tools/sweep.py", id="tool"),
]

SHEBANGS = [
    pytest.param("#!/usr/bin/env python\n", id="env"),
    pytest.param("#!/usr/bin/env python3\n", id="env3"),
    pytest.param("#!/usr/bin/env python3.12\n", id="env312"),
    pytest.param("#!/usr/bin/python\n", id="bin"),
    pytest.param("#!/usr/bin/python3\n", id="bin3"),
    pytest.param("#!/usr/local/bin/python3.13\n", id="bin313"),
]

NOT_PYTHON = [
    pytest.param("tools/launch.pyw", TYPE_ERROR, id="pyw"),
    pytest.param("tools/deploy", "#!/bin/sh\necho done\n", id="sh"),
    pytest.param("tools/notes", TYPE_ERROR, id="bare"),
    pytest.param("tools/later", "# notes\n" + SHEBANG + TYPE_ERROR, id="late"),
    pytest.param("tools/run.sh", SHEBANG + TYPE_ERROR, id="ext"),
]


def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _seed_tree(root: Path, broken: str, shebang: str = SHEBANG) -> list[Path]:
    files: list[Path] = []
    for relative in TREE_FILES:
        prefix = shebang if relative == SCRIPT else ""
        body = TYPE_ERROR if relative == broken else WELL_TYPED
        files.append(_seed(root, relative, prefix + body))
    return files


@pytest.mark.parametrize("relative", LOCATIONS)
def test_tree_verdict(tmp_path: Path, relative: str) -> None:
    """A type error in one Python file of the tree turns the verdict of the gate run over the tree's files."""
    broken = _seed_tree(tmp_path / "broken", relative)
    clean = _seed_tree(tmp_path / "clean", "")

    assert main(broken) != main(clean)


@pytest.mark.parametrize("shebang", SHEBANGS)
def test_shebang(tmp_path: Path, shebang: str) -> None:
    """A type error in an extensionless script whose shebang names python turns the verdict."""
    broken = _seed_tree(tmp_path / "broken", SCRIPT, shebang)
    clean = _seed_tree(tmp_path / "clean", "", shebang)

    assert main(broken) != main(clean)


@pytest.mark.parametrize(("relative", "source"), NOT_PYTHON)
def test_skips(tmp_path: Path, relative: str, source: str) -> None:
    """A file that is not a Python file is not type checked, so a well-typed tree holding it passes."""
    files = [*_seed_tree(tmp_path, ""), _seed(tmp_path, relative, source)]

    assert main(files) == 0


def test_clean_tree(tmp_path: Path) -> None:
    """A tree whose every Python file is well typed passes the gate."""
    files = _seed_tree(tmp_path, "")

    assert main(files) == 0
