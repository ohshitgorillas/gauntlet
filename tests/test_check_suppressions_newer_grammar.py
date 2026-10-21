"""Red tests for the suppression gate parsing with the grammar of the pinned Python, 3.12.

Sources: the quality-gates design spec under docs/superpowers/specs/, "Suppression gate",
third item (finding a `typing.no_type_check` reference takes a parse with the grammar of
the pinned Python, 3.12, so a file the gate can tokenize but that grammar cannot parse,
syntax added in 3.13 or later included, is a file the gate did not finish, and the gate
exits 2 by the rule of the Gates intro), "Types" (`python_version = "3.12"`) and "Gates"
(exit 1 with one or more findings, 2 when the checker could not finish, whatever it found
in the other files).
"""

from pathlib import Path

import pytest

from gates.check_suppressions import main
from gates.core.project import Source
from gates.core.report import Unfinished
from gates.core.source import parse

FINDINGS_STATUS = 1
PINNED = (3, 12)

UNFINISHED_STATUS = 2

NEWER_SOURCES = [
    "def seeded[T = int](value: T) -> T:\n    return value\n",
    "class Seeded[T = int]:\n    pass\n",
    "type Alias[T = int] = list[T]\n",
    "try:\n    pass\nexcept ValueError, TypeError:\n    pass\n",
    'value = t"seeded"\n',
]

PINNED_SOURCES = [
    "def first[T](items: list[T]) -> T:\n    return items[0]\n",
    "class Box[T]:\n    pass\n",
    "type Alias[T] = list[T]\n",
]

MARKER_LINE = "value = 1  # fmt: skip\n"

FINDING_SOURCE = "import typing\n\n\n@typing.no_type_check\ndef seeded() -> None:\n    pass\n"


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize("source", NEWER_SOURCES)
def test_gate_exits_unfinished_on_syntax_added_after_3_12(tmp_path: Path, source: str) -> None:
    """Exit with the unfinished status on a file using syntax added in 3.13 or later."""
    path = _seed(tmp_path, "newer.py", source)

    assert main([path]) == UNFINISHED_STATUS


@pytest.mark.parametrize("source", NEWER_SOURCES)
def test_gate_exits_unfinished_on_newer_syntax_carrying_a_marker(tmp_path: Path, source: str) -> None:
    """Exit with the unfinished status on newer syntax even when the same file carries a comment marker."""
    path = _seed(tmp_path, "newer.py", MARKER_LINE + source)

    assert main([path]) == UNFINISHED_STATUS


@pytest.mark.parametrize("source", NEWER_SOURCES)
def test_parse_names_the_file_with_newer_syntax_as_unfinished(tmp_path: Path, source: str) -> None:
    """Return the file using syntax added in 3.13 or later as unfinished, naming its path."""
    path = _seed(tmp_path, "newer.py", source)
    result = parse(Source(given=path, absolute=path), PINNED)

    assert isinstance(result, Unfinished)
    assert result.text.startswith(f"{path}: ")


@pytest.mark.parametrize("newer_first", [True, False])
def test_gate_exits_unfinished_on_newer_syntax_whatever_other_files_hold(tmp_path: Path, newer_first: bool) -> None:
    """Exit with the unfinished status when one file uses newer syntax and another carries a finding."""
    newer = _seed(tmp_path, "newer.py", NEWER_SOURCES[0])
    flagged = _seed(tmp_path, "flagged.py", FINDING_SOURCE)
    paths = [newer, flagged] if newer_first else [flagged, newer]

    assert main(paths) == UNFINISHED_STATUS


@pytest.mark.parametrize("source", PINNED_SOURCES)
def test_gate_finishes_on_syntax_the_3_12_grammar_parses(tmp_path: Path, source: str) -> None:
    """Exit with the findings status, not the unfinished one, on 3.12 type-parameter syntax carrying a marker."""
    path = _seed(tmp_path, "pinned.py", MARKER_LINE + source)

    assert main([path]) == FINDINGS_STATUS
