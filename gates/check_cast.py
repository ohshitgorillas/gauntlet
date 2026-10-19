"""Cast gate: fail on any use of `typing.cast`, found by ruff's `TID251` under the banned API in `pyproject.toml`."""

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from gates.check_suppressions import is_python_source
from gates.json_report import UnfinishedError, is_list, load, print_unread

CONFIG = Path(__file__).resolve().parent.parent / "pyproject.toml"

BLOCKED = 2

REPORTED = frozenset({"TID251"})

UNFINISHED = frozenset({"E902", "invalid-syntax"})


class Location(TypedDict):
    """A one-based place in a file, as ruff's JSON report gives it."""

    row: int
    column: int


class Violation(TypedDict):
    """The part of one entry of ruff's `--output-format json` report the gate reads.

    ruff's schema lets `code` be null, but an entry with no code names no rule the gate can
    classify, so the gate reads it as no verdict, never as a finding or an unfinished file.
    """

    code: str
    message: str
    filename: str
    location: Location


def describe(violation: Violation) -> str:
    """Render one violation as ruff's own concise report does, with its whole message and its code."""
    location = violation["location"]
    return f"{violation['filename']}:{location['row']}:{location['column']}: {violation['code']} {violation['message']}"


@dataclass(frozen=True)
class Report:
    """The gate's reading of one JSON report ruff wrote: its findings, and the entries for each file ruff could not read or parse."""

    findings: list[Violation]
    unfinished: list[Violation]


def violation(entry: object, completed: subprocess.CompletedProcess[str]) -> Violation:
    """Read one entry of ruff's JSON report as a `Violation`, checking each field the gate reads, and raise `UnfinishedError` when one is missing or of another type."""
    match entry:
        case {"code": str() as code, "message": str() as message, "filename": str() as filename, "location": {"row": int() as row, "column": int() as column}}:
            return Violation(code=code, message=message, filename=filename, location=Location(row=row, column=column))
        case _:
            raise UnfinishedError(completed.returncode, completed.stdout)


def report(completed: subprocess.CompletedProcess[str]) -> Report:
    """Read ruff's JSON report from a run that wrote one, and raise `UnfinishedError` for one that did not.

    ruff wrote a report the gate can read only when it exited 0 or 1 and wrote its JSON report to
    stdout. The exit status alone does not tell: `python -m ruff` also exits 1 when ruff never
    starts, as when the ruff module or its binary is missing, and then writes no report. The
    report is checked, not trusted: it must be a list whose every entry holds each field the gate
    reads, of the type `Violation` gives it, or the gate has no verdict it can read, as when a
    ruff release renames, drops or nulls one of those fields. An entry of the rule `E902`, a file
    ruff could not read, or of `invalid-syntax`, a file ruff could not parse, means ruff did not
    finish checking that file, so the run gave no verdict on it; it is kept among the report's
    unfinished entries, and the other files of the run were still checked. Of the other entries,
    only those of the rule `TID251`, the banned API, are the gate's findings: `pyproject.toml`
    may select any other rule, and its findings belong to the gate that checks that rule, not
    to this one.
    """
    parsed = load(completed)
    if not is_list(parsed):
        raise UnfinishedError(completed.returncode, completed.stdout)
    violations = [violation(entry, completed) for entry in parsed]
    return Report(
        findings=[found for found in violations if found["code"] in REPORTED],
        unfinished=[found for found in violations if found["code"] in UNFINISHED],
    )


def main(paths: list[Path]) -> int:
    """Check the Python files among `paths` for `typing.cast` and print each finding.

    ruff checks the rules `pyproject.toml` selects, with its banned API, and honours no `noqa`
    comment, so a suppressed use is reported all the same. The findings are read from ruff's JSON
    report, and only those of `TID251` are the gate's, whatever other rule `pyproject.toml`
    selects; each is printed with its whole message and its code. Exit 1 on any finding, and
    1 when no path is a Python file, since nothing was checked. Exit 0 on none. When ruff cannot
    read or cannot parse a file it was given, it did not finish on that file but still checked
    the others: print each finding it reported all the same, then each entry for a file it could
    not finish, with ruff's whole message, then the count line, and exit 2, since the checker
    could not finish on the tree. When ruff writes no report the gate can read, whether it
    rejects its settings, fails otherwise, is killed by a signal, never starts, or writes a
    report of another shape, it gave no verdict the gate can read: print its whole output, each
    line on a line of its own, then ruff's exit status, then the count line, and exit 2.

    Every run that checked a file ends on the one count line,
    `check_cast: N finding(s) in M Python file(s)`, finished or not; no other line counts files.

    ruff runs without its cache: the cache keys a file on its modification time and permission
    bits, not its content, so a file whose content changed while both stayed the same, as a copy
    that keeps them does, would replay its earlier verdict and a use of `typing.cast` it now holds
    would go unread.
    """
    sources = [str(path.resolve()) for path in paths if is_python_source(path)]
    if not sources:
        sys.stdout.write(f"check_cast: no Python file among {len(paths)} path(s); nothing was checked\n")
        return 1
    command = [sys.executable, "-m", "ruff", "check", "--config", str(CONFIG), "--no-cache", "--ignore-noqa", "--output-format", "json", *sources]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    sys.stderr.write(completed.stderr)
    try:
        read = report(completed)
    except UnfinishedError as unread:
        print_unread("check_cast", "ruff", unread, len(sources))
        return BLOCKED
    for entry in [*read.findings, *read.unfinished]:
        sys.stdout.write(f"{describe(entry)}\n")
    sys.stdout.write(f"check_cast: {len(read.findings)} finding(s) in {len(sources)} Python file(s)\n")
    if read.unfinished:
        return BLOCKED
    return 1 if read.findings else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
