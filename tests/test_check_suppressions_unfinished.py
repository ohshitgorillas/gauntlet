"""Red tests for the suppression gate on a file its checker did not finish.

Source: the quality gates design spec, "Gates" intro:
a gate exits 2 when its checker could not finish, and a Python file the checker
cannot read or cannot parse is a file the checker did not finish: the gate exits 2,
whatever it found in the other files. The suppression gate's checker finds
markers by tokenizing ("Suppression gate", first bullet).
"""

from pathlib import Path

import pytest

from gates.check_suppressions import main

UNPARSEABLE = {
    "unterminated triple-quoted string": 'value = """never closed\n',
    "unindent matching no outer level": "if True:\n        first = 1\n    second = 2\n",
}


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize("source", UNPARSEABLE.values(), ids=UNPARSEABLE.keys())
def test_unparseable_file_alone_exits_2(tmp_path: Path, source: str) -> None:
    broken = _seed(tmp_path, "broken.py", source)

    assert main([broken]) == 2


@pytest.mark.parametrize("source", UNPARSEABLE.values(), ids=UNPARSEABLE.keys())
def test_unparseable_file_beside_clean_file_exits_2(tmp_path: Path, source: str) -> None:
    broken = _seed(tmp_path, "broken.py", source)
    clean = _seed(tmp_path, "clean.py", "value = 1\n")

    assert main([clean, broken]) == 2


@pytest.mark.parametrize("broken_first", [True, False], ids=["broken-first", "marker-first"])
def test_unparseable_file_beside_file_with_marker_exits_2(tmp_path: Path, *, broken_first: bool) -> None:
    broken = _seed(tmp_path, "broken.py", UNPARSEABLE["unterminated triple-quoted string"])
    dirty = _seed(tmp_path, "dirty.py", "value = 1  # noqa\n")
    paths = [broken, dirty] if broken_first else [dirty, broken]

    assert main(paths) == 2


def test_undecodable_file_beside_clean_file_exits_2(tmp_path: Path) -> None:
    undecodable = tmp_path / "undecodable.py"
    undecodable.write_bytes(b"value = '\xff\xfe'\n")
    clean = _seed(tmp_path, "clean.py", "value = 1\n")

    assert main([clean, undecodable]) == 2


def test_unreadable_file_beside_file_with_marker_exits_2(tmp_path: Path) -> None:
    unreadable = _seed(tmp_path, "unreadable.py", "value = 1\n")
    unreadable.chmod(0o000)
    dirty = _seed(tmp_path, "dirty.py", "value = 1  # noqa\n")

    assert main([dirty, unreadable]) == 2
