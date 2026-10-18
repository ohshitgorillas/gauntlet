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

PYTHON_SUFFIXES = frozenset({".py", ".pyi", ".pyw"})
PYTHON_SHEBANG = re.compile(rb"^#!.*python")


@dataclass(frozen=True)
class Suppression:
    """One suppression comment: where it is and which marker it carries."""

    path: Path
    line: int
    marker: str


def is_python_source(path: Path) -> bool:
    """Return whether `path` is a regular file holding Python, by suffix or by shebang."""
    if not path.is_file():
        return False
    if path.suffix in PYTHON_SUFFIXES:
        return True
    with path.open("rb") as source:
        first_line = source.readline()
    return PYTHON_SHEBANG.match(first_line) is not None


def find_suppressions(path: Path) -> list[Suppression]:
    """Return every suppression comment in the Python file at `path`."""
    with tokenize.open(path) as source:
        comments = [token for token in tokenize.generate_tokens(source.readline) if token.type == tokenize.COMMENT]
    return [
        Suppression(path=path, line=comment.start[0], marker=marker)
        for comment in comments
        for marker, pattern in MARKERS.items()
        if pattern.search(comment.string)
    ]


def main(paths: list[Path]) -> int:
    """Exit 1 and list every suppression found in `paths`; exit 0 when none."""
    sources = [path for path in paths if is_python_source(path)]
    if not sources:
        sys.stdout.write(f"check_suppressions: no Python file among {len(paths)} path(s); nothing was checked\n")
        return 1
    found = [suppression for path in sources for suppression in find_suppressions(path)]
    for suppression in found:
        sys.stdout.write(f"{suppression.path}:{suppression.line}: suppression comment `{suppression.marker}`\n")
    sys.stdout.write(f"check_suppressions: {len(found)} suppression comment(s) in {len(sources)} Python file(s)\n")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main([Path(argument) for argument in sys.argv[1:]]))
