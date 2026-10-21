"""Red tests for the host-safety wrapper's command run, now the gates core's `checker.run`.

Source: the gates core design under docs/superpowers/specs/, section 1, checker.py: `run` runs a process "in its own
session; the whole group is killed at the timeout or on any interrupt"; the C6 row has heavy.py on `checker.run` and
`throttle_line`, the latter "GateError on a host with none, or a tool not on `path`". The agents design spec's heavy
bullet: "where a tool of the line is not on `PATH`, the wrapper runs nothing and exits 2", so a run refused for its
line has run nothing, and takes no lock to do so.

Every run is given `--lock` with a path under the test's temporary directory and never takes the default, since this
suite's own run already holds it. The command a signal test runs notes its process id in a file and sleeps for END
seconds, longer than a test waits for it to end, and each such test kills the recorded id by its pid at the end.
"""

import contextlib
import fcntl
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]

END = 20

SETTLE = 5

BLOCKED = 2

SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

RAN = "ran"

NOTE = "import sys\nwith open(sys.argv[1], 'a', encoding='utf-8') as log:\n    log.write(sys.argv[2] + '\\n')\n"

# Notes the command's process id, then sleeps; the wrapper's stop signal must end it.
SLEEP = (
    "import os, sys, time\n"
    "with open(sys.argv[1], 'w', encoding='utf-8') as out:\n"
    "    out.write(str(os.getpid()))\n"
    f"time.sleep({END})\n"
)


def _wrapper(options: list[str], command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run the wrapper with options before the command, from the repository root, to its end.

    The module is imported here, at each run, so a test and not collection meets it.
    """
    from gates import heavy

    line = [sys.executable, "-m", heavy.__name__, *options, *command]
    return subprocess.run(line, cwd=REPO_ROOT, check=False, timeout=END, capture_output=True, text=True, env=env)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def _noted(path: Path) -> int:
    """Wait for the command to note its process id in the file, and return it."""
    deadline = time.monotonic() + END
    while time.monotonic() < deadline:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if text:
            return int(text)
        time.sleep(0.05)
    message = f"the command never noted its process id in {path}"
    raise AssertionError(message)


def test_refused_line_takes_no_lock(tmp_path: Path) -> None:
    """A run refused because a tool of its line is not on PATH exits 2 at once, though another process holds its lock."""
    lock = tmp_path / "heavy.lock"
    log = tmp_path / "log"
    empty = tmp_path / "tools"
    empty.mkdir()
    with lock.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        result = _wrapper(["--lock", str(lock)], [sys.executable, "-c", NOTE, str(log), RAN], {"PATH": str(empty)})

    assert (result.returncode, log.exists()) == (BLOCKED, False)


def test_stop_signal_ends_the_command(tmp_path: Path) -> None:
    """A signal that ends the wrapper ends its command too, not only the wrapper, and the command is not left running."""
    from gates import heavy

    note = tmp_path / "pid"
    env = {"PATH": SYSTEM_PATH}
    wrapper = subprocess.Popen(
        [sys.executable, "-m", heavy.__name__, "--lock", str(tmp_path / "heavy.lock"), sys.executable, "-c", SLEEP, str(note)],
        cwd=REPO_ROOT,
        env=env,
    )
    pid = 0
    try:
        pid = _noted(note)
        wrapper.send_signal(signal.SIGTERM)
        wrapper.wait(timeout=END)
        deadline = time.monotonic() + SETTLE
        while _alive(pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        left = _alive(pid)
    finally:
        if wrapper.poll() is None:
            wrapper.kill()
            wrapper.wait()
        if pid and _alive(pid):
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)

    assert left is False
