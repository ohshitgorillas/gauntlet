"""What a gate run prints and how it exits: the run's lines, its count line, its exit code and the one writer."""

import sys
from collections.abc import Sequence
from dataclasses import dataclass


class GateError(Exception):
    """Something stops the checker; its report is printed as the checker's, and the run exits 2."""

    def __init__(self, report: str) -> None:
        """Carry the report that says what stopped the checker."""
        super().__init__(report)
        self.report = report


@dataclass(frozen=True)
class Finding:
    """One finding: one printed line, counted in N."""

    text: str


@dataclass(frozen=True)
class Remark:
    """A checker line that is no finding, as a mypy note: printed, not counted."""

    text: str


@dataclass(frozen=True)
class Unfinished:
    """The checker's report on what it did not finish, or a GateError's report: the run exits 2."""

    text: str


type Line = Finding | Remark | Unfinished


@dataclass(frozen=True)
class Outcome:
    """A run's lines in the order the checker gave them, and the gate's own lines the spec names, as pytest's seed."""

    lines: tuple[Line, ...] = ()
    notes: tuple[str, ...] = ()


def exit_code(outcome: Outcome) -> int:
    """Give 2 on any Unfinished, else 1 on any Finding, else 0."""
    if any(isinstance(line, Unfinished) for line in outcome.lines):
        return 2
    if any(isinstance(line, Finding) for line in outcome.lines):
        return 1
    return 0


def count_line(gate: str, findings: int, files: int) -> str:
    """Give the count line, `finding(s)` and `file(s)` as written whatever the numbers."""
    return f"{gate}: {findings} finding(s) in {files} Python file(s)"


def one_line(text: str) -> str:
    """Make every str.splitlines break in the text a space, and change nothing else."""
    return "".join(
        line if line == whole else line + " "
        for line, whole in zip(
            text.splitlines(), text.splitlines(keepends=True), strict=True
        )
    )


def output_lines(text: str) -> list[str]:
    """Split a checker's console output into its printed lines, one per str.splitlines line."""
    return text.splitlines()


def render(gate: str, outcome: Outcome, files: int) -> list[str]:
    """Give a run's printed lines: notes, then its lines in order, each Unfinished text once, the count line last."""
    printed = list(outcome.notes)
    unfinished: set[str] = set()
    for line in outcome.lines:
        if not isinstance(line, Unfinished):
            printed.append(one_line(line.text))
        elif line.text not in unfinished:
            unfinished.add(line.text)
            printed.extend(output_lines(line.text))
    findings = sum(isinstance(line, Finding) for line in outcome.lines)
    return [*printed, count_line(gate, findings, files)]


def nothing_checked(gate: str, selects: str, given: int) -> list[str]:
    """Give an empty run's lines: one saying nothing was checked, then the count line for no file."""
    return [
        f"{gate}: nothing checked: no {selects} among the {given} file(s) given",
        count_line(gate, 0, 0),
    ]


def time_cap(checker: str, seconds: float) -> str:
    """Give the gate's own line naming the checker, as given, and the time cap that ended it, in seconds."""
    return f"the checker {checker} ran past its time cap of {seconds} seconds"


def timed_out(
    output: str, checker: str, seconds: float
) -> tuple[Unfinished, Unfinished]:
    """Give a capped checker's lines: an Unfinished of its whole output as given, then one of its time_cap line."""
    return Unfinished(output), Unfinished(time_cap(checker, seconds))


def write(lines: Sequence[str], *, error: bool = False) -> None:
    """Print the lines, one per line, to sys.stdout, or sys.stderr when asked for the error stream, and flush it."""
    stream = sys.stderr if error else sys.stdout
    stream.write("".join(f"{line}\n" for line in lines))
    stream.flush()
