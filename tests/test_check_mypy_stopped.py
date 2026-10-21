"""Red tests for the mypy gate's stopped path: every record of a stop is unfinished, wherever it lies, once per run.

Source: the gates core design spec under docs/superpowers/specs/, section 2, `Mypy.lines` ("every record, wherever it
lies, once per run"), section 4 "In-flight work" (g1l's `show_blocked` becomes mypy's `stopped` path plus the
once-per-run rule), report.py's `render` ("each Unfinished text once per run") and decision 21; the quality gates
design spec, "Gates", the sub-bullet's sentence: "A status the checker documents as a stop whose report still stands,
as mypy's 2 on a blocking error, is not a finish either, and the gate prints the report it read."

A stopped batch's lines are one Unfinished per record it read, in the order read, whatever file the record lies in and
whatever its severity; the gate prints each such text once per run, counts none of them as a finding, and exits 2.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from gates.check_mypy import GATE, Mypy, Record
from gates.core.checker import Command, Completed
from gates.core.project import Source
from gates.core.report import Line
from gates.core.runner import run_gate
from tests.support.capture import captured
from tests.support.fake import FakeRunner, completed
from tests.support.project import scaffold

IMPORTER = "import broken\n"

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


def _record(file: Path, message: str, severity: str = "error", code: str | None = "misc") -> Record:
    return Record(file=str(file), line=3, message=message, hint=None, code=code, severity=severity)


def _batch(tmp_path: Path) -> list[Source]:
    return [Source(given=Path("here.py"), absolute=tmp_path / "here.py")]


def _kind_and_message(line: Line, records: Sequence[Record]) -> tuple[str, str | None]:
    """The line's kind, and the message of the first seeded record whose file and message its text both carry."""
    for record in records:
        if record["message"] in line.text and record["file"] in line.text:
            return (type(line).__name__, record["message"])
    return (type(line).__name__, None)


def _mypy_json(file: Path, message: str, *, sort_keys: bool = False) -> str:
    """One record as mypy's `--output json` prints it, on its own line."""
    entry: dict[str, object] = {
        "file": str(file),
        "line": 1,
        "column": 7,
        "message": message,
        "hint": None,
        "code": "syntax",
        "severity": "error",
    }
    return json.dumps(entry, sort_keys=sort_keys) + "\n"


def test_a_stop_gives_every_record_wherever_it_lies_as_unfinished(tmp_path: Path) -> None:
    """A stopped batch's lines are one Unfinished per record, in order: one in the batch's file and one in another."""
    here = _record(tmp_path / "here.py", HERE_MESSAGE, code="return-value")
    there = _record(tmp_path / "broken.py", THERE_MESSAGE, code="syntax")

    result = Mypy().lines([here, there], _batch(tmp_path), stopped=True)

    assert [_kind_and_message(line, [here, there]) for line in result] == [
        ("Unfinished", HERE_MESSAGE),
        ("Unfinished", THERE_MESSAGE),
    ]


def test_a_note_in_a_stop_is_unfinished_too(tmp_path: Path) -> None:
    """A note mypy reported before it stopped is a record of the stop like any other: an Unfinished, not a Remark."""
    note = _record(tmp_path / "here.py", NOTE_MESSAGE, severity="note", code=None)

    result = Mypy().lines([note], _batch(tmp_path), stopped=True)

    assert [_kind_and_message(line, [note]) for line in result] == [("Unfinished", NOTE_MESSAGE)]


def test_one_blocking_error_two_files_stop_on_prints_once(tmp_path: Path) -> None:
    """Two files that both stop on one imported module's blocking error print it once, count no finding, and exit 2.

    The two mypy runs print the same record with its keys in a different order, so each run's whole output differs
    while the record each reads is the same.
    """
    project = scaffold(tmp_path / "project", {"first.py": IMPORTER, "second.py": IMPORTER})
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

    assert (output.result, sum(BLOCKER_MESSAGE in line for line in output.merged), output.merged[-1]) == (
        2,
        1,
        COUNT_TWO,
    )
