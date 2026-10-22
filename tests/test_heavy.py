"""Red tests for the host-safety wrapper every heavy run is made under.

Source: the agents design spec under docs/superpowers/specs/, "Decisions", the bullet on heavy runs: every heavy run "is
wrapped in `uv run python -m gates.heavy`, the host-safety wrapper in `gates/heavy.py`". "It holds an exclusive
`fcntl.flock` lock on `/tmp/gauntlet-heavy.lock` for the whole of the command it is given, so a second wrapped run waits
until the first ends; given `--lock <path>` before its command, it locks that path instead". "It runs that command at
niceness 19, and on Linux at the lowest I/O priority too". "It exits with its command's exit status."
The owner names the lock as one taken with `fcntl.flock`, so a lock the test takes that way on the given path is one the
wrapper waits on.

Every wrapped run here is given `--lock` with a path under the test's temporary directory and never takes the default:
every documented heavy run, this suite's own among them, already holds the default lock, so a test that took it would
wait on itself. Waiting is held by order, never by a clock: a run that must wait is given WAIT seconds to break the order
it is held to, and the line it writes must come after the line written once the lock is released. A run that is not to
wait is met by its end, and a held command is held by a pipe the test releases (`tests/support/lifeline.py` of the
no-wall-clock design spec), with no timeout. On Linux the I/O
priority is held to what the documented tool itself sets: the same probe, run under `ionice -c3`, gives the expected
state. On macOS the line is "`nice -n <k> -- <command>`, with no `taskpolicy -b`", so the expected state is the one the
probe gives with no tool. A child inherits its parent's I/O priority, and this suite's own wrapped run may already be
at the lowest, so the wrapper and each probe are started from the host's default I/O priority, and on Linux the probe
run from there with no tool must give a state other than the expected one.

Every documented heavy run is made under the wrapper, this suite's own among them, so the test process may already be
at niceness 19, and a probe would show it whatever the wrapper did. The spec has the wrapper run its command by the line
`nice -n <k> -- <command>` on macOS, "with no `taskpolicy -b`", and `ionice -c3 nice -n <k> -- <command>` on Linux, `k`
being 19 less
`niceness` floored at 0, `niceness` its own process's read with `os.getpriority(os.PRIO_PROCESS, 0)`, with each tool
found on `PATH`; so the niceness run puts a stand-in `nice` first on `PATH` that notes the arguments it is given and
then runs the real `nice` with them, and the step the wrapper takes is held by what the stand-in noted. A process cannot
lower its own niceness, so a suite already at 19 can start no wrapper below it; the wrapper is also run in a process
whose `os.nice` and `os.getpriority` report a niceness other than the suite's, and the step it takes is held to 19 less
the niceness reported, a caller at 19 or above getting `nice -n 0`.

The same bullet has "each tool is found on `PATH`" and "where a tool of the line is not on `PATH`, the wrapper runs
nothing and exits 2, since a heavy run is never made unthrottled". So on Linux a stand-in for `ionice` first on `PATH`
notes the arguments it is given and runs the rest of the line; on macOS a stand-in for `taskpolicy` first on `PATH` is
never run, the line having "no `taskpolicy -b`". A run whose `PATH` lacks a tool of the line is held to exit 2 with its
command never run: on Linux `ionice`, `nice` or both, on macOS `nice`.
"""

import contextlib
import fcntl
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.lifeline import HOLD, ready

REPO_ROOT = Path(__file__).parents[1]

WAIT = 5

NICENESS = "19"

HELD = "held"

RELEASED = "released"

SECOND = "second"

ARGUMENTS = ["two words", "--lock", "other"]

NOTE = "import sys\nwith open(sys.argv[1], 'a', encoding='utf-8') as log:\n    log.write(sys.argv[2] + '\\n')\n"

# Notes HELD in the log named by its second argument, then HOLDs on the fd named by its first, and notes RELEASED once
# that fd reaches its end.
HELD_CODE = (
    "import sys\n"
    "def note(word):\n"
    "    with open(sys.argv[2], 'a', encoding='utf-8') as log:\n"
    "        log.write(word + '\\n')\n"
    f"note({HELD!r})\n" + HOLD + f"note({RELEASED!r})\n"
)

# The descriptor the held command reads: its standard input, the release pipe's read end.
RELEASE_FD = "0"

EXIT = "import sys\nsys.exit(int(sys.argv[1]))\n"

ECHO = "import sys\nwith open(sys.argv[1], 'w', encoding='utf-8') as out:\n    out.write('\\n'.join(sys.argv[2:]))\n"

NICE = (
    "import os, sys\n"
    "with open(sys.argv[1], 'w', encoding='utf-8') as out:\n"
    "    out.write(str(os.getpriority(os.PRIO_PROCESS, 0)))\n"
)

# macOS: getpriority(PRIO_DARWIN_PROCESS = 4, self) and getiopolicy_np(IOPOL_TYPE_DISK = 0, IOPOL_SCOPE_PROCESS = 0).
DARWIN_IO = (
    "import ctypes, sys\n"
    "libc = ctypes.CDLL(None, use_errno=True)\n"
    "state = (libc.getpriority(4, 0), libc.getiopolicy_np(0, 0))\n"
    "with open(sys.argv[1], 'w', encoding='utf-8') as out:\n"
    "    out.write(repr(state))\n"
)

# Linux: the scheduling class and priority ionice reports for the probe's own process.
LINUX_IO = (
    "import os, subprocess, sys\n"
    "state = subprocess.run(['ionice', '-p', str(os.getpid())], capture_output=True, text=True, check=False).stdout\n"
    "with open(sys.argv[1], 'w', encoding='utf-8') as out:\n"
    "    out.write(state)\n"
)

IO_PROBE = {"darwin": DARWIN_IO, "linux": LINUX_IO}

# The tool that sets the I/O priority the spec has the command run at: "on Linux at the lowest I/O priority too". On
# macOS the line is "`nice -n <k> -- <command>`, with no `taskpolicy -b`", so no tool sets it.
IO_LOWEST: dict[str, list[str]] = {"darwin": [], "linux": ["ionice", "-c3"]}

# Whether the expected I/O state differs from the host's default: only Linux lowers it.
IO_LOWERED = {"darwin": False, "linux": True}

# macOS: setpriority(PRIO_DARWIN_PROCESS = 4, self, 0) leaves background, and setiopolicy_np(IOPOL_TYPE_DISK = 0,
# IOPOL_SCOPE_PROCESS = 0, IOPOL_DEFAULT = 0) takes the default disk policy; then the rest of the line runs.
DARWIN_LIFT = (
    "import ctypes, os, sys\n"
    "libc = ctypes.CDLL(None, use_errno=True)\n"
    "libc.setpriority(4, 0, 0)\n"
    "libc.setiopolicy_np(0, 0, 0)\n"
    "os.execvp(sys.argv[1], sys.argv[1:])\n"
)

# The host's default I/O priority, taken before the rest of the line runs: on Linux the best-effort class at its
# default level.
IO_LIFT = {"darwin": [sys.executable, "-c", DARWIN_LIFT], "linux": ["ionice", "-c2", "-n4"]}

# Runs the module named after the niceness, with the arguments after it, in a process whose os.nice and os.getpriority
# report that niceness.
REPORTS = (
    "import os, runpy, sys\n"
    "reported = int(sys.argv[1])\n"
    "os.nice = lambda increment: reported\n"
    "os.getpriority = lambda which, who: reported\n"
    "sys.argv = sys.argv[2:]\n"
    "runpy.run_module(sys.argv[0], run_name='__main__', alter_sys=True)\n"
)

# A niceness the wrapper's process reports, and the nice -n step the spec has it take: 19 less that niceness.
REPORTED = [(0, "19"), (12, "7"), (19, "0")]

REPORTED_IDS = ["at-0", "at-12", "at-19"]

REAL_NICE = "/usr/bin/nice"

SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

BLOCKED = 2

IO_TOOL = {"darwin": "taskpolicy", "linux": "ionice"}

IO_OPTION = "-c3"

# How many arguments each stand-in drops before running the rest: the I/O tool its option, nice its -n and step.
DROPS = {"io": 1, "nice": 2}


def _io_line(step: str, command: list[str]) -> list[str]:
    """The arguments the host's I/O tool is given, nice -n taking step: none on macOS, where the line is "`nice -n <k>
    -- <command>`, with no `taskpolicy -b`"."""
    return [IO_OPTION, "nice", "-n", step, "--", *command] if IO_LOWERED[sys.platform] else []


def _python(code: str, *arguments: str) -> list[str]:
    return [sys.executable, "-c", code, *arguments]


def _stand_in(tools: Path, name: str, record: Path, real: str) -> dict[str, str]:
    """Put in tools a stand-in named name that notes its arguments in record, then runs real with them.

    Returns the environment of a run that finds the stand-in first on PATH.
    """
    tools.mkdir(exist_ok=True)
    tool = tools / name
    tool.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{record}'\nexec '{real}' \"$@\"\n", encoding="utf-8")
    tool.chmod(0o755)
    return {"PATH": f"{tools}:{SYSTEM_PATH}"}


def _pass_on(tools: Path, name: str, record: Path, drop: int) -> None:
    """Put in tools a stand-in named name that notes its arguments in record, drops the first drop and runs the rest."""
    tools.mkdir(exist_ok=True)
    tool = tools / name
    tool.write_text(f"#!/bin/sh\nprintf '%s\\n' \"$@\" > '{record}'\nshift {drop}\nexec \"$@\"\n", encoding="utf-8")
    tool.chmod(0o755)


def _wrapped(lock: Path, command: list[str]) -> list[str]:
    """The wrapper's command line; the module is imported here, at each run, so a test and not collection meets it."""
    from gates import heavy

    return [sys.executable, "-m", heavy.__name__, "--lock", str(lock), *command]


def _reporting(lock: Path, reported: int, command: list[str]) -> list[str]:
    """The wrapper's command line, run in a process that reports its niceness as reported."""
    from gates import heavy

    return [sys.executable, "-c", REPORTS, str(reported), heavy.__name__, "--lock", str(lock), *command]


def _launch(line: list[str], env: dict[str, str] | None = None) -> int:
    """Run one line to its end from the repository root and return its exit status."""
    return subprocess.run(line, cwd=REPO_ROOT, check=False, env=env).returncode


def _run(lock: Path, command: list[str], env: dict[str, str] | None = None) -> int:
    """Run one wrapped command to its end and return the wrapper's exit status."""
    return _launch(_wrapped(lock, command), env)


def _start(lock: Path, command: list[str]) -> subprocess.Popen[bytes]:
    return subprocess.Popen(_wrapped(lock, command), cwd=REPO_ROOT)


def _settle(process: subprocess.Popen[bytes]) -> None:
    """Give a wrapped run WAIT seconds to end, and leave it running if it has not."""
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=WAIT)


def _end(process: subprocess.Popen[bytes]) -> None:
    """Wait for a wrapped run to end."""
    process.wait()


def _hold(lock: Path, log: Path) -> tuple[subprocess.Popen[bytes], int]:
    """Start a wrapped command that notes it is held, then runs until the returned descriptor is closed.

    Returns once the held command has noted itself, or once the wrapper has ended without running it.
    """
    release_read, release_write = os.pipe()
    ready_read, ready_write = os.pipe()
    process = subprocess.Popen(
        _wrapped(lock, _python(HELD_CODE, RELEASE_FD, str(log))),
        cwd=REPO_ROOT,
        stdin=release_read,
        stdout=ready_write,
    )
    os.close(release_read)
    os.close(ready_write)
    ready(ready_read)
    os.close(ready_read)
    return process, release_write


def _note(log: Path, word: str) -> None:
    with log.open("a", encoding="utf-8") as handle:
        handle.write(word + "\n")


def _lines(log: Path) -> list[str]:
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def test_second_run_waits(tmp_path: Path) -> None:
    """A second run wrapped on the same lock runs its command only after the first run's command has ended."""
    lock = tmp_path / "heavy.lock"
    log = tmp_path / "log"
    first, release = _hold(lock, log)
    second = _start(lock, _python(NOTE, str(log), SECOND))
    _settle(second)
    os.close(release)
    _end(first)
    _end(second)

    assert _lines(log) == [HELD, RELEASED, SECOND]


def test_other_lock_runs_beside(tmp_path: Path) -> None:
    """A run given another path by --lock runs its command while a run holding the first path is still running."""
    log = tmp_path / "log"
    first, release = _hold(tmp_path / "first.lock", log)
    second = _start(tmp_path / "second.lock", _python(NOTE, str(log), SECOND))
    _end(second)
    os.close(release)
    _end(first)

    assert _lines(log) == [HELD, SECOND, RELEASED]


def test_waits_on_flock(tmp_path: Path) -> None:
    """A run waits while another process holds fcntl.flock on the path given by --lock, and runs once it is released."""
    lock = tmp_path / "heavy.lock"
    log = tmp_path / "log"
    with lock.open("w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        process = _start(lock, _python(NOTE, str(log), SECOND))
        _settle(process)
        _note(log, RELEASED)
    _end(process)

    assert _lines(log) == [RELEASED, SECOND]


@pytest.mark.parametrize("status", [0, 3])
def test_exit_status(tmp_path: Path, status: int) -> None:
    """The wrapper exits with its command's exit status."""
    assert _run(tmp_path / "heavy.lock", _python(EXIT, str(status))) == status


def test_arguments(tmp_path: Path) -> None:
    """The command after --lock and its path runs with every argument it was given, one written like --lock among them."""
    out = tmp_path / "out"

    _run(tmp_path / "heavy.lock", _python(ECHO, str(out), *ARGUMENTS))

    assert _lines(out) == ARGUMENTS


@pytest.mark.parametrize(("reported", "step"), REPORTED, ids=REPORTED_IDS)
def test_niceness(tmp_path: Path, reported: int, step: str) -> None:
    """The command runs at niceness 19, by nice -n with 19 less the wrapper's own niceness: this process's, and the one
    the wrapper's process reports where it reports another."""
    out = tmp_path / "out"
    record = tmp_path / "nice"
    reported_record = tmp_path / "reported"
    env = _stand_in(tmp_path / "tools", "nice", record, REAL_NICE)
    reported_env = _stand_in(tmp_path / "reported_tools", "nice", reported_record, REAL_NICE)

    _run(tmp_path / "heavy.lock", _python(NICE, str(out)), env)
    _launch(_reporting(tmp_path / "heavy.lock", reported, _python("pass")), reported_env)

    assert (_lines(record)[:2], _lines(out), _lines(reported_record)[:2]) == (
        ["-n", str(max(0, int(NICENESS) - os.getpriority(os.PRIO_PROCESS, 0)))],
        [str(max(int(NICENESS), os.getpriority(os.PRIO_PROCESS, 0)))],
        ["-n", step],
    )


def test_io_priority(tmp_path: Path) -> None:
    """The command runs at the I/O priority the spec names when the wrapper starts from the host's default: on Linux the
    one ionice -c3 sets, which the default alone does not give; on macOS, with no taskpolicy -b, the default."""
    wrapped = tmp_path / "wrapped"
    reference = tmp_path / "reference"
    unwrapped = tmp_path / "unwrapped"
    probe = IO_PROBE[sys.platform]
    lift = IO_LIFT[sys.platform]
    subprocess.run([*lift, *IO_LOWEST[sys.platform], *_python(probe, str(reference))], check=False)
    subprocess.run([*lift, *_python(probe, str(unwrapped))], check=False)

    _launch([*lift, *_wrapped(tmp_path / "heavy.lock", _python(probe, str(wrapped)))])

    assert (_lines(wrapped), _lines(unwrapped) != _lines(reference)) == (_lines(reference), IO_LOWERED[sys.platform])


@pytest.mark.parametrize(("reported", "step"), REPORTED, ids=REPORTED_IDS)
def test_io_tool_on_path(tmp_path: Path, reported: int, step: str) -> None:
    """On Linux ionice is the one found first on PATH, given -c3, nice -n with 19 less the wrapper's own niceness, this
    process's and the one the wrapper's process reports where it reports another, and the command. On macOS a
    taskpolicy first on PATH is never run."""
    record = tmp_path / "io"
    reported_record = tmp_path / "reported"
    command = _python("pass")
    tools = tmp_path / "tools"
    reported_tools = tmp_path / "reported_tools"
    _pass_on(tools, IO_TOOL[sys.platform], record, DROPS["io"])
    _pass_on(reported_tools, IO_TOOL[sys.platform], reported_record, DROPS["io"])

    _run(tmp_path / "heavy.lock", command, {"PATH": f"{tools}:{SYSTEM_PATH}"})
    _launch(_reporting(tmp_path / "heavy.lock", reported, command), {"PATH": f"{reported_tools}:{SYSTEM_PATH}"})

    assert (_lines(record), _lines(reported_record)) == (
        _io_line(str(max(0, int(NICENESS) - os.getpriority(os.PRIO_PROCESS, 0))), command),
        _io_line(step, command),
    )


# The tools put on PATH in a run held to exit 2. The macOS case with only nice is removed: the line there is "`nice -n
# <k> -- <command>`, with no `taskpolicy -b`", so with nice on PATH no tool of the line is missing.
MISSING = {
    "darwin": ([[], ["io"]], ["neither", "only-io"]),
    "linux": ([[], ["nice"], ["io"]], ["neither", "only-nice", "only-io"]),
}


@pytest.mark.parametrize("present", MISSING[sys.platform][0], ids=MISSING[sys.platform][1])
def test_tool_missing(tmp_path: Path, present: list[str]) -> None:
    """Where a tool of the line is not on PATH, the wrapper runs nothing and exits 2."""
    log = tmp_path / "log"
    tools = tmp_path / "tools"
    tools.mkdir()
    for stand_in in present:
        name = IO_TOOL[sys.platform] if stand_in == "io" else stand_in
        _pass_on(tools, name, tmp_path / stand_in, DROPS[stand_in])

    status = _run(tmp_path / "heavy.lock", _python(NOTE, str(log), SECOND), {"PATH": str(tools)})

    assert (status, _lines(log)) == (BLOCKED, [])
