"""pyright gate: type-check every Python file in strict mode under the settings in `pyproject.toml`."""

import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import NotRequired, TypedDict, TypeGuard

from gates.core.checker import Command, Completed, python_module
from gates.core.project import Source
from gates.core.report import Finding, GateError, Line, Outcome, Unfinished
from gates.core.runner import Checker, Gate, Run, check_with, run_gate
from gates.core.runner import main as run_main
from gates.core.source import Parsed, parse, pinned_version


class Position(TypedDict):
    """A zero-based place in a file, as pyright's JSON report gives it."""

    line: int
    character: int


class Span(TypedDict):
    """The part of a diagnostic's `range` the gate reads: where the diagnostic starts."""

    start: Position


class Diagnostic(TypedDict):
    """The part of one entry of `generalDiagnostics` in pyright's `--outputjson` report the gate reads.

    `rule` is absent when no rule raised it, as for a file pyright could not read or parse, or
    an error its binder raises, and `range` is absent when the diagnostic covers the whole file,
    as for a file it could not read.
    """

    file: str
    severity: str
    message: str
    range: NotRequired[Span]
    rule: NotRequired[str]


def describe(diagnostic: Diagnostic) -> str:
    """Render one diagnostic on a single line, as pyright's own text report does, with its whole message and its rule.

    pyright splits a message over several lines, each detail on a line of its own; the gate
    prints each finding on its own line, so the message's lines are joined by a space, each
    kept whole, its indentation included.
    """
    place = ""
    if "range" in diagnostic:
        start = diagnostic["range"]["start"]
        place = f":{start['line'] + 1}:{start['character'] + 1}"
    rule = f" ({diagnostic['rule']})" if "rule" in diagnostic else ""
    message = " ".join(diagnostic["message"].splitlines())
    return f"{diagnostic['file']}{place} - {diagnostic['severity']}: {message}{rule}"


def where(diagnostic: Diagnostic) -> str:
    """Return the resolved path of the file `diagnostic` lies in, the form in which the gate hands pyright its files."""
    return str(Path(diagnostic["file"]).resolve())


def read_diagnostic(entry: object, completed: Completed) -> Diagnostic:
    """Read one entry of pyright's `generalDiagnostics` as a `Diagnostic`, checking each field the gate reads, and raise `GateError` when one is missing or of another type."""
    match entry:
        case {
            "file": str() as file,
            "severity": str() as severity,
            "message": str() as message,
        }:
            read = Diagnostic(file=file, severity=severity, message=message)
        case _:
            raise GateError(completed.output())
    match entry:
        case {
            "range": {"start": {"line": int() as line, "character": int() as character}}
        }:
            read["range"] = Span(start=Position(line=line, character=character))
        case {"range": object()}:
            raise GateError(completed.output())
        case _:
            pass
    match entry:
        case {"rule": str() as rule}:
            read["rule"] = rule
        case {"rule": object()}:
            raise GateError(completed.output())
        case _:
            pass
    return read


@dataclass(frozen=True)
class Report:
    """The part of pyright's JSON report the gate reads: its diagnostics, and how many of the files it was given it analyzed (`summary.filesAnalyzed`)."""

    diagnostics: list[Diagnostic]
    analyzed: int


def is_list(value: object) -> TypeGuard[list[object]]:
    """Tell whether `value` is a list; every element of a list is an `object`, so the narrowing claims nothing it did not check."""
    return isinstance(value, list)


def report(completed: Completed) -> Report:
    """Read pyright's JSON report from a run that wrote one, and raise `GateError` for one that did not.

    pyright wrote a report the gate can read only when it exited 0 or 1 and wrote its JSON report
    to stdout. The exit status alone does not tell: `python -m pyright` also exits 1 when pyright
    never starts, as when the pyright module or its node runtime is missing, and then writes no
    report. The report is checked, not trusted: it must hold a `generalDiagnostics` list whose
    every entry holds each field the gate reads, of the type `Diagnostic` gives it, and a
    `summary` whose `filesAnalyzed` is a number, or the gate has no verdict it can read, as when
    a pyright release renames, drops or retypes one of them.
    """
    try:
        loaded: object = json.loads(completed.stdout)
    except ValueError as error:
        raise GateError(completed.output()) from error
    match loaded:
        case {
            "generalDiagnostics": object() as entries,
            "summary": {"filesAnalyzed": int() as analyzed},
        } if is_list(entries):
            return Report(
                diagnostics=[read_diagnostic(entry, completed) for entry in entries],
                analyzed=analyzed,
            )
        case _:
            raise GateError(completed.output())


class Pyright:
    """pyright over every source in one run, its diagnostics read from its JSON report.

    pyright follows the imports of the given files to resolve types, but a diagnostic is reported only when it lies in
    one of the given files. pyright reports a file it could not read or could not parse with diagnostics no rule raised,
    and it reports the same way an error its binder raises, or a `reveal_type`, in a file it parsed and checked in
    full; its report gives nothing else that tells the two apart. So every given file is read and parsed under the
    grammar pyright parses with, `pythonVersion` in `pyproject.toml`, not the grammar of the interpreter the gate runs
    under: a file that cannot be read or parsed is one pyright did not finish, and the diagnostics no rule raised there
    are its report of not finishing, not findings. A warning raised while a file is parsed is an error for that parse,
    so such a file is one pyright did not finish too, whatever pyright reported there: each such warning is printed,
    after the diagnostics, as the report of not finishing it. pyright also drops a given file from its analysis with no
    diagnostic at all, as one its default excludes match, so when its report's `summary.filesAnalyzed` counts fewer
    files than it was given, a line says it left some out.
    """

    stopped: frozenset[int] = frozenset()

    def __init__(self, version: tuple[int, int]) -> None:
        """Take the grammar the pinned Python parses with."""
        self.version = version

    def batches(self, run: Run) -> list[list[Source]]:
        """One pyright for all the files: a verdict can depend on the other files it follows imports to."""
        return [list(run.sources)]

    def command(self, run: Run, batch: Sequence[Source]) -> Command:
        """pyright over the batch, each file by its resolved path, with the project's settings, as a JSON report."""
        return python_module(
            "pyright",
            "--outputjson",
            "--project",
            run.project.config,
            "--pythonpath",
            sys.executable,
            *(resolved(source) for source in batch),
            cwd=run.project.root,
        )

    def read(self, completed: Completed) -> Report:
        """The report pyright wrote, or a GateError."""
        return report(completed)

    def expected_status(self, report: Report) -> int:
        """pyright exits 1 when its report holds an error, 0 when it holds none."""
        return (
            1
            if any(
                diagnostic["severity"] == "error" for diagnostic in report.diagnostics
            )
            else 0
        )

    def lines(
        self, report: Report, batch: Sequence[Source], *, stopped: bool
    ) -> list[Line]:
        """The diagnostics in the given files, then each parse that did not finish, then the line for files pyright left out.

        A diagnostic no rule raised in a file that could not be parsed is pyright's report of not finishing it; every
        other diagnostic is a finding.
        """
        del stopped
        parses = {resolved(source): parse(source, self.version) for source in batch}
        lines: list[Line] = []
        for diagnostic in report.diagnostics:
            parsed = parses.get(where(diagnostic))
            if parsed is None:
                continue
            unfinished = "rule" not in diagnostic and not isinstance(parsed, Parsed)
            lines.append(
                Unfinished(describe(diagnostic))
                if unfinished
                else Finding(describe(diagnostic))
            )
        lines.extend(
            parsed for parsed in parses.values() if isinstance(parsed, Unfinished)
        )
        if report.analyzed < len(parses):
            lines.append(
                Unfinished(
                    "check_pyright: pyright left some of the given Python files out of its analysis"
                )
            )
        return lines


def resolved(source: Source) -> str:
    """Return the resolved path of the source, the form in which the gate hands pyright its files."""
    return str(source.absolute.resolve())


def check(run: Run) -> Outcome:
    """Run pyright over the run's sources under the grammar of the pinned Python; GateError when the pin cannot be read."""
    checker: Checker[Report] = Pyright(pinned_version(run.project))
    return check_with(checker)(run)


GATE = Gate(name="check_pyright", check=check)


def main(paths: Sequence[Path]) -> int:
    """Run the gate over the paths, in the working directory's project, and return its exit code."""
    return run_gate(GATE, paths)


if __name__ == "__main__":
    run_main(GATE)
