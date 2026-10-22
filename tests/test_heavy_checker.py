"""Red tests for the host-safety wrapper's command run, now the gates core's `checker.run`.

Source: the gates core design under docs/superpowers/specs/, section 1, checker.py: `run` runs a process "in its own
session; the whole group is killed at the timeout or on any interrupt"; the C6 row has heavy.py on `checker.run` and
`throttle_line`, the latter "GateError on a host with none, or a tool not on `path`". The agents design spec's heavy
bullet: "where a tool of the line is not on `PATH`, the wrapper runs nothing and exits 2", so a run refused for its
line has run nothing, and takes no lock to do so.

Every run is given `--lock` with a path under the test's temporary directory and never takes the default, since this
suite's own run already holds it. The command a signal test runs notes its process id in a file, writes a ready line and
holds on a `Lifeline` the test never releases (`tests/support/lifeline.py` of the no-wall-clock design spec), and each
such test's `Pids` kills the recorded id at the end. The test reads the ready line as the event that the command is
running, and then its standard output to its end, which comes only when no process of the run holds it, with no timeout.
"""

import fcntl
import os
import signal
import subprocess
import sys
from pathlib import Path

from tests.support.lifeline import HOLD, Lifeline, Pids, ready

REPO_ROOT = Path(__file__).parents[1]

BLOCKED = 2

SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

RAN = "ran"

NOTE = "import sys\nwith open(sys.argv[1], 'a', encoding='utf-8') as log:\n    log.write(sys.argv[2] + '\\n')\n"

# Notes the command's process id in the file named by its second argument, then HOLDs on the fd named by its first; the
# wrapper's stop signal must end it.
NOTE_PID = (
    "import os, sys\n"
    "with open(sys.argv[2], 'w', encoding='utf-8') as out:\n"
    "    out.write(str(os.getpid()))\n" + HOLD
)

# The descriptor the command holds on: its standard input, the Lifeline's read end.
LIFELINE_FD = "0"

# The line HOLD writes once the command is running.
RUNNING = b"ready\n"


def _wrapper(
    options: list[str], command: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the wrapper with options before the command, from the repository root, to its end.

    The module is imported here, at each run, so a test and not collection meets it.
    """
    from gates import heavy

    line = [sys.executable, "-m", heavy.__name__, *options, *command]
    return subprocess.run(
        line, cwd=REPO_ROOT, check=False, capture_output=True, text=True, env=env
    )


def test_refused_line_takes_no_lock(tmp_path: Path) -> None:
    """A run refused because a tool of its line is not on PATH exits 2 at once, though another process holds its lock."""
    lock = tmp_path / "heavy.lock"
    log = tmp_path / "log"
    empty = tmp_path / "tools"
    empty.mkdir()
    with lock.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        result = _wrapper(
            ["--lock", str(lock)],
            [sys.executable, "-c", NOTE, str(log), RAN],
            {"PATH": str(empty)},
        )

    assert (result.returncode, log.exists()) == (BLOCKED, False)


def test_stop_signal_ends_the_command(tmp_path: Path) -> None:
    """A signal that ends the wrapper ends its command too, not only the wrapper, and the command is not left running."""
    from gates import heavy

    note = tmp_path / "pid"
    env = {"PATH": SYSTEM_PATH}
    output_read, output_write = os.pipe()
    with Lifeline() as lifeline, Pids(note):
        wrapper = subprocess.Popen(
            [
                sys.executable,
                "-m",
                heavy.__name__,
                "--lock",
                str(tmp_path / "heavy.lock"),
                sys.executable,
                "-c",
                NOTE_PID,
                LIFELINE_FD,
                str(note),
            ],
            cwd=REPO_ROOT,
            env=env,
            stdin=lifeline.read_fd,
            stdout=output_write,
        )
        os.close(output_write)
        try:
            running = ready(output_read) == RUNNING
            wrapper.send_signal(signal.SIGTERM)
            wrapper.wait()
            # End of file on the command's output comes only once no process of the run holds it. A command that never
            # ran counts as left, so the test fails and does not pass on a wrapper that ran nothing.
            left = not running or ready(output_read) != b""
        finally:
            if wrapper.poll() is None:
                wrapper.kill()
                wrapper.wait()
            os.close(output_read)

    assert left is False
