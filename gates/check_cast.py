"""Cast gate: fail on any use of `typing.cast`, found by ruff's `TID251` under the banned API in `pyproject.toml`."""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, TypeGuard

from gates.check_suppressions import is_python_source

CONFIG = Path(__file__).resolve().parent.parent / "pyproject.toml"

FINISHED = frozenset({0, 1})

BLOCKED = 2

REPORTED = frozenset({"TID251", None})

UNREAD = "E902"


class Location(TypedDict):
    """A one-based place in a file, as ruff's JSON report gives it."""

    row: int
    column: int


class Violation(TypedDict):
    """The part of one entry of ruff's `--output-format json` report the gate reads; `code` is null for a syntax error."""

    code: str | None
    message: str
    filename: str
    location: Location


def describe(violation: Violation) -> str:
    """Render one violation as ruff's own concise report does, with its whole message and its code."""
    location = violation["location"]
    code = "" if violation["code"] is None else f"{violation['code']} "
    return f"{violation['filename']}:{location['row']}:{location['column']}: {code}{violation['message']}"


class UnfinishedError(Exception):
    """ruff gave no verdict the gate can read: it exited `status` and wrote `output` to stdout, with no JSON report the gate can read in it."""

    def __init__(self, status: int, output: str) -> None:
        """Carry ruff's exit status and its whole stdout."""
        super().__init__(status, output)
        self.status = status
        self.output = output


@dataclass(frozen=True)
class Report:
    """The gate's reading of one JSON report ruff wrote: its findings, and the entries for each file ruff could not read."""

    findings: list[Violation]
    unread: list[Violation]


def is_list(value: object) -> TypeGuard[list[object]]:
    """Tell whether `value` is a list; every element of a list is an `object`, so the narrowing claims nothing it did not check."""
    return isinstance(value, list)


def violation(entry: object, completed: subprocess.CompletedProcess[str]) -> Violation:
    """Read one entry of ruff's JSON report as a `Violation`, checking each field the gate reads, and raise `UnfinishedError` when one is missing or of another type."""
    match entry:
        case {"code": str() | None as code, "message": str() as message, "filename": str() as filename, "location": {"row": int() as row, "column": int() as column}}:
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
    ruff could not read, means ruff did not finish checking that file, so the run gave no verdict
    on it; it is kept among the report's unread entries, and the other files of the run were
    still checked. Of the other entries, only those of the rule `TID251`, the banned API, and
    those with no code, a file ruff cannot parse, are the gate's findings: `pyproject.toml` may
    select any other rule, and its findings belong to the gate that checks that rule, not to
    this one.
    """
    if completed.returncode not in FINISHED:
        raise UnfinishedError(completed.returncode, completed.stdout)
    try:
        parsed: object = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise UnfinishedError(completed.returncode, completed.stdout) from error
    if not is_list(parsed):
        raise UnfinishedError(completed.returncode, completed.stdout)
    violations = [violation(entry, completed) for entry in parsed]
    return Report(
        findings=[found for found in violations if found["code"] in REPORTED],
        unread=[found for found in violations if found["code"] == UNREAD],
    )


def main(paths: list[Path]) -> int:
    """Check the Python files among `paths` for `typing.cast` and print each finding.

    ruff checks the rules `pyproject.toml` selects, with its banned API, and honours no `noqa`
    comment, so a suppressed use is reported all the same. The findings are read from ruff's JSON
    report, and only those of `TID251` are the gate's, whatever other rule `pyproject.toml`
    selects; each is printed with its whole message and its code; a file ruff
    cannot parse is reported the same way and counted as a finding. Exit 1 on any finding, and
    1 when no path is a Python file, since nothing was checked. Exit 0 on none. When ruff cannot
    read a file it was given, it did not finish on that file but still checked the others:
    print each finding it reported all the same, then each file it could not read, with ruff's
    whole message, then a count line saying on how many files ruff could not finish and with how
    many findings, and exit 2, since the checker could not finish on the tree. When ruff writes
    no report the gate can read, whether it rejects its settings, fails otherwise, is killed by
    a signal, never starts, or writes a report of another shape, it gave no verdict the gate can
    read: print its whole output, each line on a line of its own, then a count line saying ruff
    could not finish and with what status, and exit 2.

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
    except UnfinishedError as unfinished:
        sys.stdout.write("".join(f"{line}\n" for line in unfinished.output.splitlines()))
        sys.stdout.write(f"check_cast: ruff exited {unfinished.status} and gave no report it could read on {len(sources)} Python file(s)\n")
        return BLOCKED
    for finding in read.findings:
        sys.stdout.write(f"{describe(finding)}\n")
    if read.unread:
        for entry in read.unread:
            sys.stdout.write(f"{describe(entry)}\n")
        unfinished_files = len({entry["filename"] for entry in read.unread})
        sys.stdout.write(f"check_cast: ruff could not finish on {unfinished_files} of {len(sources)} Python file(s), with {len(read.findings)} finding(s)\n")
        return BLOCKED
    sys.stdout.write(f"check_cast: {len(read.findings)} finding(s) in {len(sources)} Python file(s)\n")
    return 1 if read.findings else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
