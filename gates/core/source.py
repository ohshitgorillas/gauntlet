"""Reading a Python file under the pinned Python: the pin, the file's text, tokens and tree, and its comment markers."""

import ast
import io
import re
import sys
import tokenize
import warnings
from collections.abc import Mapping
from dataclasses import dataclass
from tokenize import TokenInfo

from gates.core.project import Project, Source
from gates.core.report import GateError, Unfinished

PIN_KEYS = ("tool", "pyright", "pythonVersion")

MAJOR_MINOR = re.compile(r"[0-9]+\.[0-9]+")

# The oldest Python whose grammar `ast.parse` has, by its `feature_version` documentation; the newest is the interpreter's own.
OLDEST_GRAMMAR = (3, 7)


@dataclass(frozen=True)
class Parsed:
    """A Python file read and parsed: its Source, its decoded text, its tokens and its tree."""

    source: Source
    text: str
    tokens: tuple[TokenInfo, ...]
    tree: ast.Module


def pinned_version(project: Project) -> tuple[int, int]:
    """Return the Python the project is pinned to, as `(major, minor)`: pyright's pythonVersion, the one pin rule.

    A pin that is not set, is not a `major.minor` version, or is a version the parser has no grammar for pins
    nothing: `ast.parse` takes a version outside the grammars it has and parses with another, which would fall back to
    a grammar that is not the pin's. Raises GateError naming the key, or the file when it cannot be read.
    """
    key = f"{project.config}: {'.'.join(PIN_KEYS)}"
    version = project.setting(*PIN_KEYS)
    if version is None:
        message = f"{key}: not set"
        raise GateError(message)
    if not isinstance(version, str) or MAJOR_MINOR.fullmatch(version) is None:
        message = f"{key}: {version!r} is not a `major.minor` version"
        raise GateError(message)
    major, minor = version.split(".")
    pinned = (int(major), int(minor))
    newest = (sys.version_info.major, sys.version_info.minor)
    if not OLDEST_GRAMMAR <= pinned <= newest:
        message = (
            f"{key}: {version!r} is a version the parser has no grammar for:"
            f" the parser of Python {newest[0]}.{newest[1]} has the grammars of"
            f" {OLDEST_GRAMMAR[0]}.{OLDEST_GRAMMAR[1]} through {newest[0]}.{newest[1]}"
        )
        raise GateError(message)
    return pinned


def parse(source: Source, version: tuple[int, int]) -> Parsed | Unfinished:
    """Read, decode, parse with the grammar of Python `version`, and tokenize the file; or say why it is unfinished.

    An OSError, a SyntaxError, a file that cannot be decoded, a MemoryError or RecursionError of a parse deeper than
    the parser can go, and any warning raised meanwhile, whatever the caller's warning filters say, is an Unfinished
    whose report names the file as given. The file is parsed before it is tokenized, because the tokenizer copies a
    token's whole line into every token, so a file too deep to parse stops before that copying starts.
    """
    given = source.given
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            data = source.absolute.read_bytes()
            encoding, _ = tokenize.detect_encoding(io.BytesIO(data).readline)
            text = data.decode(encoding)
            tree = ast.parse(text, filename=str(given), feature_version=version)
            tokens = tuple(tokenize.generate_tokens(io.StringIO(text).readline))
        except (OSError, SyntaxError, UnicodeDecodeError, tokenize.TokenError, MemoryError, RecursionError) as error:
            return Unfinished(f"{given}: {type(error).__name__}: {error}")
    if caught:
        return Unfinished(
            "\n".join(f"{given}:{warning.lineno}: {warning.category.__name__}: {warning.message}" for warning in caught)
        )
    return Parsed(source=source, text=text, tokens=tokens, tree=tree)


def comment_markers(parsed: Parsed, markers: Mapping[str, re.Pattern[str]]) -> list[tuple[int, tuple[str, ...]]]:
    """Return each comment that carries a marker: its line, and the names of its markers in the order of `markers`."""
    carried: list[tuple[int, tuple[str, ...]]] = []
    for token in parsed.tokens:
        if token.type != tokenize.COMMENT:
            continue
        names = tuple(name for name, pattern in markers.items() if pattern.search(token.string))
        if names:
            carried.append((token.start[0], names))
    return carried
