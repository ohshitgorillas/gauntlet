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

MAJOR_MINOR = re.compile(r"[0-9]+\.[0-9]+")

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


def comment_suppressions(path: Path, tokens: list[tokenize.TokenInfo]) -> list[Suppression]:
    """Return one finding per comment token among `tokens` that carries a marker, naming every marker it carries."""
    comments = [token for token in tokens if token.type == tokenize.COMMENT]
    carried = [(comment.start[0], [marker for marker, pattern in MARKERS.items() if pattern.search(comment.string)]) for comment in comments]
    return [Suppression(path=path, line=line, kind="suppression comment", marker=", ".join(markers)) for line, markers in carried if markers]


def case_keywords(tokens: list[tokenize.TokenInfo]) -> list[tuple[int, int]]:
    """Return the start, line and column, of each name token `case` among `tokens`, in source order: every `case` keyword, and any name `case` that is not one."""
    return [token.start for token in tokens if token.type == tokenize.NAME and token.string == "case"]


def no_type_check_references(path: Path, tree: ast.Module, keywords: list[tuple[int, int]]) -> list[Suppression]:
    """Return one finding per reference in `tree` to `no_type_check` or `no_type_check_decorator` of `typing` or `typing_extensions`, a `case` line read from `keywords`, the `case` name tokens of its source.

    A reference is a name importing the function, a use of a name any binding of which, in a
    scope Python's scoping rules resolve the use to, can be the function, by an import, a star
    import, an assignment from another reference, or a `for` target or `match` capture pattern
    that takes it, and an attribute naming it of a name any such binding of which can be a
    typing module, by an import or by an assignment from another such name. The line of a
    `case` whose capture pattern can take the function is a reference too, on the line its
    `case` keyword sits on. Where and in what order the bindings of the name sit in that scope,
    and whether any of them runs, does not matter.
    """
    return [Suppression(path=path, line=reference.line, kind="reference to", marker=reference.functions) for reference in Resolver(keywords).run(tree)]


class UnpinnedError(Exception):
    """`pyproject.toml` pins no Python to parse with: it cannot be read, sets no pyright `pythonVersion`, sets one that is not a `major.minor` version, or sets one the parser has no grammar for."""


def pinned_grammar() -> tuple[int, int]:
    """Return the Python version the tree is pinned to, as `(major, minor)`: pyright's `pythonVersion` in `pyproject.toml`.

    This is the one home of the pin rule, for every gate that parses a Python file. The pin is
    read from `pyproject.toml` on every call; a gate calls it once per run and parses every file
    of the run with what it returned, so a gate that parses with it parses with the grammar the
    type checkers take from the same file, and all the files of one run under one grammar. A
    `pyproject.toml` that cannot be read, sets no `pythonVersion`, or sets one that is not a
    `major.minor` version, such as `"3"`, `"3.12.0"` or `"py312"`, pins nothing, and neither
    does one whose version the parser has no grammar for, such as `"2.7"` or `"4.0"`, which
    `ast.parse` refuses: `UnpinnedError` is raised with a message naming the key, and the gate
    never falls back to the grammar of the interpreter it runs under.
    """
    try:
        with CONFIG.open("rb") as config:
            settings: object = tomllib.load(config)
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        message = f"{CONFIG}: cannot read pyright's `pythonVersion`: {error}"
        raise UnpinnedError(message) from error
    match settings:
        case {"tool": {"pyright": {"pythonVersion": str() as version}}} if MAJOR_MINOR.fullmatch(version):
            major, minor = version.split(".")
            pinned = (int(major), int(minor))
            try:
                ast.parse("", feature_version=pinned)
            except (ValueError, OverflowError) as error:
                message = f"{CONFIG}: pyright's `pythonVersion` is {version!r}, a version the parser has no grammar for: {error}"
                raise UnpinnedError(message) from error
            return pinned
        case {"tool": {"pyright": {"pythonVersion": object() as version}}}:
            message = f"{CONFIG}: pyright's `pythonVersion` is {version!r}, not a `major.minor` version"
            raise UnpinnedError(message)
        case _:
            message = f"{CONFIG}: sets no pyright `pythonVersion`"
            raise UnpinnedError(message)


def parse_pinned(path: Path, source: str, version: tuple[int, int]) -> ast.Module:
    """Parse `source` with the grammar of the pinned Python `version`, as `pinned_grammar` returned it, raising `SyntaxError` on what that grammar cannot parse.

    A source nested deeper than the parser can go cannot be parsed either: the parser raises
    `MemoryError` when its stack overflows, and `RecursionError` when building the tree of a
    parse runs past the recursion limit.

    A `SyntaxWarning` the parse raises, such as an invalid escape sequence, says nothing about
    the grammar, so it is kept out of the warning filters of whoever runs the gate and cannot
    turn a file that parses into one the gate did not finish.
    """
    with warnings.catch_warnings(action="ignore", category=SyntaxWarning):
        return ast.parse(source, filename=str(path), feature_version=version)


def find_suppressions(path: Path, version: tuple[int, int] | None = None) -> list[Suppression]:
    """Return every suppression comment and every `no_type_check` reference in the Python file at `path`, in line order.

    The file is parsed with the grammar of the pinned Python `version`; a call that gives none,
    as for one file looked at on its own, reads the pin with `pinned_grammar`. A run over many
    files reads the pin once and gives it to every call, so its files parse under one grammar.

    Raise `OSError` when the file cannot be read, `UnpinnedError` when no `version` is given and
    `pyproject.toml` pins no Python to parse it with, `SyntaxError`, `UnicodeDecodeError` or
    `tokenize.TokenError` when it cannot be decoded or tokenized, `SyntaxError` when the
    grammar of the pinned Python cannot parse it, and `MemoryError` or `RecursionError` when
    its parse runs deeper than the parser can go.
    """
    with tokenize.open(path) as reader:
        source = reader.read()
    tokens = list(tokenize.generate_tokens(io.StringIO(source).readline))
    comments = comment_suppressions(path, tokens)
    tree = parse_pinned(path, source, pinned_grammar() if version is None else version)
    references = no_type_check_references(path, tree, case_keywords(tokens))
    return sorted(comments + references)


def scan(path: Path, version: tuple[int, int] | None = None) -> list[Suppression] | Unfinished:
    """Return every finding in the Python file at `path`, parsed with the pinned Python `version` as `find_suppressions` reads it, or what the gate reported when it could not read, tokenize or parse that file, or, given no `version`, found no Python pinned to parse it with."""
    try:
        return find_suppressions(path, version)
    except (OSError, UnpinnedError, SyntaxError, UnicodeDecodeError, tokenize.TokenError, MemoryError, RecursionError) as error:
        return Unfinished(path=path, report=f"{type(error).__name__}: {error}")


def main(paths: list[Path]) -> int:
    """List every suppression comment and `no_type_check` reference found in the Python files among `paths`.

    When every file was parsed, print a count line and exit 1 on any finding and 0 on none.
    A file the gate cannot read, tokenize or parse is one it did not finish: print each
    finding of the other files all the same, then what the gate reported for each such
    file, then the same count line, in the same shape, as the last line, and exit 2. When no path is a Python file, nothing was checked: print a line
    saying so and exit 1. When `pyproject.toml` pins no `major.minor` pyright `pythonVersion`,
    or pins one the parser has no grammar for, no file can be parsed with the grammar of the pinned Python, so none is checked: print an
    error naming the key, then a count line with no finding as the last line, and exit 2. The pin
    is read once, before any file is checked, and every file of the run is parsed with it.
    """
    sources = [path for path in paths if is_python_source(path)]
    if not sources:
        sys.stdout.write(f"check_suppressions: no Python file among {len(paths)} path(s); nothing was checked\n")
        return 1
    try:
        version = pinned_grammar()
    except UnpinnedError as unpinned:
        sys.stdout.write(f"check_suppressions: {unpinned}\n")
        sys.stdout.write(f"check_suppressions: 0 finding(s) in {len(sources)} Python file(s)\n")
        return BLOCKED
    scans = [scan(path, version) for path in sources]
    found = [suppression for scanned in scans if not isinstance(scanned, Unfinished) for suppression in scanned]
    unfinished = [scanned for scanned in scans if isinstance(scanned, Unfinished)]
    for suppression in found:
        sys.stdout.write(f"{suppression.path}:{suppression.line}: {suppression.kind} `{suppression.marker}`\n")
    for file in unfinished:
        sys.stdout.write(f"{file.path}: {file.report}\n")
    sys.stdout.write(f"check_suppressions: {len(found)} finding(s) in {len(sources)} Python file(s)\n")
    if unfinished:
        return BLOCKED
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
