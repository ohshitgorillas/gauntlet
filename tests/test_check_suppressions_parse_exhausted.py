# Copyright 2026 oh shit, gorillas!
"""Red tests for the suppression gate on a file whose parse cannot finish.

Sources: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item (finding a `typing.no_type_check` reference takes a parse with the grammar of
the pinned Python, so a file the gate can tokenize but cannot parse is a file the gate
did not finish, and the gate exits 2 by the rule of the Gates intro), and "Gates" (a gate
exits 2 when its checker could not finish; a Python file the checker cannot parse is a
file the checker did not finish, and the gate exits 2 whatever it found in the other files).

Each source below is plain tokens, nested far past the depth any parser can recurse to,
so its parse cannot finish while its tokenizing can.
"""

from pathlib import Path

import pytest

from gates.check_suppressions import main
from gates.core.project import Source
from gates.core.report import Unfinished
from gates.core.source import parse

PINNED = (3, 12)

UNFINISHED_STATUS = 2

DEPTH = 100_000

EXHAUSTING = {
    "unary minus": "value = " + "-" * DEPTH + "1\n",
    "not": "value = " + "not " * DEPTH + "True\n",
    "power": "value = " + "2 ** " * DEPTH + "2\n",
    "lambda": "value = " + "lambda: " * DEPTH + "1\n",
}

MARKER_SOURCE = "value = 1  # noqa\n"


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize("source", EXHAUSTING.values(), ids=EXHAUSTING.keys())
def test_gate_exits_unfinished_on_a_parse_past_any_depth(
    tmp_path: Path, source: str
) -> None:
    """Exit with the unfinished status on a file whose parse runs out of depth."""
    deep = _seed(tmp_path, "deep.py", source)

    assert main([deep]) == UNFINISHED_STATUS


@pytest.mark.parametrize(
    "deep_first", [True, False], ids=["deep-first", "marker-first"]
)
def test_gate_exits_unfinished_on_a_deep_parse_beside_a_finding(
    tmp_path: Path, *, deep_first: bool
) -> None:
    """Exit with the unfinished status when one file's parse runs out of depth and another carries a marker."""
    deep = _seed(tmp_path, "deep.py", EXHAUSTING["unary minus"])
    dirty = _seed(tmp_path, "dirty.py", MARKER_SOURCE)
    paths = [deep, dirty] if deep_first else [dirty, deep]

    assert main(paths) == UNFINISHED_STATUS


@pytest.mark.parametrize("source", EXHAUSTING.values(), ids=EXHAUSTING.keys())
def test_parse_names_the_file_whose_parse_ran_out_of_depth(
    tmp_path: Path, source: str
) -> None:
    """Return the file whose parse runs out of depth as unfinished, naming its path."""
    deep = _seed(tmp_path, "deep.py", source)
    result = parse(Source(given=deep, absolute=deep), PINNED)

    assert isinstance(result, Unfinished)
    assert result.text.startswith(f"{deep}: ")
