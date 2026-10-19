"""pyright gate: type-check every Python file in strict mode under the settings in `pyproject.toml`."""

import json
import subprocess
import sys
from pathlib import Path
from typing import NotRequired, TypedDict

from gates.check_suppressions import is_python_source

CONFIG = Path(__file__).resolve().parent.parent / "pyproject.toml"

FINISHED = frozenset({0, 1})


class Position(TypedDict):
    """A zero-based place in a file, as pyright's JSON report gives it."""

    line: int
    character: int


class Span(TypedDict):
    """The part of a diagnostic's `range` the gate reads: where the diagnostic starts."""

    start: Position


class Diagnostic(TypedDict):
    """One entry of `generalDiagnostics` in pyright's `--outputjson` report; `rule` is absent when no rule raised it."""

    file: str
    severity: str
    message: str
    range: Span
    rule: NotRequired[str]


class Report(TypedDict):
    """The part of pyright's `--outputjson` report the gate reads."""

    generalDiagnostics: list[Diagnostic]


def describe(diagnostic: Diagnostic) -> str:
    """Render one diagnostic as pyright's own text report does, with its whole message and its rule."""
    start = diagnostic["range"]["start"]
    rule = f" ({diagnostic['rule']})" if "rule" in diagnostic else ""
    return f"{diagnostic['file']}:{start['line'] + 1}:{start['character'] + 1} - {diagnostic['severity']}: {diagnostic['message']}{rule}"


def main(paths: list[Path]) -> int:
    """Type-check the Python files among `paths` and print the findings located in them.

    pyright follows their imports to resolve types, but a finding is reported only when it
    lies in one of the given files. The findings are read from pyright's JSON report, and
    each is printed with its whole message and its rule. Exit 1 on any such finding, and 1
    when no path is a Python file, since pyright handed no file checks the whole project
    instead. Exit 0 on none; when pyright does not finish a check, print its whole output and
    return its exit status.
    """
    sources = [str(path.resolve()) for path in paths if is_python_source(path)]
    if not sources:
        sys.stdout.write(f"check_pyright: no Python file among {len(paths)} path(s); nothing was checked\n")
        return 1
    command = [sys.executable, "-m", "pyright", "--outputjson", "--project", str(CONFIG), "--pythonpath", sys.executable, *sources]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    sys.stderr.write(completed.stderr)
    if completed.returncode not in FINISHED:
        sys.stdout.write(completed.stdout)
        return completed.returncode
    report: Report = json.loads(completed.stdout)
    given = frozenset(sources)
    findings = [diagnostic for diagnostic in report["generalDiagnostics"] if str(Path(diagnostic["file"]).resolve()) in given]
    for finding in findings:
        sys.stdout.write(f"{describe(finding)}\n")
    sys.stdout.write(f"check_pyright: {len(findings)} finding(s) in {len(sources)} Python file(s)\n")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
