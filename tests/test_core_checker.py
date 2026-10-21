"""Red tests for running a checker process: what `run` gives back from the Command it is handed.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process".
A `Command` carries `argv`, `cwd`, `env` and `outputs: Mapping[str, Path]`; `run(command)` starts the checker and gives
back a `Completed(status, stdout, stderr, timed_out, outputs)`, its "status as a shell reports it". "`outputs` names the
files a checker writes, such as pytest's JUnit XML or mutmut's coverage record. `run` reads them back into
`Completed.outputs`", whose values are `str | None`: the text of each file the checker wrote, and None for one it did not.

A shell reports a process that exited by its exit code, so a checker that exits 3 has status 3. A shell reports a process
a signal ended as a status greater than 128 (POSIX, "Exit Status for Commands"); the exact value above 128 differs from
shell to shell and the documents do not name the shell, so a checker a signal ended is held only to a status above 128,
which a negative signal number never is.

`Completed` holds `stdout` and `stderr` as two fields, and the quality-gates design spec's "Gates" bullet names the
checker's whole output as "stdout and stderr", so each is held to its own stream's text alone. A Command's `cwd` and
`env` are where and with what the checker starts, so a checker run with them reads them back; an `env` is the checker's
whole environment, as `environment(drop_prefixes=("PYTEST_",))` handed to mutmut makes it, so a variable of the running
process that `env` leaves out never reaches the checker. What `run` does on a timeout, an interrupt, a program that
cannot start, a throttled run, an uncaptured run or passed descriptors are other behaviors, and no test here holds them.
"""

import sys
from collections.abc import Mapping
from pathlib import Path

import pytest

from gates.core.checker import Command, Completed, run

# A shell reports a process a signal ended as a status greater than this.
SIGNAL_FLOOR = 128

EXIT = "import sys\nsys.exit(int(sys.argv[1]))\n"

KILLED = "import os, signal\nos.kill(os.getpid(), signal.SIGKILL)\n"

OUT = "check: on stdout\nsecond stdout line\n"

ERR = "check: on stderr\nsecond stderr line\n"

BOTH = "import sys\nsys.stdout.write(sys.argv[1])\nsys.stdout.flush()\nsys.stderr.write(sys.argv[2])\n"

REPORT = '<?xml version="1.0"?>\n<testsuites><testsuite name="t" tests="1"/></testsuites>\n'

OTHER_REPORT = '{"mutants": ["a.x__mutmut_1"]}\n'

WRITE = "import sys\nwith open(sys.argv[1], 'w', encoding='utf-8') as out:\n    out.write(sys.argv[2])\n"

WHERE = "import os, sys\nsys.stdout.write(os.getcwd())\n"

PROBE = "GATE_CHECKER_PROBE"

PROBE_VALUE = "probe-value-17"

# pytest sets this in its own process's environment while each test runs, so it is there for `run` to leak.
PYTEST_VARIABLE = "PYTEST_CURRENT_TEST"

SEES = "import os, sys\nsys.stdout.write(repr(tuple(os.environ.get(name) for name in sys.argv[1:])))\n"


def _python(code: str, *arguments: str) -> tuple[str, ...]:
    return (sys.executable, "-c", code, *arguments)


def _run(
    cwd: Path,
    argv: tuple[str, ...],
    outputs: Mapping[str, Path] | None = None,
    env: Mapping[str, str] | None = None,
) -> Completed:
    """Run argv in cwd through `run`, naming outputs where given."""
    return run(Command(argv=argv, cwd=cwd, env=env, outputs=outputs or {}))


@pytest.mark.parametrize("code", [1, 3, 70])
def test_exit_status(tmp_path: Path, code: int) -> None:
    """A checker that exits with a code has that code as its status, as a shell reports it."""
    assert _run(tmp_path, _python(EXIT, str(code))).status == code


def test_signal_status(tmp_path: Path) -> None:
    """A checker a signal ended has a status greater than 128, as a shell reports it, never a negative signal number."""
    assert _run(tmp_path, _python(KILLED)).status > SIGNAL_FLOOR


def test_stdout(tmp_path: Path) -> None:
    """Completed.stdout holds exactly the text the checker wrote to its stdout, none of its stderr."""
    assert _run(tmp_path, _python(BOTH, OUT, ERR)).stdout == OUT


def test_stderr(tmp_path: Path) -> None:
    """Completed.stderr holds exactly the text the checker wrote to its stderr, none of its stdout."""
    assert _run(tmp_path, _python(BOTH, OUT, ERR)).stderr == ERR


def test_output_written(tmp_path: Path) -> None:
    """A file the Command's outputs names, which the checker wrote, is read back as its text under its name."""
    report = tmp_path / "junit.xml"

    completed = _run(tmp_path, _python(WRITE, str(report), REPORT), {"junit": report})

    assert completed.outputs == {"junit": REPORT}


def test_output_unwritten(tmp_path: Path) -> None:
    """A file the Command's outputs names, which the checker never wrote, is None under its name."""
    completed = _run(tmp_path, _python(EXIT, "0"), {"junit": tmp_path / "junit.xml"})

    assert completed.outputs == {"junit": None}


def test_outputs_by_name(tmp_path: Path) -> None:
    """Of three named files, the two the checker wrote are read under their own names and the third is None."""
    junit = tmp_path / "junit.xml"
    record = tmp_path / "record.json"
    write_both = (
        "import sys\n"
        "for path, text in ((sys.argv[1], sys.argv[2]), (sys.argv[3], sys.argv[4])):\n"
        "    with open(path, 'w', encoding='utf-8') as out:\n"
        "        out.write(text)\n"
    )
    outputs = {"junit": junit, "record": record, "missing": tmp_path / "missing.txt"}

    completed = _run(tmp_path, _python(write_both, str(junit), REPORT, str(record), OTHER_REPORT), outputs)

    assert completed.outputs == {"junit": REPORT, "record": OTHER_REPORT, "missing": None}


def test_cwd(tmp_path: Path) -> None:
    """The checker starts in the Command's cwd."""
    place = tmp_path / "place"
    place.mkdir()

    assert _run(place, _python(WHERE)).stdout == str(place.resolve())


def test_env(tmp_path: Path) -> None:
    """A checker run with an env sees what that env sets and no variable of this process it leaves out."""
    completed = _run(tmp_path, _python(SEES, PROBE, PYTEST_VARIABLE), env={PROBE: PROBE_VALUE})

    assert completed.stdout == repr((PROBE_VALUE, None))
