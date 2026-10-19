"""Red tests for the pyright gate on a file pyright cannot read or cannot parse.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph:
"A gate exits 0 with no finding, 1 with one or more findings, and 2 when its checker could not
finish" and "A Python file the checker cannot read or cannot parse is a file the checker did not
finish: the gate prints what the checker reported for that file and exits 2, whatever it found in
the other files." The pyright gate is "Types", second bullet.

A file is made unreadable by taking away every permission bit, and unparseable by seeding Python
syntax no parser accepts. Each companion file is one the gate alone would pass (exit 0) or fail
with a finding (exit 1), and it is placed before and after the unfinished file, so only a gate
that lets the unfinished file decide its verdict exits 2 on every layout.
"""

from pathlib import Path

import pytest

from gates.check_pyright import main

UNPARSEABLE = "def broken(:\n    return\n"

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

ONE_FINDING = 'first_value: int = "alpha"\n'

LAYOUTS = [
    pytest.param(None, True, id="alone"),
    pytest.param(CLEAN, True, id="clean1"),
    pytest.param(CLEAN, False, id="clean2"),
    pytest.param(ONE_FINDING, True, id="found1"),
    pytest.param(ONE_FINDING, False, id="found2"),
]


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _layout(tmp_path: Path, broken: Path, companion: str | None, *, broken_first: bool) -> list[Path]:
    if companion is None:
        return [broken]
    other = _seed(tmp_path, "companion.py", companion)
    return [broken, other] if broken_first else [other, broken]


@pytest.mark.parametrize(("companion", "broken_first"), LAYOUTS)
def test_unparsed(tmp_path: Path, companion: str | None, *, broken_first: bool) -> None:
    """A file pyright cannot parse makes the run unfinished, whatever the other file holds."""
    broken = _seed(tmp_path, "broken.py", UNPARSEABLE)
    paths = _layout(tmp_path, broken, companion, broken_first=broken_first)

    assert main(paths) == 2


@pytest.mark.parametrize(("companion", "broken_first"), LAYOUTS)
def test_unread(tmp_path: Path, companion: str | None, *, broken_first: bool) -> None:
    """A file pyright cannot read makes the run unfinished, whatever the other file holds."""
    broken = _seed(tmp_path, "unreadable.py", CLEAN)
    broken.chmod(0o000)
    paths = _layout(tmp_path, broken, companion, broken_first=broken_first)

    assert main(paths) == 2
