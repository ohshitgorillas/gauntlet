"""Suppression gate: fail on any comment that silences a checker."""

import re
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path

MARKERS: dict[str, re.Pattern[str]] = {
    "noqa": re.compile(r"noqa", re.IGNORECASE),
    "type: ignore": re.compile(r"type\s*:\s*ignore", re.IGNORECASE),
    "pyright: ignore": re.compile(r"pyright\s*:\s*ignore", re.IGNORECASE),
    "pragma: no cover": re.compile(r"pragma\s*:\s*no\s*cover", re.IGNORECASE),
    "pragma: no mutate": re.compile(r"pragma\s*:\s*no\s*mutate", re.IGNORECASE),
}

PYTHON_SUFFIXES = (".py", ".pyi")

PYTHON_SHEBANG = re.compile(rb"^#!.*python")

BLOCKED = 2


@dataclass(frozen=True)
class Suppression:
    """One suppression comment: where it is and which marker it carries."""

    path: Path
    line: int
    marker: str


def is_python_source(path: Path) -> bool:
    """Return whether `path` is a Python file: a name ending in `.py` or `.pyi`, or an extensionless file whose first line is a python shebang.

    A path named as a Python file, or an extensionless one, that cannot be told to be a file,
    as under a directory it may not search, or an extensionless file whose first line cannot be
    read, may be a Python file, and nothing short of reading it tells, so it is taken as one:
    the gate hands it to its checker, which reports that it could not read it, and the gate
    exits 2 on a file it could not finish instead of skipping it or dying before any check runs.
    """
    named = path.name.endswith(PYTHON_SUFFIXES)
    if not named and path.suffix:
        return False
    try:
        if not path.is_file():
            return False
        if named:
            return True
        with path.open("rb") as source:
            first_line = source.readline()
    except OSError:
        return True
    return PYTHON_SHEBANG.match(first_line) is not None


@dataclass(frozen=True)
class Unfinished:
    """A Python file the tokenizer could not read or could not tokenize, with what it reported for that file."""

    path: Path
    report: str


def find_suppressions(path: Path) -> list[Suppression]:
    """Return every suppression comment in the Python file at `path`.

    Raise `OSError` when the file cannot be read, and `SyntaxError`, `UnicodeDecodeError` or
    `tokenize.TokenError` when it cannot be decoded or tokenized.
    """
    with tokenize.open(path) as source:
        comments = [token for token in tokenize.generate_tokens(source.readline) if token.type == tokenize.COMMENT]
    return [
        Suppression(path=path, line=comment.start[0], marker=marker)
        for comment in comments
        for marker, pattern in MARKERS.items()
        if pattern.search(comment.string)
    ]


def scan(path: Path) -> list[Suppression] | Unfinished:
    """Return every suppression comment in the Python file at `path`, or what the tokenizer reported when it could not read or tokenize that file."""
    try:
        return find_suppressions(path)
    except (OSError, SyntaxError, UnicodeDecodeError, tokenize.TokenError) as error:
        return Unfinished(path=path, report=f"{type(error).__name__}: {error}")


def main(paths: list[Path]) -> int:
    """List every suppression comment found in the Python files among `paths`.

    When every file was tokenized, print a count line and exit 1 on any finding and 0 on none.
    A file the tokenizer cannot read or cannot tokenize is one it did not finish: print each
    finding of the other files all the same, then what the tokenizer reported for each such
    file, then a count line saying on how many files it could not finish and with how many
    findings, and exit 2. When no path is a Python file, nothing was checked: print a line
    saying so and exit 1.
    """
    sources = [path for path in paths if is_python_source(path)]
    if not sources:
        sys.stdout.write(f"check_suppressions: no Python file among {len(paths)} path(s); nothing was checked\n")
        return 1
    scans = [scan(path) for path in sources]
    found = [suppression for scanned in scans if not isinstance(scanned, Unfinished) for suppression in scanned]
    unfinished = [scanned for scanned in scans if isinstance(scanned, Unfinished)]
    for suppression in found:
        sys.stdout.write(f"{suppression.path}:{suppression.line}: suppression comment `{suppression.marker}`\n")
    for file in unfinished:
        sys.stdout.write(f"{file.path}: {file.report}\n")
    if unfinished:
        sys.stdout.write(f"check_suppressions: the tokenizer could not finish on {len(unfinished)} of {len(sources)} Python file(s), with {len(found)} finding(s)\n")
        return BLOCKED
    sys.stdout.write(f"check_suppressions: {len(found)} finding(s) in {len(sources)} Python file(s)\n")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
