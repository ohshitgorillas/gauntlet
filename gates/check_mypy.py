"""mypy gate: type-check every Python file under the settings in `pyproject.toml`."""

import json
from collections.abc import Sequence
from functools import partial
from pathlib import Path
from typing import TypedDict

from mypy.errors import SHOW_NOTE_CODES

from gates.core.checker import Command, Completed, python_module
from gates.core.project import Project, Source
from gates.core.report import Finding, GateError, Line, Remark, Unfinished
from gates.core.runner import Gate, Run, check_with, run_gate
from gates.core.runner import main as run_main

NOTE = "note"


class Record(TypedDict):
    """The part of one record of mypy's `--output json` report the gate reads; `hint` joins the notes on the finding."""

    file: str
    line: int
    message: str
    hint: str | None
    code: str | None
    severity: str


def record(line: str) -> Record:
    """Read one line of mypy's `--output json` report, which holds one record as a JSON object, checking each field the gate reads.

    The record is checked, not trusted: a line that is not JSON, or a record missing a field the gate reads or holding
    one of another type than `Record` gives it, as when a mypy release renames, drops or retypes one, is no record the
    gate can read, and raises GateError.
    """
    try:
        entry: object = json.loads(line)
    except json.JSONDecodeError as error:
        raise GateError(line) from error
    match entry:
        case {
            "file": str() as file,
            "line": int() as number,
            "message": str() as message,
            "hint": str() | None as hint,
            "code": str() | None as code,
            "severity": str() as severity,
        }:
            return Record(
                file=file,
                line=number,
                message=message,
                hint=hint,
                code=code,
                severity=severity,
            )
        case _:
            raise GateError(line)


def _texts(record: Record) -> list[str]:
    """The lines mypy's own text report gives the record: the record with its whole message and its code, then each of its notes.

    A record of severity `note` shows its code only where mypy's text report shows one, for a code in `SHOW_NOTE_CODES`.
    """
    shown_code = record["code"] is not None and (
        record["severity"] != NOTE or record["code"] in SHOW_NOTE_CODES
    )
    code = f"  [{record['code']}]" if shown_code else ""
    notes = [] if record["hint"] is None else record["hint"].split("\n")
    place = f"{record['file']}:{record['line']}"
    return [
        f"{place}: {record['severity']}: {record['message']}{code}",
        *(f"{place}: note: {note}" for note in notes),
    ]


def describe(record: Record) -> str:
    """Render one record as mypy's own text report does, one line for the record and one for each of its notes."""
    return "\n".join(_texts(record))


def shown(record: Record) -> list[Line]:
    """The record's lines for a finished check: a Finding for the record, a Remark when it is a note, and a Remark per note on it."""
    head, *notes = _texts(record)
    return [
        Remark(head) if record["severity"] == NOTE else Finding(head),
        *(Remark(note) for note in notes),
    ]


def _options(project: Project, cache: Path) -> tuple[str | Path, ...]:
    """The options every mypy run of the gate takes: the project's settings and the cache it reads and writes."""
    return ("--config-file", project.config, "--cache-dir", cache, "--no-error-summary")


def warm_cache(run: Run, directory: Path) -> None:
    """Warm the mypy cache in the directory with mypy on an empty program, which holds no repository file, through the run's process runner.

    Raises GateError unless mypy exits 0, prints nothing and leaves a file in the directory: its report is mypy's whole
    output, or, when mypy printed nothing, the gate's line naming the cache it could not warm.
    """
    completed = run.process(
        python_module(
            "mypy", *_options(run.project, directory), "-c", "", cwd=run.project.root
        )
    )
    if completed.output():
        raise GateError(completed.output())
    if completed.status != 0:
        raise GateError(
            f"cannot warm the mypy cache in {directory}: mypy exited {completed.status}"
        )
    if not any(path.is_file() for path in directory.rglob("*")):
        raise GateError(
            f"cannot warm the mypy cache in {directory}: mypy left no file there"
        )


class Mypy:
    """mypy as a child process, one per Python file, each from its own copy of the run's one warm cache.

    mypy follows its imports and checks what it imports, but a finished check gives a record only when it lies in the
    file checked; a note is a Remark, never a finding. A cached module replays its findings under the path it had when
    cached, so each file starts from its own copy of a cache warmed on no repository file, and none is ever replayed.
    """

    stopped: frozenset[int] = frozenset(
        {2}
    )  # a blocking error stops mypy; its records still stand

    def batches(self, run: Run) -> list[list[Source]]:
        """One mypy per file: no verdict depends on another file."""
        return [[source] for source in run.sources]

    def command(self, run: Run, batch: Sequence[Source]) -> Command:
        """mypy over the batch's one file, from its own copy of the warm cache, as a JSON report with absolute paths."""
        warm = run.scratch.once("warm", partial(warm_cache, run))
        return python_module(
            "mypy",
            *_options(run.project, run.scratch.copy(warm, "cache")),
            "--show-absolute-path",
            "--output",
            "json",
            batch[0].absolute,
            cwd=run.project.root,
        )

    def read(self, completed: Completed) -> list[Record]:
        """The records of mypy's JSON report; GateError on a line that holds none."""
        return [record(line) for line in completed.stdout.splitlines()]

    def expected_status(self, report: list[Record]) -> int:
        """mypy exits 1 when its report holds a record and 0 when it holds none: exit 1 with no record is a refusal, not a pass."""
        return 1 if report else 0

    def lines(
        self, report: list[Record], batch: Sequence[Source], *, stopped: bool
    ) -> list[Line]:
        """A stop gives every record, wherever it lies, as unfinished; a finish gives the records in the batch's file."""
        if stopped:
            return [Unfinished(describe(entry)) for entry in report]
        here = str(batch[0].absolute)
        return [
            line for entry in report if entry["file"] == here for line in shown(entry)
        ]


GATE: Gate = Gate(name="check_mypy", check=check_with(Mypy()))


def main(paths: Sequence[Path]) -> int:
    """Run the gate over the paths, in the working directory's project, and return its exit code."""
    return run_gate(GATE, paths)


if __name__ == "__main__":
    run_main(GATE)
