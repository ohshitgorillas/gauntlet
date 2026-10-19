"""Suppression gate: fail on any comment that silences a checker, and on any reference to `typing.no_type_check`."""

import ast
import errno
import io
import re
import stat
import sys
import tokenize
import tomllib
import warnings
from dataclasses import dataclass
from pathlib import Path

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

CONFIG = Path(__file__).resolve().parent.parent / "pyproject.toml"

PYTHON_SUFFIXES = (".py", ".pyi")

PYTHON_SHEBANG = re.compile(rb"^#!.*python")

NAMES_NOTHING = frozenset({errno.ENOENT, errno.ENOTDIR})

BLOCKED = 2


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


def is_python_source(path: Path) -> bool:
    """Return whether `path` is a Python file: a name ending in `.py` or `.pyi`, or an extensionless file whose first line is a python shebang.

    A path named as a Python file, or an extensionless one, that cannot be told to be a file,
    as under a directory it may not search, or an extensionless file whose first line cannot be
    read, may be a Python file, and nothing short of reading it tells, so it is taken as one:
    the gate hands it to its checker, which reports that it could not read it, and the gate
    exits 2 on a file it could not finish instead of skipping it or dying before any check runs.
    Only a path that names nothing, because it or one of its directories does not exist, is
    told not to be a file by its failure. The path is stat'ed here, not asked `Path.is_file()`,
    which reports False on any error and so cannot tell the two apart.
    """
    named = path.name.endswith(PYTHON_SUFFIXES)
    if not named and path.suffix:
        return False
    try:
        if not stat.S_ISREG(path.stat().st_mode):
            return False
        if named:
            return True
        with path.open("rb") as source:
            first_line = source.readline()
    except OSError as error:
        return error.errno not in NAMES_NOTHING
    return PYTHON_SHEBANG.match(first_line) is not None


@dataclass(frozen=True)
class Unfinished:
    """A Python file the gate could not read, tokenize or parse, with what it reported for that file."""

    path: Path
    report: str


def comment_suppressions(path: Path, source: str) -> list[Suppression]:
    """Return one finding per comment token of `source` that carries a marker, naming every marker it carries."""
    comments = [token for token in tokenize.generate_tokens(io.StringIO(source).readline) if token.type == tokenize.COMMENT]
    carried = [(comment.start[0], [marker for marker, pattern in MARKERS.items() if pattern.search(comment.string)]) for comment in comments]
    return [Suppression(path=path, line=line, kind="suppression comment", marker=", ".join(markers)) for line, markers in carried if markers]


def no_type_check_references(path: Path, tree: ast.Module) -> list[Suppression]:
    """Return one finding per reference in `tree` to `no_type_check` or `no_type_check_decorator` of `typing` or `typing_extensions`.

    A reference is a name importing the function, a use of a name any binding of which, in a
    scope Python's scoping rules resolve the use to, can be the function, by an import, a star
    import, an assignment from another reference, or a `for` target or `match` capture pattern
    that takes it, and an attribute naming it of a name any such binding of which can be a
    typing module, by an import or by an assignment from another such name. Where and in what
    order the bindings of the name sit in that scope, and whether any of them runs, does not
    matter.
    """
    return [Suppression(path=path, line=reference.line, kind="reference to", marker=reference.functions) for reference in Resolver().run(tree)]


def pinned_grammar() -> tuple[int, int] | None:
    """Return the Python version the tree is pinned to, as `(major, minor)`: pyright's `pythonVersion` in `pyproject.toml`, or None when that is not set, since pyright then takes the version of the interpreter the gate hands it, the one `ast` parses with by default.

    The pin is read from `pyproject.toml` on every call, never kept in a gate, so a gate that
    parses with it parses with the grammar the type checkers take from the same file.
    """
    with CONFIG.open("rb") as config:
        settings: object = tomllib.load(config)
    match settings:
        case {"tool": {"pyright": {"pythonVersion": str() as version}}}:
            major, minor, *_ = version.split(".")
            return int(major), int(minor)
        case _:
            return None


def parse_pinned(path: Path, source: str) -> ast.Module:
    """Parse `source` with the grammar of the pinned Python, `pinned_grammar`, raising `SyntaxError` on what that grammar cannot parse.

    A source nested deeper than the parser can go cannot be parsed either: the parser raises
    `MemoryError` when its stack overflows, and `RecursionError` when building the tree of a
    parse runs past the recursion limit.

    A `SyntaxWarning` the parse raises, such as an invalid escape sequence, says nothing about
    the grammar, so it is kept out of the warning filters of whoever runs the gate and cannot
    turn a file that parses into one the gate did not finish.
    """
    with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
        return ast.parse(source, filename=str(path), feature_version=pinned_grammar())


def find_suppressions(path: Path) -> list[Suppression]:
    """Return every suppression comment and every `no_type_check` reference in the Python file at `path`, in line order.

    Raise `OSError` when the file, or the `pyproject.toml` that holds the pin, cannot be read, `SyntaxError`, `UnicodeDecodeError` or
    `tokenize.TokenError` when it cannot be decoded or tokenized, `SyntaxError` when the
    grammar of the pinned Python cannot parse it, and `MemoryError` or `RecursionError` when
    its parse runs deeper than the parser can go.
    """
    with tokenize.open(path) as reader:
        source = reader.read()
    comments = comment_suppressions(path, source)
    references = no_type_check_references(path, parse_pinned(path, source))
    return sorted(comments + references)


def scan(path: Path) -> list[Suppression] | Unfinished:
    """Return every finding in the Python file at `path`, or what the gate reported when it could not read, tokenize or parse that file."""
    try:
        return find_suppressions(path)
    except (OSError, SyntaxError, UnicodeDecodeError, tokenize.TokenError, MemoryError, RecursionError) as error:
        return Unfinished(path=path, report=f"{type(error).__name__}: {error}")


def main(paths: list[Path]) -> int:
    """List every suppression comment and `no_type_check` reference found in the Python files among `paths`.

    When every file was parsed, print a count line and exit 1 on any finding and 0 on none.
    A file the gate cannot read, tokenize or parse is one it did not finish: print each
    finding of the other files all the same, then what the gate reported for each such
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
        sys.stdout.write(f"{suppression.path}:{suppression.line}: {suppression.kind} `{suppression.marker}`\n")
    for file in unfinished:
        sys.stdout.write(f"{file.path}: {file.report}\n")
    if unfinished:
        sys.stdout.write(f"check_suppressions: the gate could not finish on {len(unfinished)} of {len(sources)} Python file(s), with {len(found)} finding(s)\n")
        return BLOCKED
    sys.stdout.write(f"check_suppressions: {len(found)} finding(s) in {len(sources)} Python file(s)\n")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
