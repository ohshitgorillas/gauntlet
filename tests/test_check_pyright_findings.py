"""Red tests for the pyright gate's finding lines on a finished run.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph:
"it prints each finding on its own line and prints its count line on every run." and "Gate
code", third bullet: "a finding carries the checker's whole message". The pyright gate is
"Types", second bullet.

Each seeded finding assigns a seeded string to a variable declared `int`, so pyright's message
for it names the seeded string. A line carrying a finding is found by the seeded string it names.

The documents name no stream, so stdout and stderr are written into one buffer.
"""

import io
from collections.abc import Callable
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from gates.check_pyright import main

ALPHA = 'first_value: int = "alpha"\n'

BETA = 'second_value: int = "beta"\n'

SEEDED = ("alpha", "beta")


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _one_file(tmp_path: Path) -> list[Path]:
    return [_seed(tmp_path, "seeded.py", ALPHA + BETA)]


def _two_files(tmp_path: Path) -> list[Path]:
    return [_seed(tmp_path, "first.py", ALPHA), _seed(tmp_path, "second.py", BETA)]


def _printed_lines(paths: list[Path]) -> list[str]:
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        main(paths)
    return buffer.getvalue().splitlines()


@pytest.mark.parametrize(
    "layout",
    [
        pytest.param(_one_file, id="one-file"),
        pytest.param(_two_files, id="two-files"),
    ],
)
def test_each_finding_on_own_line(
    tmp_path: Path, layout: Callable[[Path], list[Path]]
) -> None:
    """Two findings print on two lines, one finding to a line."""
    lines = _printed_lines(layout(tmp_path))
    carrying = [line for line in lines if any(word in line for word in SEEDED)]

    assert len(carrying) == 2
