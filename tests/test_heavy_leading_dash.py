"""Red tests for the host-safety wrapper given a command whose first word begins with `-`.

Source: the agents design spec under docs/superpowers/specs/, "Decisions", the bullet on heavy runs: the wrapper runs
its command "by the line one pure function gives, `wrapped(command, platform, niceness)`, where `platform` is the host
as `sys.platform` names it, `linux` or `darwin`, and `niceness` is the caller's own [...]: on Linux `ionice -c3 nice -n
<k> -- <command>`, on macOS `nice -n <k> -- <command>`, with no `taskpolicy -b`, [...] where `k` is 19 − niceness
[...]; the `--` ends
`nice`'s options, so any command is run as given, one whose first word begins with `-` included; each tool is found on
`PATH`". "It exits with its command's exit status." The wrapper is given `--lock <path>` before its command.

The line is held whole, the command after the `--` exactly as given, whether its first word is a lone `-x`, a word
written like `nice`'s own `-n`, or `--` itself. The run is held end to end: a program whose name begins with `-` is put
first on `PATH`, the wrapper is given it as its command, and the program must run with its arguments as given and the
wrapper exit with the program's status. The run is given `--lock` with a path under the test's temporary directory and
never takes the default, since this suite's own run already holds it.
"""

import subprocess
import sys
from pathlib import Path

from gates import heavy

REPO_ROOT = Path(__file__).parents[1]

END = 20

SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

PROGRAM = "-gauntlet-probe"

ARGUMENTS = ["-n", "5", "--lock", "other"]

STATUS = 3

LINUX = ["ionice", "-c3", "nice", "-n", "19", "--"]

DARWIN = ["nice", "-n", "19", "--"]

LONE = ["-x"]

NICE_OPTION = ["-n", "5", "make"]

DOUBLE_DASH = ["--", "make"]


def _program(tools: Path, record: Path) -> None:
    """Put in tools a program named PROGRAM that notes its arguments in record and exits with STATUS."""
    tools.mkdir()
    program = tools / PROGRAM
    program.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{record}'\nexit {STATUS}\n", encoding="utf-8")
    program.chmod(0o755)


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_linux_x() -> None:
    """On Linux a command whose first word is a lone -x follows nice's --, exactly as given."""
    assert heavy.wrapped(LONE, "linux", 0) == ["ionice", "-c3", "nice", "-n", "19", "--", "-x"]


def test_darwin_x() -> None:
    """On macOS a command whose first word is a lone -x follows nice's --, exactly as given."""
    assert heavy.wrapped(LONE, "darwin", 0) == ["nice", "-n", "19", "--", "-x"]


def test_linux_n() -> None:
    """On Linux a command that begins like nice's own -n follows nice's --, exactly as given."""
    assert heavy.wrapped(NICE_OPTION, "linux", 0) == [*LINUX, "-n", "5", "make"]


def test_darwin_n() -> None:
    """On macOS a command that begins like nice's own -n follows nice's --, exactly as given."""
    assert heavy.wrapped(NICE_OPTION, "darwin", 0) == [*DARWIN, "-n", "5", "make"]


def test_linux_dd() -> None:
    """On Linux a command whose first word is -- itself follows nice's own --, exactly as given."""
    assert heavy.wrapped(DOUBLE_DASH, "linux", 0) == [*LINUX, "--", "make"]


def test_darwin_dd() -> None:
    """On macOS a command whose first word is -- itself follows nice's own --, exactly as given."""
    assert heavy.wrapped(DOUBLE_DASH, "darwin", 0) == [*DARWIN, "--", "make"]


def test_run_dash(tmp_path: Path) -> None:
    """The wrapper given a command whose first word begins with - runs it with its arguments as given and exits with
    its status."""
    tools = tmp_path / "tools"
    record = tmp_path / "record"
    _program(tools, record)
    line = [sys.executable, "-m", heavy.__name__, "--lock", str(tmp_path / "heavy.lock"), PROGRAM, *ARGUMENTS]

    status = subprocess.run(
        line, cwd=REPO_ROOT, check=False, timeout=END, env={"PATH": f"{tools}:{SYSTEM_PATH}"}
    ).returncode

    assert (status, _lines(record)) == (STATUS, ARGUMENTS)
