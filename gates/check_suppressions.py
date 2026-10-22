# Copyright 2026 oh shit, gorillas!
"""Suppression gate: fail on any comment that silences a checker, and on any reference to `typing.no_type_check`."""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from gates.core.report import Finding, Line, Outcome, Unfinished
from gates.core.runner import Gate, Run, run_gate
from gates.core.runner import main as run_main
from gates.core.source import Parsed, comment_markers, parse, pinned_version
from gates.no_type_check import Resolver

MARKERS: dict[str, re.Pattern[str]] = {
    "noqa": re.compile(r"noqa", re.IGNORECASE),
    "type: ignore": re.compile(r"type\s*:\s*ignore", re.IGNORECASE),
    "pyright: ignore": re.compile(r"pyright\s*:\s*ignore", re.IGNORECASE),
    "pragma: no cover": re.compile(r"pragma\s*:\s*no\s*cover", re.IGNORECASE),
    "pragma: no mutate": re.compile(r"pragma\s*:\s*no\s*mutate", re.IGNORECASE),
    "# mypy:": re.compile(r"mypy\s*:", re.IGNORECASE),
    "# pyright:": re.compile(r"pyright\s*:", re.IGNORECASE),
    "# fmt: off": re.compile(r"fmt\s*:\s*off", re.IGNORECASE),
    "# fmt: skip": re.compile(r"fmt\s*:\s*skip", re.IGNORECASE),
}


@dataclass(frozen=True, order=True)
class Suppression:
    """One finding: where it is, what kind it is, and what it names; findings order by path, then line.

    A comment finding names every marker its comment carries; a reference finding names the
    `no_type_check` function the line refers to.
    """

    path: Path
    line: int
    kind: str
    marker: str


def comment_suppressions(parsed: Parsed) -> list[Suppression]:
    """Return one finding per comment of the parsed file that carries a marker, naming every marker it carries."""
    path = parsed.source.given
    return [
        Suppression(
            path=path, line=line, kind="suppression comment", marker=", ".join(names)
        )
        for line, names in comment_markers(parsed, MARKERS)
    ]


def no_type_check_references(parsed: Parsed) -> list[Suppression]:
    """Return one finding per reference in the parsed file to `no_type_check` or `no_type_check_decorator` of `typing` or `typing_extensions`.

    A reference is a name importing the function, a use of a name any binding of which, in a
    scope Python's scoping rules resolve the use to, can be the function, by an import, a star
    import, an assignment from another reference, or a `for` target or `match` capture pattern
    that takes it, and an attribute naming it of a name any such binding of which can be a
    typing module, by an import or by an assignment from another such name. The line of a
    `case` whose capture pattern can take the function is a reference too, on the line its
    `case` keyword sits on. Where and in what order the bindings of the name sit in that scope,
    and whether any of them runs, does not matter.
    """
    path = parsed.source.given
    return [
        Suppression(
            path=path,
            line=reference.line,
            kind="reference to",
            marker=reference.functions,
        )
        for reference in Resolver(parsed.tokens).run(parsed.tree)
    ]


def find_suppressions(parsed: Parsed) -> list[Suppression]:
    """Return every suppression comment and every `no_type_check` reference in the parsed file, in line order."""
    return sorted(comment_suppressions(parsed) + no_type_check_references(parsed))


def check(run: Run) -> Outcome:
    """List every suppression comment and `no_type_check` reference in the run's files, then what could not be parsed.

    Every file is parsed under the grammar of the pinned Python, read once, by the core; a file it cannot parse is one
    the gate did not finish, and is reported after the findings of the others. GateError when the project pins no Python.
    """
    version = pinned_version(run.project)
    parses = [parse(source, version) for source in run.sources]
    lines: list[Line] = [
        Finding(f"{found.path}:{found.line}: {found.kind} `{found.marker}`")
        for parsed in parses
        if isinstance(parsed, Parsed)
        for found in find_suppressions(parsed)
    ]
    lines.extend(parsed for parsed in parses if isinstance(parsed, Unfinished))
    return Outcome(lines=tuple(lines))


GATE = Gate(name="check_suppressions", check=check)


def main(paths: Sequence[Path]) -> int:
    """Run the gate over the paths, in the working directory's project, and return its exit code."""
    return run_gate(GATE, paths)


if __name__ == "__main__":
    run_main(GATE)
