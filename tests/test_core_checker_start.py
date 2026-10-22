# Copyright 2026 oh shit, gorillas!
"""Red tests for a checker whose program cannot start: `run` raises a GateError instead of giving back a Completed.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`def run(command: Command) -> Completed  # own session; ...; GateError if the program cannot start`. GateError is the
core's error of section 1, "report.py": "something stops the checker; ... printed as the checker's, exit 2". The quality
gates spec's "Gates" bullet lists "a checker that cannot start" among what keeps a gate from running its checker.

A program cannot start when the path argv names holds no file, when the file there may not be executed, when the path
is a directory, when its shebang names an interpreter that does not exist, and when a bare name is on no directory of
the PATH it runs under. A shell would report the first as status 127; `run` gives back no Completed at all, so a
GateError comes out. The quality gates spec has the gate print "one error naming what kept the gate from running its
checker", and GateError keeps `.report`, the report as given, which is printed as the checker's, so that report names
the checker that cannot start: the program the Command's argv names. Its other words the documents do not fix.
"""

from collections.abc import Callable
from pathlib import Path

import pytest

from gates.core.checker import Command, run
from gates.core.report import GateError

ABSENT_NAME = "gauntlet-no-such-checker-7f3a"

SCRIPT = "#!/bin/sh\nexit 0\n"

NOT_EXECUTABLE = 0o644

EXECUTABLE = 0o755


def _missing(tmp_path: Path) -> Command:
    return Command(argv=(str(tmp_path / "absent-checker"),), cwd=tmp_path)


def _not_executable(tmp_path: Path) -> Command:
    program = tmp_path / "checker.sh"
    program.write_text(SCRIPT, encoding="utf-8")
    program.chmod(NOT_EXECUTABLE)
    return Command(argv=(str(program),), cwd=tmp_path)


def _directory(tmp_path: Path) -> Command:
    program = tmp_path / "checker.d"
    program.mkdir()
    return Command(argv=(str(program),), cwd=tmp_path)


def _missing_interpreter(tmp_path: Path) -> Command:
    program = tmp_path / "checker"
    program.write_text(f"#!{tmp_path / 'absent-interpreter'}\n", encoding="utf-8")
    program.chmod(EXECUTABLE)
    return Command(argv=(str(program),), cwd=tmp_path)


def _not_on_path(tmp_path: Path) -> Command:
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    return Command(argv=(ABSENT_NAME,), cwd=tmp_path, env={"PATH": str(empty)})


@pytest.mark.parametrize(
    "build",
    [_missing, _not_executable, _directory, _missing_interpreter, _not_on_path],
    ids=[
        "missing",
        "not-executable",
        "directory",
        "missing-interpreter",
        "not-on-path",
    ],
)
def test_cannot_start(tmp_path: Path, build: Callable[[Path], Command]) -> None:
    """A Command whose program cannot start makes `run` raise a GateError whose report names that program."""
    command = build(tmp_path)
    with pytest.raises(GateError) as caught:
        run(command)
    assert command.argv[0] in caught.value.report
