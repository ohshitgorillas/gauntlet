"""Red tests for a throttled Command: `run` starts it under this host's throttle line, and an unthrottled one as its argv says.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`Command` carries `throttled: bool = False`, `throttle_line(platform, niceness)` is "heavy's line", `run` replaces
"heavy's `wrapped`, `missing` and `status`, and its subprocess call", and "A throttled `run` looks its tools up on the
PATH of `Command.env`, and on os.environ's PATH when `env` is None, so a test sets PATH in-process through `env`";
section 2 starts the mutation run as `Command(..., throttled=True, ...)`. Heavy's line is the agents design spec's, under
"Decisions", the bullet on heavy runs: it "runs that command at niceness 19, and on Linux at the lowest I/O priority
too", where `platform` is the host as `sys.platform` names it and `niceness` is the caller's own: "on Linux `ionice -c3
nice -n <k> -- <command>`, on macOS `nice -n <k> -- <command>`, ... where `k` is 19 - niceness, ... and a caller at 19 or
above ... gets `nice -n 0`; the `--` ends `nice`'s options, so any command is run as given, ...; each tool is found on
`PATH`".

The line is observed through stand-in `nice` and `ionice` executables in one directory, handed to `run` as the PATH of
the Command's `env`: each appends its name and its arguments, one line, to a log, then runs the command after its own
options, and the checker appends its own name and arguments too. `run` is called in this process, whose niceness the
test reads and does not change, so the `k` it expects is 19 less that niceness, floored at 0.

A throttled checker started with the host's own `nice` runs at niceness 19. A child inherits its caller's niceness, so
at 19 that alone holds with no throttle; the stand-in `nice` that logs its call and then runs the host's own, found by
POSIX `command -p` on the standard PATH, shows the throttle was applied whatever niceness the test runs at.
"""

import os
import shlex
import sys
from pathlib import Path

from gates.core.checker import Command, run

EXECUTABLE = 0o755

LOW_PRIORITY = "19"

ARGUMENTS = ("-q", "report")

SKIP_TO_COMMAND = (
    'while [ $# -gt 0 ] && [ "$1" != "--" ]; do shift; done\nshift\nexec "$@"\n'
)

SKIP_OPTIONS = (
    'while [ $# -gt 0 ]; do case "$1" in -*) shift;; *) break;; esac; done\nexec "$@"\n'
)

FINISH = "exit 0\n"

HOST_NICE = 'command -p nice "$@"\n'

NICENESS = "import os, sys; sys.stdout.write(str(os.getpriority(os.PRIO_PROCESS, 0)))"


def _recorder(path: Path, log: Path, rest: str) -> None:
    """Write an executable at path that appends its name and arguments, tab-separated, to log, then runs rest."""
    record = (
        f"{{ printf '%s' {shlex.quote(path.name)}; "
        "for word in \"$@\"; do printf '\\t%s' \"$word\"; done; printf '\\n'; } "
        f">> {shlex.quote(str(log))}\n"
    )
    path.write_text("#!/bin/sh\n" + record + rest, encoding="utf-8")
    path.chmod(EXECUTABLE)


def _logged(*words: str) -> str:
    return "\t".join(words)


def _step() -> str:
    """The nice step this process's own niceness gives: 19 less it, floored at 0."""
    return str(max(0, 19 - os.getpriority(os.PRIO_PROCESS, 0)))


def _run(tmp_path: Path, throttled: bool) -> tuple[int, list[str], Path]:
    """Run the checker through `run` with an env whose PATH holds only the stand-in tools; return status and log."""
    tools = tmp_path / "bin"
    tools.mkdir()
    log = tmp_path / "log.txt"
    _recorder(tools / "nice", log, SKIP_TO_COMMAND)
    _recorder(tools / "ionice", log, SKIP_OPTIONS)
    checker = tmp_path / "checker"
    _recorder(checker, log, FINISH)
    command = Command(
        argv=(str(checker), *ARGUMENTS),
        cwd=tmp_path,
        env={"PATH": str(tools)},
        throttled=throttled,
    )
    completed = run(command)
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return completed.status, lines, checker


def test_throttled_line(tmp_path: Path) -> None:
    """A throttled Command runs under this host's line, nice -n k -- (after ionice -c3 on Linux), then its argv."""
    step = _step()
    status, lines, checker = _run(tmp_path, throttled=True)
    argv = (str(checker), *ARGUMENTS)
    nice = _logged("nice", "-n", step, "--", *argv)
    started = _logged("checker", *ARGUMENTS)
    expected = {
        "darwin": [nice, started],
        "linux": [
            _logged("ionice", "-c3", "nice", "-n", step, "--", *argv),
            nice,
            started,
        ],
    }

    assert (status, lines) == (0, expected[sys.platform])


def test_unthrottled_as_argv(tmp_path: Path) -> None:
    """An unthrottled Command starts its argv as given, with neither nice nor ionice before it."""
    status, lines, _ = _run(tmp_path, throttled=False)

    assert (status, lines) == (0, [_logged("checker", *ARGUMENTS)])


def test_throttled_low_priority(tmp_path: Path) -> None:
    """A throttled checker, started under the host's own nice through this host's line, runs at niceness 19."""
    step = _step()
    tools = tmp_path / "bin"
    tools.mkdir()
    log = tmp_path / "log.txt"
    _recorder(tools / "nice", log, HOST_NICE)
    _recorder(tools / "ionice", log, SKIP_OPTIONS)
    argv = (sys.executable, "-c", NICENESS)
    completed = run(
        Command(argv=argv, cwd=tmp_path, env={"PATH": str(tools)}, throttled=True)
    )
    lines = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    nice = _logged("nice", "-n", step, "--", *argv)
    expected = {
        "darwin": [nice],
        "linux": [_logged("ionice", "-c3", "nice", "-n", step, "--", *argv), nice],
    }

    assert (completed.stdout, lines) == (LOW_PRIORITY, expected[sys.platform])
