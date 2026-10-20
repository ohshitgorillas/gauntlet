"""Red tests for the host-safety wrapper given `--` right after its own options.

Source: the agents design spec under docs/superpowers/specs/, "Decisions", the bullet on heavy runs: "given `--lock
<path>` before its command, it locks that path instead [...]. One `--` right after the wrapper's own options ends them
and is not passed on, so `uv run python -m gates.heavy -- make check` runs `make check`." The same bullet has "any
command is run as given, one whose first word begins with `-` included" and "It exits with its command's exit status."

The `--` is held end to end: a program put first on `PATH` notes its arguments and exits with STATUS, the wrapper is
given `--lock`, its path, `--` and the program, and the program must run with its arguments as given and the wrapper
exit with its status. Only the one `--` right after the options is taken: a second `--` right after it is the command's
first word, and a `--` later in the command is one of its arguments. Each such run is given `--lock` with a path under
the test's temporary directory and never takes the default, since this suite's own run already holds it; so the form
with no option before the `--`, and a `--lock` written after the `--`, are held where the wrapper reads its arguments.
"""

import subprocess
import sys
from pathlib import Path

from gates import heavy

REPO_ROOT = Path(__file__).parents[1]

END = 20

SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

PROGRAM = "gauntlet-probe"

DASH_PROGRAM = "-gauntlet-probe"

DOUBLE_DASH = "--"

ARGUMENTS = ["-n", "5", "--lock", "other"]

LATER = ["first", "--", "second"]

STATUS = 3


def _program(tools: Path, name: str, record: Path) -> None:
    """Put in tools a program named name that notes its arguments in record and exits with STATUS."""
    tools.mkdir(exist_ok=True)
    program = tools / name
    program.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{record}'\nexit {STATUS}\n", encoding="utf-8")
    program.chmod(0o755)


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def _run(tmp_path: Path, name: str, after: list[str]) -> tuple[int, list[str]]:
    """Run the wrapper given --lock, its path and after, with a program named name first on PATH.

    Returns the wrapper's exit status and the arguments the program noted.
    """
    tools = tmp_path / "tools"
    record = tmp_path / "record"
    _program(tools, name, record)
    line = [sys.executable, "-m", heavy.__name__, "--lock", str(tmp_path / "heavy.lock"), *after]
    status = subprocess.run(
        line, cwd=REPO_ROOT, check=False, timeout=END, env={"PATH": f"{tools}:{SYSTEM_PATH}"}
    ).returncode
    return status, _lines(record)


def _command(arguments: list[str]) -> list[str]:
    """The command the wrapper reads from arguments."""
    return heavy.parser().parse_args(arguments, namespace=heavy.Arguments()).command


def test_ends_options(tmp_path: Path) -> None:
    """A -- right after --lock and its path is not passed on: the command after it runs as given, and the wrapper exits
    with its status."""
    assert _run(tmp_path, PROGRAM, [DOUBLE_DASH, PROGRAM, *ARGUMENTS]) == (STATUS, ARGUMENTS)


def test_dash_program(tmp_path: Path) -> None:
    """After the --, a command whose first word begins with - is the command, not an option of the wrapper."""
    assert _run(tmp_path, DASH_PROGRAM, [DOUBLE_DASH, DASH_PROGRAM, *ARGUMENTS]) == (STATUS, ARGUMENTS)


def test_one_taken(tmp_path: Path) -> None:
    """Only one -- is taken: a second -- right after it is the command's program, run with the arguments after it."""
    assert _run(tmp_path, DOUBLE_DASH, [DOUBLE_DASH, DOUBLE_DASH, *ARGUMENTS]) == (STATUS, ARGUMENTS)


def test_later_kept(tmp_path: Path) -> None:
    """A -- later in the command than right after the options is passed on as one of the command's arguments."""
    assert _run(tmp_path, PROGRAM, [DOUBLE_DASH, PROGRAM, *LATER]) == (STATUS, LATER)


def test_no_options() -> None:
    """Given -- before any option of its own, the wrapper reads the command after it, as `-- make check` runs
    `make check`."""
    assert _command([DOUBLE_DASH, "make", "check"]) == ["make", "check"]


def test_lock_after() -> None:
    """A --lock after the -- is part of the command, not the wrapper's option."""
    assert _command([DOUBLE_DASH, "--lock", "other", "make"]) == ["--lock", "other", "make"]
