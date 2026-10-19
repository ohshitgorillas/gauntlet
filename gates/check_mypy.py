"""mypy gate: type-check every Python file under the settings in `pyproject.toml`."""

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from mypy import api
from mypy.errors import SHOW_NOTE_CODES

from gates.check_suppressions import is_python_source
from gates.json_report import UnfinishedError

CONFIG = Path(__file__).resolve().parent.parent / "pyproject.toml"

FINISHED = frozenset({0, 1})

BLOCKED = 2

NOTE = "note"


class Record(TypedDict):
    """The part of one record of mypy's `--output json` report the gate reads; `hint` joins the notes on the finding."""

    file: str
    line: int
    message: str
    hint: str | None
    code: str | None
    severity: str


def parse(line: str, status: int, report: str) -> Record:
    """Read one line of mypy's `--output json` report, which holds one record as a JSON object, checking each field the gate reads.

    The record is checked, not trusted: a line that is not JSON, or a record missing a field the
    gate reads or holding one of another type than `Record` gives it, as when a mypy release
    renames, drops or retypes one, is no record the gate can read, and raises `UnfinishedError`
    with mypy's exit `status` and its whole `report`.
    """
    try:
        entry: object = json.loads(line)
    except json.JSONDecodeError as error:
        raise UnfinishedError(status, report) from error
    match entry:
        case {
            "file": str() as file,
            "line": int() as number,
            "message": str() as message,
            "hint": str() | None as hint,
            "code": str() | None as code,
            "severity": str() as severity,
        }:
            return Record(file=file, line=number, message=message, hint=hint, code=code, severity=severity)
        case _:
            raise UnfinishedError(status, report)


def describe(record: Record) -> str:
    """Render one record as mypy's own text report does, with its whole message, its code and each of its notes.

    A record of severity `note` shows its code only where mypy's text report shows one, for a code in `SHOW_NOTE_CODES`.
    """
    shown = record["code"] is not None and (record["severity"] != NOTE or record["code"] in SHOW_NOTE_CODES)
    code = f"  [{record['code']}]" if shown else ""
    notes = [] if record["hint"] is None else record["hint"].split("\n")
    return "\n".join([f"{record['file']}:{record['line']}: {record['severity']}: {record['message']}{code}", *(f"{record['file']}:{record['line']}: note: {note}" for note in notes)])


@dataclass(frozen=True)
class Verdict:
    """The outcome of one mypy run over a single Python file: the findings it printed there, and whether the check finished."""

    findings: int
    finished: bool


def show(records: list[Record], source: str) -> int:
    """Print each of `records` located in `source`, in report order, and return how many are findings, every record but a note."""
    located = [record for record in records if record["file"] == source]
    for record in located:
        sys.stdout.write(f"{describe(record)}\n")
    return len([record for record in located if record["severity"] != NOTE])


def read(report: str, status: int, source: str) -> Verdict:
    """Read mypy's JSON `report` of its check of `source`, which exited `status`, print the records located in `source`, and return the verdict.

    Every line of the report is read before any is printed, so a report the gate cannot read
    prints none of its records. Raise `UnfinishedError` when mypy gave no verdict the gate can
    read: a line of its report is no record the gate can read, or it exited other than 0 or 1
    without the sign of a blocking error, exit 2 with a record in its report.
    """
    records = [parse(line, status, report) for line in report.splitlines()]
    if status in FINISHED:
        return Verdict(show(records, source), finished=True)
    if status == BLOCKED and records:
        findings = show(records, source)
        sys.stdout.write(f"check_mypy: mypy stopped on a blocking error checking {source}\n")
        return Verdict(findings, finished=False)
    raise UnfinishedError(status, report)


def check(source: str) -> Verdict:
    """Type-check the Python file `source` in a mypy run of its own and print the records located in it.

    mypy follows its imports and checks what it imports, but a record is printed only when it
    lies in `source`. The findings are read from mypy's JSON report, one record per finding,
    and each is printed with its whole message, its code and its notes. A note mypy files at a
    location apart from the finding it explains comes as a record of its own, of severity
    `note`; it is never counted as a finding, and when it lies in `source` it is printed in its
    place in the report, as mypy's text report prints it. The verdict of a finished check is
    read from the printed findings, never from mypy's exit status: under `--output json` mypy
    exits 1 on any record at all, a lone note included, and only when its report holds at least
    one record. A blocking error, such as a syntax error, stops the check with exit 2, and mypy
    still writes it to its JSON report as a record: the records located in `source` are printed
    the same way, then a line saying the check of `source` stopped, and the check counts as
    unfinished, even when the blocking error lies only in an imported file it does not show.
    When mypy does not finish a check and its report holds no record, or writes a report with a
    line the gate cannot read, as a record missing a field the gate reads or holding one of
    another type, it gave no verdict the gate can read: its whole output is printed, then its
    exit status and `source`, and the check counts as unfinished.

    mypy runs without its cache: a cached module replays its findings under the path it had
    when cached, so a file moved with unchanged content, or a file sharing its module name and
    content with one checked before, would report under a path other than its own, and its
    findings would be dropped.
    """
    arguments = ["--config-file", str(CONFIG), "--cache-dir", os.devnull, "--show-absolute-path", "--no-error-summary", "--output", "json", source]
    report, errors, status = api.run(arguments)
    sys.stderr.write(errors)
    try:
        return read(report, status, source)
    except UnfinishedError as unread:
        sys.stdout.write("".join(f"{line}\n" for line in unread.output.splitlines()))
        sys.stdout.write(f"check_mypy: mypy exited {unread.status} on {source}\n")
        return Verdict(0, finished=False)


def main(paths: list[Path]) -> int:
    """Type-check each Python file among `paths` in a mypy run of its own and print the findings located in it.

    Each file is checked alone, so its verdict is the same whatever other files the tree holds:
    a file elsewhere with a syntax error, or one sharing its module name, never changes what is
    reported on it. A finding that lies only in a file a given one imports is neither printed nor
    counted, so the gate never fails on a finding it does not show; a run over every file of the
    tree gives that file too, and reports the finding there. When no path is a Python file,
    nothing was checked: print a line saying so and exit 1, so an empty file list never passes.
    Every run that checked a file ends on its count line, the one line that counts files, in the
    same shape whether or not every check finished. When every check finished, exit 1 on any
    finding and 0 on none. When any check did not finish, exit 2, whatever was found in the
    other files, since the checker could not finish on the tree.
    """
    sources = sorted({os.path.abspath(path) for path in paths if is_python_source(path)})
    if not sources:
        sys.stdout.write(f"check_mypy: no Python file among {len(paths)} path(s); nothing was checked\n")
        return 1
    verdicts = [check(source) for source in sources]
    findings = sum(verdict.findings for verdict in verdicts)
    unfinished = any(not verdict.finished for verdict in verdicts)
    sys.stdout.write(f"check_mypy: {findings} finding(s) in {len(sources)} Python file(s)\n")
    if unfinished:
        return BLOCKED
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
