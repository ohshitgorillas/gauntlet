# Copyright 2026 oh shit, gorillas!
"""Red tests for the gates core source reader: the pinned version, a parse under it, and the comment markers it holds.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "source.py: reading a Python file under
the pinned version", and its decisions 14 to 16; the quality gates design spec, "Gates", intro: a gate "parses it with
the grammar of the pinned Python, which is pyright's `pythonVersion` in `pyproject.toml`, and a `pyproject.toml` that
sets no `pythonVersion`, or one that is not a `major.minor` version, is one the checker could not finish: the gate
prints an error that names the key ... and never falls back to the grammar of the interpreter it runs under"; and "A
warning raised while a gate parses a Python file is an error for that parse, so its file is a file the checker did not
finish: the gate prints the warning as the checker's report".

`pinned_version(project)` is the pin as `(major, minor)`, or a GateError naming the key; a version the parser has no
grammar for pins nothing (decision 14). `parse(source, version)` reads, decodes, tokenizes and parses the file; an
OSError, a SyntaxError, any warning, a MemoryError or a RecursionError is an Unfinished with its report, which names
the file as given (decision 15), a warning's naming its category. `comment_markers(parsed, markers)` gives each line
whose comment carries a marker, with the names of every marker it carries in the order of `markers` (decision 16).

The deep sources nest far past what the parser can build, as the suppression and pyright gate tests seed them.
"""

import ast
import re
import tokenize
import warnings
from pathlib import Path
from typing import Literal

import pytest

from gates.core.project import Project, Source
from gates.core.report import GateError, Unfinished
from gates.core.source import Parsed, comment_markers, parse, pinned_version

PIN = (3, 12)

KEY = "pythonVersion"

STRICT = '[tool.pyright]\ntypeCheckingMode = "strict"\n'

DEPTH = 100_000

DEEP = {
    "unary-minus": "value = " + "-" * DEPTH + "1\n",
    "addition": "value = 1" + " + 1" * DEPTH + "\n",
    "not": "value = " + "not " * DEPTH + "True\n",
}

MARKERS = {
    "noqa": re.compile(r"noqa", re.IGNORECASE),
    "type: ignore": re.compile(r"type\s*:\s*ignore", re.IGNORECASE),
}


def _project(root: Path, text: str) -> Project:
    (root / "pyproject.toml").write_text(text, encoding="utf-8")
    return Project(root)


def _source(path: Path, data: str | bytes) -> Source:
    if isinstance(data, str):
        path.write_text(data, encoding="utf-8")
    else:
        path.write_bytes(data)
    return Source(given=path, absolute=path)


def _parsed(tmp_path: Path, text: str) -> Parsed | None:
    result = parse(_source(tmp_path / "a.py", text), PIN)
    return result if isinstance(result, Parsed) else None


# pinned_version


@pytest.mark.parametrize(
    ("version", "pin"), [("3.12", (3, 12)), ("3.10", (3, 10)), ("3.7", (3, 7))]
)
def test_pin(tmp_path: Path, version: str, pin: tuple[int, int]) -> None:
    """The pin is pyright's pythonVersion as (major, minor)."""
    assert (
        pinned_version(_project(tmp_path, STRICT + f'pythonVersion = "{version}"\n'))
        == pin
    )


@pytest.mark.parametrize(
    "text",
    [
        pytest.param('[tool.mypy]\npython_version = "3.12"\n', id="no-table"),
        pytest.param(STRICT, id="no-key"),
        pytest.param(
            STRICT + '\n[tool.mypy]\npythonVersion = "3.12"\n', id="other-table"
        ),
        pytest.param(STRICT + 'pythonVersion = "3"\n', id="major"),
        pytest.param(STRICT + 'pythonVersion = "3.12.0"\n', id="micro"),
        pytest.param(STRICT + 'pythonVersion = "py312"\n', id="py312"),
        pytest.param(STRICT + 'pythonVersion = "3.x"\n', id="x"),
        pytest.param(STRICT + 'pythonVersion = ""\n', id="empty"),
        pytest.param(STRICT + 'pythonVersion = " 3.12"\n', id="space"),
        pytest.param(STRICT + "pythonVersion = 312\n", id="int"),
        pytest.param(STRICT + "pythonVersion = 3.12\n", id="float"),
    ],
)
def test_unpinned(tmp_path: Path, text: str) -> None:
    """No pythonVersion, or one that is not a major.minor version, is a GateError naming the key."""
    with pytest.raises(GateError) as raised:
        pinned_version(_project(tmp_path, text))

    assert KEY in raised.value.report


@pytest.mark.parametrize("version", ["2.7", "3.6", "4.0", "3.99"])
def test_no_grammar(tmp_path: Path, version: str) -> None:
    """A version the parser has no grammar for pins nothing: a GateError naming the key (decision 14)."""
    with pytest.raises(GateError) as raised:
        pinned_version(_project(tmp_path, STRICT + f'pythonVersion = "{version}"\n'))

    assert KEY in raised.value.report


def test_pin_unreadable(tmp_path: Path) -> None:
    """A pyproject.toml that cannot be read pins nothing: a GateError naming the file."""
    project = Project(tmp_path)
    with pytest.raises(GateError) as raised:
        pinned_version(project)

    assert str(project.config) in raised.value.report


# parse


def test_parsed(tmp_path: Path) -> None:
    """A file that parses gives its Source, its text, its tokens and its tree."""
    text = "value = 1  # one\n\n\ndef double(x: int) -> int:\n    return x * 2\n"
    source = _source(tmp_path / "a.py", text)
    result = parse(source, PIN)
    assert isinstance(result, Parsed)

    assert (result.source, result.text, ast.dump(result.tree)) == (
        source,
        text,
        ast.dump(ast.parse(text)),
    )


def test_tokens(tmp_path: Path) -> None:
    """The tokens are the file's, in order: a comment is a token of its own."""
    parsed = _parsed(tmp_path, "value = 1  # one\n# two\n")
    assert parsed is not None

    assert [
        (token.type, token.string, token.start[0])
        for token in parsed.tokens
        if token.type == tokenize.COMMENT
    ] == [
        (tokenize.COMMENT, "# one", 1),
        (tokenize.COMMENT, "# two", 2),
    ]


def test_tokens_whole(tmp_path: Path) -> None:
    """The tokens run from the file's first to its end marker."""
    parsed = _parsed(tmp_path, "value = 1\n")
    assert parsed is not None

    assert [token.string for token in parsed.tokens] == ["value", "=", "1", "\n", ""]


def test_decoded_by_cookie(tmp_path: Path) -> None:
    """The text is decoded as the file's coding cookie says."""
    data = "# -*- coding: latin-1 -*-\nname = 'café'\n"
    result = parse(_source(tmp_path / "a.py", data.encode("latin-1")), PIN)
    assert isinstance(result, Parsed)

    assert result.text == data


def test_pinned_grammar(tmp_path: Path) -> None:
    """A file is parsed with the grammar of the version given, not the interpreter's: `type` needs 3.12."""
    source = _source(tmp_path / "a.py", "type Alias = int\n")

    assert (
        isinstance(parse(source, (3, 11)), Unfinished),
        isinstance(parse(source, (3, 12)), Parsed),
    ) == (True, True)


def test_older_grammar(tmp_path: Path) -> None:
    """A `match` statement is no syntax of 3.9."""
    source = _source(tmp_path / "a.py", "match value:\n    case 1:\n        pass\n")

    assert isinstance(parse(source, (3, 9)), Unfinished)


def _unfinished(source: Source) -> str | None:
    result = parse(source, PIN)
    return result.text if isinstance(result, Unfinished) else None


def test_missing(tmp_path: Path) -> None:
    """A file that cannot be read is Unfinished, its report naming the file and the error."""
    path = tmp_path / "gone.py"
    text = _unfinished(Source(given=path, absolute=path))
    assert text is not None

    assert (text.startswith(f"{path}: "), "FileNotFoundError" in text) == (True, True)


def test_directory(tmp_path: Path) -> None:
    """A path that is a directory cannot be read: Unfinished."""
    path = tmp_path / "package.py"
    path.mkdir()

    text = _unfinished(Source(given=path, absolute=path))
    assert text is not None

    assert text.startswith(f"{path}: ")


def test_unreadable(tmp_path: Path) -> None:
    """A file its mode makes unreadable is Unfinished."""
    source = _source(tmp_path / "a.py", "value = 1\n")
    source.absolute.chmod(0)

    text = _unfinished(source)
    assert text is not None

    assert "PermissionError" in text


def test_names_given(tmp_path: Path) -> None:
    """The report names the file as given, not its absolute path."""
    absolute = tmp_path / "gone.py"

    text = _unfinished(Source(given=Path("gone.py"), absolute=absolute))
    assert text is not None

    assert text.startswith("gone.py: ")


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("def broken(:\n", id="invalid"),
        pytest.param("value = (\n", id="unclosed"),
        pytest.param("if True:\n  a = 1\n    b = 2\n", id="indent"),
        pytest.param("value = 1\x00\n", id="null-byte"),
    ],
)
def test_syntax_error(tmp_path: Path, text: str) -> None:
    """A file the grammar cannot parse is Unfinished, its report naming the file."""
    path = tmp_path / "a.py"

    report = _unfinished(_source(path, text))
    assert report is not None

    assert report.startswith(f"{path}: ")


@pytest.mark.parametrize(
    "data",
    [
        pytest.param(b"name = '\xff'\n", id="not-utf8"),
        pytest.param(b"# coding: no-such-codec\nvalue = 1\n", id="unknown-cookie"),
        pytest.param(b"# coding: ascii\nname = '\xc3\xa9'\n", id="against-cookie"),
    ],
)
def test_undecodable(tmp_path: Path, data: bytes) -> None:
    """A file that cannot be decoded is Unfinished, its report naming the file."""
    path = tmp_path / "a.py"

    report = _unfinished(_source(path, data))
    assert report is not None

    assert report.startswith(f"{path}: ")


@pytest.mark.parametrize("source", DEEP.values(), ids=DEEP.keys())
def test_too_deep(tmp_path: Path, source: str) -> None:
    """A parse that runs deeper than the parser can go is Unfinished, never an error out of parse."""
    path = tmp_path / "deep.py"

    report = _unfinished(_source(path, source))
    assert report is not None

    assert report.startswith(f"{path}: ")


def test_warning(tmp_path: Path) -> None:
    """A warning raised by the parse is an error for it: Unfinished, the report naming the file, line and category."""
    path = tmp_path / "a.py"
    text = _unfinished(_source(path, 'value = 1\npattern = "\\d"\n'))
    assert text is not None

    assert (text.startswith(f"{path}:2: "), "SyntaxWarning" in text) == (True, True)


@pytest.mark.parametrize("action", ["ignore", "error", "default"])
def test_warning_whatever_filters(
    tmp_path: Path, action: Literal["ignore", "error", "default"]
) -> None:
    """A parse warning is reported as a warning whatever the warning filters of the caller say."""
    source = _source(tmp_path / "a.py", 'pattern = "\\d"\n')
    with warnings.catch_warnings(action=action):
        result = parse(source, PIN)
    assert isinstance(result, Unfinished)

    assert "SyntaxWarning" in result.text


def test_warning_leaves_filters(tmp_path: Path) -> None:
    """A parse leaves the caller's warning filters as they were."""
    before = list(warnings.filters)
    parse(_source(tmp_path / "a.py", 'pattern = "\\d"\n'), PIN)

    assert list(warnings.filters) == before


# comment_markers


def test_markers(tmp_path: Path) -> None:
    """Each line whose comment carries a marker, with the names of its markers in the order of the table."""
    parsed = _parsed(
        tmp_path, "a = 1  # noqa\nb = 2  # plain\nc = 3  # TYPE: ignore and NOQA\n"
    )
    assert parsed is not None

    assert comment_markers(parsed, MARKERS) == [
        (1, ("noqa",)),
        (3, ("noqa", "type: ignore")),
    ]


def test_markers_in_strings(tmp_path: Path) -> None:
    """A marker inside a string is in no comment."""
    parsed = _parsed(tmp_path, 'a = "# noqa"\nb = """\n# type: ignore\n"""\n')
    assert parsed is not None

    assert comment_markers(parsed, MARKERS) == []


def test_markers_comment_line(tmp_path: Path) -> None:
    """A comment on a line of its own is read too, at its own line."""
    parsed = _parsed(tmp_path, "a = 1\n\n# type: ignore\n")
    assert parsed is not None

    assert comment_markers(parsed, MARKERS) == [(3, ("type: ignore",))]


def test_no_markers(tmp_path: Path) -> None:
    """With no marker table, no line carries a marker."""
    parsed = _parsed(tmp_path, "a = 1  # noqa\n")
    assert parsed is not None

    assert comment_markers(parsed, {}) == []
