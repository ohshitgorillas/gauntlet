"""Red tests for which comments the suppression gate takes as mypy, pyright and fmt directives.

Sources: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate":
its opening paragraph (comment markers are found by tokenizing and match only inside a
comment token, never inside a string; a marker matches anywhere in the comment, ignoring
case and the whitespace around the colon and between its words; a comment that carries
more than one marker is one finding that names every marker it carries) and its second
item (a `# mypy:`, `# pyright:`, `# fmt: off` or `# fmt: skip` comment).
"""

from pathlib import Path

import pytest

from tests.support.suppressions import find_suppressions

CANONICAL_DIRECTIVES = [
    "# mypy: ignore-errors",
    "# pyright: basic",
    "# fmt: off",
    "# fmt: skip",
]

SPELLED_DIRECTIVES = [
    "#mypy: strict",
    "# FMT: OFF",
    "value = 1  # note; fmt:skip",
    "# MyPy :ignore-errors",
    "#\tPyRight  :  basic",
    "# Fmt :Skip",
    "# fmt:\toff",
    "# fmt  :  off",
]

EMBEDDED_DIRECTIVES = [
    "# kept as written; mypy: ignore-errors",
    "value = 1  # see the issue, pyright: basic",
    "# layout below, fmt: off",
    "value = 1  # aligned by hand fmt: skip",
]

STRING_SOURCES = [
    ('text = "# mypy: strict"\nvalue = 1  # fmt: skip\n', 2),
    ("text = '# FMT: OFF'\n# pyright: basic\n", 2),
    ('doc = """\n# mypy: ignore-errors\n# fmt: off\n"""\n# fmt: skip\n', 5),
    ('label = f"{1} # pyright: basic"\n# mypy: strict\n', 2),
    ("raw = rb'# fmt: skip'\n# fmt: off\n", 2),
    ('def seeded() -> None:\n    """Keep # fmt: off here."""\n\n\n# mypy: strict\n', 5),
]

MULTI_MARKER_SOURCES = [
    "value = 1  # fmt: skip; mypy: ignore-errors\n",
    "# pyright: basic  fmt: off\n",
    "# FMT:OFF  MYPY:strict\n",
]

MULTI_MARKER_NAMES = [
    ("value = 1  # fmt: skip; mypy: ignore-errors\n", ("fmtskip", "mypy")),
    ("# pyright: basic  fmt: off\n", ("pyright", "fmtoff")),
    ("# FMT:OFF  MYPY:strict\n", ("fmtoff", "mypy")),
]

SINGLE_MARKER_NAMES = [
    ("# FMT: OFF\n", "fmtoff"),
    ("value = 1  # note; fmt:skip\n", "fmtskip"),
    ("#mypy: strict\n", "mypy"),
    ("# Pyright : basic\n", "pyright"),
]


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "seeded.py"
    path.write_text(source, encoding="utf-8")
    return path


def _letters(text: str) -> str:
    return "".join(char for char in text.lower() if char.isalpha())


@pytest.mark.parametrize("directive", CANONICAL_DIRECTIVES)
def test_directive_comment_is_one_finding_on_its_line(tmp_path: Path, directive: str) -> None:
    """Report a mypy, pyright or fmt directive comment as one finding on the line it sits on."""
    path = _seed(tmp_path, "first = 1\nsecond = 2\n" + directive + "\n")

    assert [finding.line for finding in find_suppressions(path)] == [3]


@pytest.mark.parametrize("directive", SPELLED_DIRECTIVES)
def test_directive_matches_whatever_its_case_and_spacing(tmp_path: Path, directive: str) -> None:
    """Match a directive whatever its case and the whitespace around its colon and between its words."""
    path = _seed(tmp_path, "first = 1\n" + directive + "\n")

    assert [finding.line for finding in find_suppressions(path)] == [2]


@pytest.mark.parametrize("directive", EMBEDDED_DIRECTIVES)
def test_directive_matches_anywhere_in_the_comment(tmp_path: Path, directive: str) -> None:
    """Match a directive that stands after other words in the comment."""
    path = _seed(tmp_path, "first = 1\n" + directive + "\n")

    assert [finding.line for finding in find_suppressions(path)] == [2]


@pytest.mark.parametrize(("source", "comment_line"), STRING_SOURCES)
def test_directive_inside_a_string_is_no_finding(tmp_path: Path, source: str, comment_line: int) -> None:
    """Report only the directive in a comment token, never one inside a string literal."""
    path = _seed(tmp_path, source)

    assert [finding.line for finding in find_suppressions(path)] == [comment_line]


def test_directive_after_a_string_on_the_same_line_names_only_the_comment(tmp_path: Path) -> None:
    """Name the marker of the comment and not the marker inside the string before it."""
    path = _seed(tmp_path, 'text = "# mypy: strict"  # fmt: skip\n')
    findings = find_suppressions(path)

    assert [(finding.line, "fmtskip" in _letters(finding.marker), "mypy" in _letters(finding.marker)) for finding in findings] == [(1, True, False)]


@pytest.mark.parametrize("source", MULTI_MARKER_SOURCES)
def test_comment_with_several_directives_is_one_finding(tmp_path: Path, source: str) -> None:
    """Report a comment that carries more than one directive as a single finding."""
    path = _seed(tmp_path, source)

    assert [finding.line for finding in find_suppressions(path)] == [1]


@pytest.mark.parametrize(("source", "names"), MULTI_MARKER_NAMES)
def test_comment_with_several_directives_names_each_of_them(tmp_path: Path, source: str, names: tuple[str, str]) -> None:
    """Name every directive a comment carries in its one finding."""
    path = _seed(tmp_path, source)
    findings = find_suppressions(path)

    assert [[name in _letters(finding.marker) for name in names] for finding in findings] == [[True, True]]


@pytest.mark.parametrize(("source", "name"), SINGLE_MARKER_NAMES)
def test_finding_names_the_directive_it_found(tmp_path: Path, source: str, name: str) -> None:
    """Name the directive a comment carries in its finding."""
    path = _seed(tmp_path, source)

    assert [name in _letters(finding.marker) for finding in find_suppressions(path)] == [True]


def test_each_directive_comment_is_its_own_finding(tmp_path: Path) -> None:
    """Report every directive comment in a file, and not a `fmt: on` comment, which is no directive the gate bans."""
    path = _seed(tmp_path, "# fmt: off\nvalue = 1\n# fmt: on\nother = 2  # fmt: skip\n")

    assert [finding.line for finding in find_suppressions(path)] == [1, 4]
