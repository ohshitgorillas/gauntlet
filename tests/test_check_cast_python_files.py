"""Red test for the cast gate's exit status when its checker cannot finish.

Source: the quality-gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "Every gate applies to
every Python file in the tree: `gauntlet/`, `tests/`, gate scripts, and any hook or tool script. No path is excluded.
A Python file is a file whose name ends in `.py` or `.pyi`, or an extensionless file whose first line is a shebang that
names python; a `.pyw` file is not one." and "A gate exits 0 with no finding, 1 with one or more findings, and 2 when
its checker could not finish". The banned name comes from "Types", third bullet: "`typing.cast` is banned (ruff
`TID251`)."

The seeded file holds a use of `typing.cast`, so a gate that checks it has a finding and exits 1. The test name is
kept short so that pytest's one-line summary has room to name the exception the test fails with.
"""

import stat
from pathlib import Path

from gates.check_cast import main

DIRTY = "import typing\n\nvalue = typing.cast(int, 1)\n"


def _seed(path: Path, source: str) -> Path:
    path.write_text(source, encoding="utf-8")
    return path


def test_unreadable(tmp_path: Path) -> None:
    """A checker that cannot read a Python file it was given could not finish checking it, so the gate exits 2.

    Exit 0 would pass a file nobody read, and exit 1 would report a finding the file was never checked for.
    """
    path = _seed(tmp_path / "locked.py", DIRTY)
    path.chmod(stat.S_IWUSR)

    assert main([path]) == 2
