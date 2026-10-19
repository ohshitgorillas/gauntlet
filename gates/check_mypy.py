"""mypy gate: type-check every Python file under the settings in `pyproject.toml`."""

import json
import os
import sys
from pathlib import Path
from typing import TypedDict

from mypy import api
from mypy.errors import SHOW_NOTE_CODES

from gates.check_suppressions import is_python_source

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


def parse(line: str) -> Record:
    """Read one line of mypy's `--output json` report, which holds one record as a JSON object."""
    record: Record = json.loads(line)
    return record


def describe(record: Record) -> str:
    """Render one record as mypy's own text report does, with its whole message, its code and each of its notes.

    A record of severity `note` shows its code only where mypy's text report shows one, for a code in `SHOW_NOTE_CODES`.
    """
    shown = record["code"] is not None and (record["severity"] != NOTE or record["code"] in SHOW_NOTE_CODES)
    code = f"  [{record['code']}]" if shown else ""
    notes = [] if record["hint"] is None else record["hint"].split("\n")
    return "\n".join([f"{record['file']}:{record['line']}: {record['severity']}: {record['message']}{code}", *(f"{record['file']}:{record['line']}: note: {note}" for note in notes)])


def show(report: str, sources: list[str]) -> list[Record]:
    """Print each record of `report` located in one of `sources`, in report order, and return the findings among them, every record but a note."""
    given = frozenset(sources)
    located = [record for record in (parse(line) for line in report.splitlines()) if record["file"] in given]
    for record in located:
        sys.stdout.write(f"{describe(record)}\n")
    return [record for record in located if record["severity"] != NOTE]


def unread(report: str, status: int, count: int) -> int:
    """Print the whole output of a mypy run that gave no verdict, then a count line saying so, and return mypy's exit status."""
    sys.stdout.write("".join(f"{line}\n" for line in report.splitlines()))
    sys.stdout.write(f"check_mypy: mypy exited {status} with no verdict on {count} Python file(s)\n")
    return status


def main(paths: list[Path]) -> int:
    """Type-check the Python files among `paths` and print the findings located in them.

    mypy follows their imports and checks what they import, but a finding is reported only
    when it lies in one of the given files. The findings are read from mypy's JSON report, one
    record per finding, and each is printed with its whole message, its code and its notes.
    A note mypy files at a location apart from the finding it explains comes as a record of
    its own, of severity `note`; it is never counted as a finding, and when it lies in one of
    the given files it is printed in its place in the report, as mypy's text report prints it.
    Exit 1 on any such finding and 0 on none. A finding that lies only in a file the given ones
    import is neither printed nor counted, so the gate never fails on a finding it does not
    show; a run over every file of the tree gives that file too, and reports the finding there.
    The verdict of a finished check is read from the printed findings, never from mypy's exit
    status: under `--output json` mypy exits 1 on any record at all, a lone note included, and
    only when its report holds at least one record. A blocking error, such as a syntax error,
    stops the check with exit 2, and mypy still writes it to its JSON report as a record: the
    records located in the given files are printed the same way, then a count line saying the
    check stopped, and the gate returns 2, failing even when the blocking error lies only in an
    imported file it does not show, since the check of the given files never finished. When
    mypy does not finish a check and its report holds no record, it gave no verdict the gate can
    read: print its whole output and a count line saying so, and return its exit status.

    mypy runs without its cache: a cached module replays its findings under the path it had
    when cached, so a file moved with unchanged content would report under a path no longer
    given, and its findings would be dropped.
    """
    sources = [os.path.abspath(path) for path in paths if is_python_source(path)]
    arguments = ["--config-file", str(CONFIG), "--cache-dir", os.devnull, "--show-absolute-path", "--no-error-summary", "--output", "json", *sources]
    report, errors, status = api.run(arguments)
    sys.stderr.write(errors)
    if status in FINISHED:
        findings = show(report, sources)
        sys.stdout.write(f"check_mypy: {len(findings)} finding(s) in {len(sources)} Python file(s)\n")
        return 1 if findings else 0
    if status == BLOCKED and report:
        findings = show(report, sources)
        sys.stdout.write(f"check_mypy: mypy stopped on a blocking error with {len(findings)} finding(s) in {len(sources)} Python file(s)\n")
        return status
    return unread(report, status, len(sources))


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
