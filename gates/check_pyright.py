"""pyright gate: type-check every Python file in strict mode under the settings in `pyproject.toml`."""

import ast
import subprocess
import sys
from pathlib import Path
from typing import NotRequired, TypedDict

from gates.check_suppressions import is_python_source
from gates.json_report import UnfinishedError, is_list, load, print_unread

CONFIG = Path(__file__).resolve().parent.parent / "pyproject.toml"

BLOCKED = 2


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


def read_diagnostic(entry: object, completed: subprocess.CompletedProcess[str]) -> Diagnostic:
    """Read one entry of pyright's `generalDiagnostics` as a `Diagnostic`, checking each field the gate reads, and raise `UnfinishedError` when one is missing or of another type."""
    match entry:
        case {"file": str() as file, "severity": str() as severity, "message": str() as message}:
            read = Diagnostic(file=file, severity=severity, message=message)
        case _:
            raise UnfinishedError(completed.returncode, completed.stdout)
    match entry:
        case {"range": {"start": {"line": int() as line, "character": int() as character}}}:
            read["range"] = Span(start=Position(line=line, character=character))
        case {"range": object()}:
            raise UnfinishedError(completed.returncode, completed.stdout)
        case _:
            pass
    match entry:
        case {"rule": str() as rule}:
            read["rule"] = rule
        case {"rule": object()}:
            raise UnfinishedError(completed.returncode, completed.stdout)
        case _:
            pass
    return read


def report(completed: subprocess.CompletedProcess[str]) -> list[Diagnostic]:
    """Read the diagnostics of pyright's JSON report from a run that wrote one, and raise `UnfinishedError` for one that did not.

    pyright wrote a report the gate can read only when it exited 0 or 1 and wrote its JSON report
    to stdout. The exit status alone does not tell: `python -m pyright` also exits 1 when pyright
    never starts, as when the pyright module or its node runtime is missing, and then writes no
    report. The report is checked, not trusted: it must hold a `generalDiagnostics` list whose
    every entry holds each field the gate reads, of the type `Diagnostic` gives it, or the gate
    has no verdict it can read, as when a pyright release renames, drops or retypes one of them.
    """
    match load(completed):
        case {"generalDiagnostics": object() as entries} if is_list(entries):
            return [read_diagnostic(entry, completed) for entry in entries]
        case _:
            raise UnfinishedError(completed.returncode, completed.stdout)


def parses(source: str) -> bool:
    """Tell whether the Python file `source` can be read and parsed, so that pyright could have read and parsed it too."""
    try:
        ast.parse(Path(source).read_bytes(), filename=source)
    except (OSError, SyntaxError, ValueError):
        return False
    return True


def main(paths: list[Path]) -> int:
    """Type-check the Python files among `paths` and print the diagnostics located in them.

    pyright follows their imports to resolve types, but a diagnostic is reported only when it
    lies in one of the given files. The diagnostics are read from pyright's JSON report, and
    each is printed with its whole message and its rule. pyright reports a file it could not
    read or could not parse with diagnostics no rule raised, but so does its binder report an
    error in a file it parsed and checked in full, so a missing rule alone does not tell: a
    file is one pyright did not finish when it reported there a diagnostic no rule raised and
    the file cannot be read or parsed, and that file's diagnostics no rule raised are its report
    of not finishing; every other diagnostic is a finding. When pyright finished on every file,
    print a count line and exit 1 on any finding and 0 on none. When it did not finish on some
    file, print a count line saying on how many files and with how many findings, and exit 2,
    whatever it found in the other files. Exit 1 when no path is a Python file, since pyright
    handed no file checks the whole project instead. When pyright writes no report the gate can
    read, whether it rejects its settings or its arguments, fails otherwise, is killed by a
    signal, never starts, or writes a report of another shape, it gave no verdict the gate can
    read: print its whole output, each line on a line of its own, then a count line saying
    pyright could not finish and with what status, and exit 2.
    """
    sources = [str(path.resolve()) for path in paths if is_python_source(path)]
    if not sources:
        sys.stdout.write(f"check_pyright: no Python file among {len(paths)} path(s); nothing was checked\n")
        return 1
    command = [sys.executable, "-m", "pyright", "--outputjson", "--project", str(CONFIG), "--pythonpath", sys.executable, *sources]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    sys.stderr.write(completed.stderr)
    try:
        diagnostics = report(completed)
    except UnfinishedError as unread:
        print_unread("check_pyright", "pyright", unread, len(sources))
        return BLOCKED
    given = frozenset(sources)
    located = [diagnostic for diagnostic in diagnostics if str(Path(diagnostic["file"]).resolve()) in given]
    for diagnostic in located:
        sys.stdout.write(f"{describe(diagnostic)}\n")
    unruled = {diagnostic["file"] for diagnostic in located if "rule" not in diagnostic}
    unfinished = {file for file in unruled if not parses(file)}
    findings = [diagnostic for diagnostic in located if "rule" in diagnostic or diagnostic["file"] not in unfinished]
    if unfinished:
        sys.stdout.write(f"check_pyright: pyright could not finish on {len(unfinished)} of {len(sources)} Python file(s), with {len(findings)} finding(s)\n")
        return BLOCKED
    sys.stdout.write(f"check_pyright: {len(findings)} finding(s) in {len(sources)} Python file(s)\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
