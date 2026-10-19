"""Red tests for the pyright gate on a file whose parse cannot run to its end.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates",
first paragraph: a gate parses a Python file with the grammar of the pinned
Python; a parse that cannot run to its end, as when it runs out of depth or
memory, is one the gate could not make, and its file is a file the checker did
not finish, so the gate exits 2 whatever it found in the other files.

The deep sources are valid Python by the grammar but nest too deep for the
parser of the pinned Python to build them: a long chain of unary minus
overflows the parser's stack, and a long chain of additions builds an AST too
deep to hand back.
"""

from pathlib import Path

import pytest

from gates.check_pyright import main

DEPTH = 100_000

UNARY_CHAIN = "value = " + "-" * DEPTH + "1\n"

ADDITION_CHAIN = "value = 1" + " + 1" * DEPTH + "\n"

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

MISSING_PARAMETER_TYPE = "def double(value) -> int:\n    return value * 2\n"

DEEP_SOURCES = [
    pytest.param(UNARY_CHAIN, id="unary-chain"),
    pytest.param(ADDITION_CHAIN, id="addition-chain"),
]


def _seed(directory: Path, name: str, source: str) -> Path:
    path = directory / name
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize("source", DEEP_SOURCES)
def test_deep_file_alone_is_unfinished(tmp_path: Path, source: str) -> None:
    """A lone file whose parse runs out of depth or memory exits 2."""
    deep = _seed(tmp_path, "deep.py", source)

    assert main([deep]) == 2


@pytest.mark.parametrize("source", DEEP_SOURCES)
def test_deep_file_beside_clean_file_is_unfinished(tmp_path: Path, source: str) -> None:
    """A clean file given alongside does not turn the unfinished run into a pass."""
    clean = _seed(tmp_path, "clean.py", CLEAN)
    deep = _seed(tmp_path, "deep.py", source)

    assert main([clean, deep]) == 2


@pytest.mark.parametrize("source", DEEP_SOURCES)
def test_deep_file_beside_finding_is_unfinished(tmp_path: Path, source: str) -> None:
    """A finding in another file does not turn the unfinished run into exit 1."""
    flawed = _seed(tmp_path, "flawed.py", MISSING_PARAMETER_TYPE)
    deep = _seed(tmp_path, "deep.py", source)

    assert main([flawed, deep]) == 2
