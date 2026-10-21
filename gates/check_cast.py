"""Cast gate: fail on any use of `typing.cast`, found by ruff's `TID251` under the banned API in `pyproject.toml`."""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict, TypeGuard

from gates.core.checker import Command, Completed, python_module
from gates.core.project import Source
from gates.core.report import Finding, GateError, Line, Unfinished
from gates.core.runner import Checker, Gate, Run, check_with, run_gate
from gates.core.runner import main as run_main

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
    """The gate's reading of one JSON report ruff wrote: every entry, which of them are its findings, and which are files ruff could not finish."""

    entries: list[Violation]

    @property
    def findings(self) -> list[Violation]:
        """The entries of the rule the gate reports; `pyproject.toml` may select any other rule, and its findings belong to the gate that checks it."""
        return [found for found in self.entries if found["code"] in REPORTED]

    @property
    def unfinished(self) -> list[Violation]:
        """The entries for a file ruff could not read (`E902`) or parse (`invalid-syntax`): no verdict on it, the others still checked."""
        return [found for found in self.entries if found["code"] in UNFINISHED]


def violation(entry: object, completed: Completed) -> Violation:
    """Read one entry of ruff's JSON report as a `Violation`, checking each field the gate reads, and raise `GateError` when one is missing or of another type."""
    match entry:
        case {
            "code": str() as code,
            "message": str() as message,
            "filename": str() as filename,
            "location": {"row": int() as row, "column": int() as column},
        }:
            return Violation(
                code=code,
                message=message,
                filename=filename,
                location=Location(row=row, column=column),
            )
        case _:
            raise GateError(completed.output())


def is_list(value: object) -> TypeGuard[list[object]]:
    """Tell whether the value is a list, as one of objects."""
    return isinstance(value, list)


def report(completed: Completed) -> Report:
    """Read ruff's JSON report from a run that wrote one, and raise `GateError` for one that did not.

    The report is checked, not trusted: stdout must be a JSON list whose every entry holds each field the gate reads,
    of the type `Violation` gives it, or the gate has no verdict it can read, as when a ruff release renames, drops or
    nulls one of those fields, or when `python -m ruff` exits 1 because ruff never starts and writes no report.
    """
    try:
        parsed: object = json.loads(completed.stdout)
    except ValueError as error:
        raise GateError(completed.output()) from error
    if not is_list(parsed):
        raise GateError(completed.output())
    return Report(entries=[violation(entry, completed) for entry in parsed])


class Cast:
    """ruff's `TID251` over every source in one run, with no cache and no `noqa`.

    ruff runs without its cache: the cache keys a file on its modification time and permission bits, not its content,
    so a file whose content changed while both stayed the same, as a copy that keeps them does, would replay its
    earlier verdict and a use of `typing.cast` it now holds would go unread. `--ignore-noqa` keeps a suppressed use a
    finding.
    """

    stopped: frozenset[int] = frozenset()

    def batches(self, run: Run) -> list[list[Source]]:
        """One ruff for all the files: no verdict depends on how they are grouped."""
        return [list(run.sources)]

    def command(self, run: Run, batch: Sequence[Source]) -> Command:
        """ruff over the batch, with the project's settings, as a JSON report."""
        return python_module(
            "ruff",
            "check",
            "--config",
            run.project.config,
            "--no-cache",
            "--ignore-noqa",
            "--output-format",
            "json",
            *(source.absolute for source in batch),
            cwd=run.project.root,
        )

    def read(self, completed: Completed) -> Report:
        """The report ruff wrote, or a GateError."""
        return report(completed)

    def expected_status(self, report: Report) -> int:
        """ruff exits 1 with any entry of any rule it was set to check, 0 with none."""
        return 1 if report.entries else 0

    def lines(
        self, report: Report, batch: Sequence[Source], *, stopped: bool
    ) -> list[Line]:
        """A Finding for each use of the banned name, then an Unfinished for each file ruff could not finish."""
        del batch, stopped
        return [
            *(Finding(describe(found)) for found in report.findings),
            *(Unfinished(describe(found)) for found in report.unfinished),
        ]


CHECKER: Checker[Report] = Cast()

GATE = Gate(name="check_cast", check=check_with(CHECKER))


def main(paths: Sequence[Path]) -> int:
    """Run the gate over the paths, in the working directory's project, and return its exit code."""
    return run_gate(GATE, paths)


if __name__ == "__main__":
    run_main(GATE)
