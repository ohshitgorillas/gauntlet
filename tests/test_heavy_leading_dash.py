"""Red tests for the host-safety wrapper given a command whose first word begins with `-`.

Source: the agents design spec under docs/superpowers/specs/, "Decisions", the bullet on heavy runs: the `--` of the
throttle line "ends `nice`'s options, so any command is run as given, one whose first word begins with `-` included".
"It exits with its command's exit status." The wrapper is given `--lock <path>` before its command.

The run is held end to end: a program whose name begins with `-` is put first on `PATH`, the wrapper is given it as its
command, and the program must run with its arguments as given and the wrapper exit with the program's status. The run
is given `--lock` with a path under the test's temporary directory and never takes the default, since this suite's own
run already holds it. The line itself, as one pure function gave it, is held by the throttle tests of the gates core.
"""

import subprocess
import sys
from pathlib import Path

from gates import heavy

REPO_ROOT = Path(__file__).parents[1]

SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

PROGRAM = "-gauntlet-probe"

ARGUMENTS = ["-n", "5", "--lock", "other"]

STATUS = 3


def _program(tools: Path, record: Path) -> None:
    """Put in tools a program named PROGRAM that notes its arguments in record and exits with STATUS."""
    tools.mkdir()
    program = tools / PROGRAM
    program.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{record}'\nexit {STATUS}\n", encoding="utf-8")
    program.chmod(0o755)


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def test_run_dash(tmp_path: Path) -> None:
    """The wrapper given a command whose first word begins with - runs it with its arguments as given and exits with
    its status."""
    tools = tmp_path / "tools"
    record = tmp_path / "record"
    _program(tools, record)
    line = [sys.executable, "-m", heavy.__name__, "--lock", str(tmp_path / "heavy.lock"), PROGRAM, *ARGUMENTS]

    status = subprocess.run(
        line, cwd=REPO_ROOT, check=False, env={"PATH": f"{tools}:{SYSTEM_PATH}"}
    ).returncode

    assert (status, _lines(record)) == (STATUS, ARGUMENTS)
