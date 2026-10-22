# Copyright 2026 oh shit, gorillas!
"""Red tests for the output files a checker writes: a file left at an output path is never read back as the checker's.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
"`run` deletes a file already at an output path before it starts the checker, so a file it reads back is one this
checker wrote, and an output file that exists but cannot be read, or cannot be deleted, is a GateError." An output
not written is None in `Completed.outputs`.

A path that holds a directory can neither be deleted as a file nor read as one, whoever runs the test, so a directory
left at an output path is one that cannot be deleted, and a directory the checker makes there is one that exists and
cannot be read. The checker that would make a mark file shows whether it started.
"""

import sys
from pathlib import Path

import pytest

from gates.core.checker import Command, run
from gates.core.report import GateError

STALE = '<?xml version="1.0"?>\n<testsuites><testsuite name="stale" tests="9"/></testsuites>\n'

EXIT = "import sys\nsys.exit(0)\n"

MAKE_DIRECTORY = "import os, sys\nos.mkdir(sys.argv[1])\n"

MARK = "import pathlib, sys\npathlib.Path(sys.argv[1]).with_suffix('.started').write_text('')\n"


def _run(tmp_path: Path, code: str, report: Path) -> dict[str, str | None]:
    """Run code with report as its argument, naming report as the output `junit`; return what run read back."""
    command = Command(
        argv=(sys.executable, "-c", code, str(report)),
        cwd=tmp_path,
        outputs={"junit": report},
    )
    return dict(run(command).outputs)


def test_stale_output_is_not_read(tmp_path: Path) -> None:
    """A file left at an output path, which the checker does not write, is None: it is not read as the checker's."""
    report = tmp_path / "junit.xml"
    report.write_text(STALE, encoding="utf-8")

    assert _run(tmp_path, EXIT, report) == {"junit": None}


def test_undeletable_output(tmp_path: Path) -> None:
    """A directory left at an output path cannot be deleted: a GateError, and the checker never starts."""
    report = tmp_path / "junit.xml"
    report.mkdir()

    with pytest.raises(GateError):
        _run(tmp_path, MARK, report)
    assert not report.with_suffix(".started").exists()


def test_unreadable_output(tmp_path: Path) -> None:
    """An output path the checker leaves holding something that exists and cannot be read as a file: a GateError."""
    with pytest.raises(GateError):
        _run(tmp_path, MAKE_DIRECTORY, tmp_path / "junit.xml")
