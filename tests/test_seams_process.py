# Copyright 2026 oh shit, gorillas!
"""Product process seam contracts from M2 launcher design, Order 8.

Design: docs/superpowers/specs/m2-launcher-kinds-design.md, `gauntlet/seams/process.py` and `gauntlet/seams/readiness.py`.
Commands carry argv as separate values and nothing splits or interprets shell text. run executes a child in the
Command's cwd with its env and returns status, captured streams and named outputs; pass-through mode preserves stdio.
A command past its timeout is reported timed out, its waits bounded through the injected readiness Clock. Failed starts
raise ProcessError. run/start own child sessions, termination and reaping on exceptions and interrupts; close is
idempotent. exec_command replaces the calling process with argv and exactly the env given. Every child is harmless and
every wait is a lifeline event; VirtualClock is the only clock.
"""

import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from gauntlet.core.errors import ProcessError
from gauntlet.seams.process import Command, run, start
from tests.support.clock import VirtualClock
from tests.support.lifeline import Beacon, Lifeline, Pids, Witness

if TYPE_CHECKING:
    from gauntlet.seams.readiness import Clock

ROOT = Path(__file__).resolve().parents[1]

# Shell text a shell would split, expand or chain; the child must see each value as one argument.
SHELL_TEXT = ("two words", "$HOME; echo split | cat", "'quoted' \"twice\"", "*")

# An environment complete in itself: the locale is pinned so the child's Python adds no variable of its own.
ENV = {"GAUNTLET_PROBE": "seen value", "LC_ALL": "C.UTF-8", "PYTHONCOERCECLOCALE": "0"}

DURING = "raised during the wait"

ECHO = "import json, sys\nprint(json.dumps(sys.argv[1:]))\n"

PLACE = "import json, os\nprint(json.dumps([os.getcwd(), dict(os.environ)], sort_keys=True))\n"

STREAMS = "import sys\nsys.stdout.write('to stdout')\nsys.stderr.write('to stderr')\nsys.exit(3)\n"

THROUGH = "import sys\nsys.stdout.write('through stdout')\nsys.stderr.write('through stderr')\n"

WRITES = "import pathlib, sys\npathlib.Path(sys.argv[1]).write_text('report body', encoding='utf-8')\n"

SESSION = "import os\nprint(os.getsid(0), os.getpid())\n"

IDENTITY = (
    "import json, os, sys\n"
    "print(os.getpid())\n"
    "print(json.dumps([sys.argv[1:], dict(os.environ)], sort_keys=True))\n"
)

EXEC = (
    "import json, sys\n"
    "from gauntlet.seams.process import exec_command\n"
    "exec_command(tuple(sys.argv[2:]), json.loads(sys.argv[1]))\n"
)

# A child that notes its pid in the file argv[4], opens the FIFO argv[1] to write and marks it, writes its ready line on
# fd argv[2], then reads fd argv[3] to EOF.
HELD = (
    "import os, sys\n"
    "with open(sys.argv[4], 'a', encoding='utf-8') as noted:\n"
    "    noted.write(f'{os.getpid()}\\n')\n"
    "witness = os.open(sys.argv[1], os.O_WRONLY)\n"
    "os.write(witness, b'held')\n"
    "os.write(int(sys.argv[2]), b'ready\\n')\n"
    "while os.read(int(sys.argv[3]), 65536):\n"
    "    pass\n"
)


def _python(code: str, *arguments: str) -> tuple[str, ...]:
    return (sys.executable, "-c", code, *arguments)


def _held(
    witness: Witness, beacon: Beacon, line: Lifeline, pids: Pids, *, timeout: float | None
) -> Command:
    return Command(
        argv=_python(
            HELD, str(witness.path), str(beacon.write_fd), str(line.read_fd), str(pids.path)
        ),
        cwd=pids.path.parent,
        timeout=timeout,
        pass_fds=(beacon.write_fd, line.read_fd),
    )


def _run(command: Command) -> object:
    return run(command, clock=VirtualClock())


def _start(command: Command) -> object:
    return start(command, clock=VirtualClock())


def _reaped(pid: int) -> bool:
    try:
        os.waitpid(pid, os.WNOHANG)
    except ChildProcessError:
        return True
    return False


# Joining argv into one string for a shell, or splitting any value, breaks this.
def test_argv_values_reach_the_child_unsplit(tmp_path: Path) -> None:
    """Each argv value, shell text included, arrives as exactly one argument."""
    completed = run(Command(argv=_python(ECHO, *SHELL_TEXT), cwd=tmp_path), clock=VirtualClock())

    assert (completed.status, completed.stdout) == (0, json.dumps(list(SHELL_TEXT)) + "\n")


# Splitting a value on whitespace, which runs echo instead of failing to start, breaks this.
def test_one_value_holding_a_command_line_is_not_split(tmp_path: Path) -> None:
    """A single argv value holding shell text names one executable, which does not exist."""
    with pytest.raises(ProcessError):
        run(Command(argv=("echo split",), cwd=tmp_path), clock=VirtualClock())


# Ignoring cwd, or merging the Command's env into the inherited one, breaks this.
def test_run_uses_the_command_cwd_and_its_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The child runs in the Command's cwd with the Command's env and nothing inherited."""
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.setenv("GAUNTLET_PARENT_ONLY", "inherited")
    completed = run(Command(argv=_python(PLACE), cwd=work, env=ENV), clock=VirtualClock())

    assert completed.stdout == json.dumps([str(work.resolve()), ENV], sort_keys=True) + "\n"


# Dropping the exit status, swapping or discarding a stream, or reporting a timeout breaks this.
def test_run_returns_status_and_captured_streams(tmp_path: Path) -> None:
    """A run returns the child's exit status and its captured stdout and stderr."""
    completed = run(Command(argv=_python(STREAMS), cwd=tmp_path), clock=VirtualClock())

    assert (completed.status, completed.stdout, completed.stderr, completed.timed_out) == (
        3,
        "to stdout",
        "to stderr",
        False,
    )


# Not reading a named output file back, or keying it by another name, breaks this.
def test_run_returns_named_outputs(tmp_path: Path) -> None:
    """A named output the child wrote is returned under its name."""
    report = tmp_path / "report.txt"
    completed = run(
        Command(argv=_python(WRITES, str(report)), cwd=tmp_path, outputs={"report": report}),
        clock=VirtualClock(),
    )

    assert (completed.status, dict(completed.outputs)) == (0, {"report": "report body"})


# Capturing the streams in pass-through mode breaks this.
def test_pass_through_preserves_stdio(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    """With capture off, the child writes to the caller's own stdout and stderr."""
    completed = run(
        Command(argv=_python(THROUGH), cwd=tmp_path, capture=False), clock=VirtualClock()
    )
    captured = capfd.readouterr()

    assert (completed.status, captured.out, captured.err) == (
        0,
        "through stdout",
        "through stderr",
    )


# Waiting on real time instead of the injected Clock, capping that wait at anything but the Command's timeout, leaving
# the child running or unreaped, or reporting no timeout breaks this.
@pytest.mark.parametrize(("timeout", "passed"), [(5, 5.0), (2.5, 2.5)], ids=["cap-5", "cap-2.5"])
def test_a_command_past_its_timeout_is_reported_timed_out_through_the_injected_clock(
    tmp_path: Path, timeout: float, passed: float
) -> None:
    """A held child past its timeout is ended and reaped; only the injected Clock's time passes, by the timeout."""
    with (
        Lifeline() as line,
        Beacon() as beacon,
        Witness(tmp_path / "witness.fifo") as witness,
        Pids(tmp_path / "pids.txt") as pids,
    ):
        clock = VirtualClock(passes=5, after=beacon.seen)
        injected: Clock = clock
        completed = run(_held(witness, beacon, line, pids, timeout=timeout), clock=injected)
        held = witness.ended()
        reaped = [_reaped(pid) for pid in pids.noted()]

    assert (completed.timed_out, clock.now, held, reaped) == (True, passed, b"held", [True])


# Returning a Completed, or letting OSError escape, for a child that never started breaks this.
@pytest.mark.parametrize(
    "launch",
    [
        pytest.param(_run, id="run"),
        pytest.param(_start, id="start"),
    ],
)
@pytest.mark.parametrize("missing", ["executable", "cwd"])
def test_failed_start_raises_process_error(
    tmp_path: Path, launch: Callable[[Command], object], missing: str
) -> None:
    """A missing executable or a missing cwd is a failed start."""
    if missing == "executable":
        command = Command(argv=(str(tmp_path / "absent"),), cwd=tmp_path)
    else:
        command = Command(argv=_python(ECHO), cwd=tmp_path / "absent")
    with pytest.raises(ProcessError):
        launch(command)


# Starting the child in the caller's session breaks this.
def test_child_leads_its_own_session(tmp_path: Path) -> None:
    """The child runs as the leader of a session of its own."""
    completed = run(Command(argv=_python(SESSION), cwd=tmp_path), clock=VirtualClock())
    session, pid = (int(word) for word in completed.stdout.split())

    assert (session, session == os.getsid(0)) == (pid, False)


# Leaving the child running, or unreaped, when the wait raises breaks this.
@pytest.mark.parametrize("raised", [KeyboardInterrupt, ValueError], ids=["interrupt", "exception"])
def test_run_ends_and_reaps_its_child_when_the_wait_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, raised: type[BaseException]
) -> None:
    """An interrupt or exception during the wait propagates after the child is ended and reaped."""
    with (
        Lifeline() as line,
        Beacon() as beacon,
        Witness(tmp_path / "witness.fifo") as witness,
        Pids(tmp_path / "pids.txt") as pids,
    ):

        def interrupt() -> None:
            beacon.seen()
            raise raised(DURING)

        clock = VirtualClock(passes=5, after=interrupt)
        monkeypatch.setattr(time, "monotonic", lambda: clock.now)
        with pytest.raises(raised, match=DURING):
            run(_held(witness, beacon, line, pids, timeout=5), clock=clock)
        held = witness.ended()
        reaped = [_reaped(pid) for pid in pids.noted()]

    assert (held, reaped) == (b"held", [True])


# Leaving a running child alive or unreaped on close, or failing on a second close, breaks this.
def test_close_ends_and_reaps_a_running_child_and_repeats_safely(tmp_path: Path) -> None:
    """Closing ends and reaps a running child; a second close does nothing."""
    with (
        Lifeline() as line,
        Beacon() as beacon,
        Witness(tmp_path / "witness.fifo") as witness,
        Pids(tmp_path / "pids.txt") as pids,
    ):
        child = start(_held(witness, beacon, line, pids, timeout=None), clock=VirtualClock())
        seen = beacon.seen()
        child.close()
        child.close()
        held = witness.ended()
        reaped = [_reaped(pid) for pid in pids.noted()]

    assert (seen, held, reaped) == (b"ready\n", b"held", [True])


# A started child's wait losing its status or stdout, or close failing after it finished, breaks this.
def test_a_started_child_waits_to_completion_and_closes_twice(tmp_path: Path) -> None:
    """Waiting returns the finished child's result; closing after it, twice, does nothing."""
    child = start(Command(argv=_python(ECHO, *SHELL_TEXT), cwd=tmp_path), clock=VirtualClock())
    completed = child.wait()
    child.close()
    child.close()

    assert (completed.status, completed.stdout) == (0, json.dumps(list(SHELL_TEXT)) + "\n")


# Spawning a new process instead of replacing this one, splitting argv, or adding inherited env breaks this.
def test_exec_command_replaces_the_process_with_argv_and_exactly_the_env() -> None:
    """The exec'd program runs as the calling pid, with argv unsplit and only the env given."""
    with subprocess.Popen(
        _python(EXEC, json.dumps(ENV), *_python(IDENTITY, *SHELL_TEXT)),
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ) as caller:
        assert caller.stdout is not None
        out = caller.stdout.read()
        status = caller.wait()

    assert (status, out) == (
        0,
        f"{caller.pid}\n{json.dumps([list(SHELL_TEXT), ENV], sort_keys=True)}\n",
    )
