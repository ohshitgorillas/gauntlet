"""Red tests for the mypy gate's stopped path: every record of a stop is unfinished, wherever it lies, once per run.

Source: the gates core design spec under docs/superpowers/specs/, section 2, `Mypy.lines` ("every record, wherever it
lies, once per run"), section 4 "In-flight work" (g1l's `show_blocked` becomes mypy's `stopped` path plus the
once-per-run rule), report.py's `render` ("each Unfinished text once per run") and decision 21; the quality gates
design spec, "Gates", the sub-bullet's sentence: "A status the checker documents as a stop whose report still stands,
as mypy's 2 on a blocking error, is not a finish either, and the gate prints the report it read."

A stopped batch's lines are one Unfinished per record it read, in the order read, whatever file the record lies in and
whatever its severity; the gate prints each such text once per run, counts none of them as a finding, and exits 2. Each
stop is driven through `run_gate`, its mypy run answered by a canned reply of exit 2 and the records mypy printed.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from gates.check_mypy import GATE
from gates.core.checker import Command, Completed
from gates.core.runner import run_gate
from tests.support.capture import captured
from tests.support.fake import FakeRunner, completed
from tests.support.project import scaffold

IMPORTER = "import broken\n"

COUNT_ONE = "check_mypy: 0 finding(s) in 1 Python file(s)\n"

COUNT_TWO = "check_mypy: 0 finding(s) in 2 Python file(s)\n"

HERE_MESSAGE = 'Incompatible return value type (got "str", expected "int")'

THERE_MESSAGE = "Unexpected indent"

NOTE_MESSAGE = 'Revealed type is "builtins.int"'

BLOCKER_MESSAGE = "Unmatched ')'"

# mypy's exit status for a blocking error: a stop whose report still stands.
STOP = 2

# The warm run's reply: exit 0 and nothing printed.
WARM = completed(0)


class CacheLeavingRunner:
    """A Runner that leaves a file in each empty directory under the scratch root, then gives the next canned reply."""

    def __init__(self, scratch: Path, replies: Sequence[Completed]) -> None:
        self.scratch = scratch
        self.replies = FakeRunner(replies)

    def __call__(self, command: Command) -> Completed:
        for directory in list(self.scratch.rglob("*")):
            if directory.is_dir() and not any(directory.iterdir()):
                (directory / "cache.json").write_text("{}\n", encoding="utf-8")
        return self.replies(command)


def _carried(line: str, records: Sequence[tuple[Path, str]]) -> str | None:
    """The message of the first seeded record whose file and message the printed line both carry, else None."""
    for file, message in records:
        if message in line and str(file) in line:
            return message
    return None


def _mypy_json(
    file: Path,
    message: str,
    *,
    sort_keys: bool = False,
    severity: str = "error",
    code: str | None = "syntax",
) -> str:
    """One record as mypy's `--output json` prints it, on its own line."""
    entry: dict[str, object] = {
        "file": str(file),
        "line": 1,
        "column": 7,
        "message": message,
        "hint": None,
        "code": code,
        "severity": severity,
    }
    return json.dumps(entry, sort_keys=sort_keys) + "\n"


def _stop(tmp_path: Path, stdout: str) -> tuple[int, list[str]]:
    """Run the gate over here.py of a scaffolded project: the warm, then one mypy run that stops having printed `stdout`."""
    project = scaffold(tmp_path / "project", {"here.py": IMPORTER})
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    runner = CacheLeavingRunner(scratch, [WARM, completed(STOP, stdout)])
    output = captured(
        lambda: run_gate(
            GATE,
            [project.root / "here.py"],
            project=project,
            process=runner,
            scratch_root=scratch,
        )
    )
    return output.result, output.merged


def test_a_stop_gives_every_record_wherever_it_lies_as_unfinished(
    tmp_path: Path,
) -> None:
    """A stop prints each record it read once, in order, one in the batch's file and one in another; none counts; exit 2."""
    here = tmp_path / "project" / "here.py"
    there = tmp_path / "project" / "broken.py"
    records = [(here, HERE_MESSAGE), (there, THERE_MESSAGE)]

    status, lines = _stop(
        tmp_path,
        _mypy_json(here, HERE_MESSAGE, code="return-value")
        + _mypy_json(there, THERE_MESSAGE),
    )

    assert (status, [_carried(line, records) for line in lines], lines[-1]) == (
        2,
        [HERE_MESSAGE, THERE_MESSAGE, None],
        COUNT_ONE,
    )


def test_a_note_in_a_stop_is_unfinished_too(tmp_path: Path) -> None:
    """A note mypy reported before it stopped is a record of the stop like any other: printed once, not counted, exit 2."""
    here = tmp_path / "project" / "here.py"

    status, lines = _stop(
        tmp_path, _mypy_json(here, NOTE_MESSAGE, severity="note", code=None)
    )

    assert (status, [_carried(line, [(here, NOTE_MESSAGE)]) for line in lines], lines[-1]) == (
        2,
        [NOTE_MESSAGE, None],
        COUNT_ONE,
    )


def test_one_blocking_error_two_files_stop_on_prints_once(tmp_path: Path) -> None:
    """Two files that both stop on one imported module's blocking error print it once, count no finding, and exit 2.

    The two mypy runs print the same record with its keys in a different order, so each run's whole output differs
    while the record each reads is the same.
    """
    project = scaffold(
        tmp_path / "project", {"first.py": IMPORTER, "second.py": IMPORTER}
    )
    broken = project.root / "broken.py"
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    runner = CacheLeavingRunner(
        scratch,
        [
            WARM,
            completed(STOP, _mypy_json(broken, BLOCKER_MESSAGE)),
            completed(STOP, _mypy_json(broken, BLOCKER_MESSAGE, sort_keys=True)),
        ],
    )

    output = captured(
        lambda: run_gate(
            GATE,
            [project.root / "first.py", project.root / "second.py"],
            project=project,
            process=runner,
            scratch_root=scratch,
        )
    )

    assert (
        output.result,
        sum(BLOCKER_MESSAGE in line for line in output.merged),
        output.merged[-1],
    ) == (
        2,
        1,
        COUNT_TWO,
    )
