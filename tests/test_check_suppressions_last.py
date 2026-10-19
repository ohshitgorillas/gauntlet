"""Red tests for the count line of a suppression gate run whose checker could not finish.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: a gate "exits 2 when its
checker could not finish" and "prints its count line on every run"; "The count line of a run whose checker finished
reads `<gate>: N finding(s) in M Python file(s)`, where `<gate>` is the name of the gate script without its extension";
"A run whose checker could not finish prints the same count line, in the same shape, as the last line it prints, after
what the checker reported; a line saying on how many files the checker could not finish is not a count line." and "A
Python file the checker cannot read or cannot parse is a file the checker did not finish: the gate prints what the
checker reported for that file and exits 2, whatever it found in the other files." The suppression gate's checker
tokenizes every file and parses it with the grammar of the pinned Python, 3.12, so a file that grammar cannot parse,
syntax added in 3.13 or later included, is a file it did not finish ("Suppression gate", first and third items).

The documents spell the count line of an unfinished run nowhere but in the count line's own shape, so the last line is
held to that shape with any N and M. A run that ends on a count line but did not exit 2 finished, so each claim is held
together with the exit status. The documents name no stream, so stdout and stderr go to one buffer while the gate runs,
which keeps the order the run printed its lines in.

The file name, test names and ids are kept short so that pytest's one-line summary has room to name the exception a
test fails with.
"""

import contextlib
import io
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from gates.check_suppressions import main

GATE = "check_suppressions"

UNFINISHED = 2

COUNT_LINE_SHAPE = re.compile(rf"{GATE}: \d+ finding\(s\) in \d+ Python file\(s\)")

CLEAN = "value = 1\n"

MARKED = "value = 1  # noqa\n"


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _untokenizable(tmp_path: Path) -> list[Path]:
    """One file the tokenizer cannot finish: a triple-quoted string never closed."""
    return [_seed(tmp_path, "broken.py", 'value = """never closed\n')]


def _unparseable(tmp_path: Path) -> list[Path]:
    """One file that tokenizes but that no grammar parses."""
    return [_seed(tmp_path, "broken.py", "value = = 1\n")]


def _newer_grammar(tmp_path: Path) -> list[Path]:
    """One file that tokenizes but holds syntax added in 3.13, a type parameter default, beyond the pinned 3.12."""
    return [_seed(tmp_path, "newer.py", "type Alias[T = int] = list[T]\n")]


def _beside_clean(tmp_path: Path) -> list[Path]:
    """A clean file, then a file the tokenizer cannot finish."""
    clean = _seed(tmp_path, "clean.py", CLEAN)
    return [clean, *_untokenizable(tmp_path)]


def _beside_marker(tmp_path: Path) -> list[Path]:
    """A file with a marker, then a file the tokenizer cannot finish."""
    dirty = _seed(tmp_path, "dirty.py", MARKED)
    return [dirty, *_untokenizable(tmp_path)]


def _undecodable(tmp_path: Path) -> list[Path]:
    """A clean file, then a file that is not valid UTF-8."""
    clean = _seed(tmp_path, "clean.py", CLEAN)
    undecodable = tmp_path / "undecodable.py"
    undecodable.write_bytes(b"value = '\xff\xfe'\n")
    return [clean, undecodable]


def _unreadable(tmp_path: Path) -> list[Path]:
    """A file with a marker, then a file no one may read."""
    dirty = _seed(tmp_path, "dirty.py", MARKED)
    unreadable = _seed(tmp_path, "unreadable.py", CLEAN)
    unreadable.chmod(0o000)
    return [dirty, unreadable]


SEEDS = [
    pytest.param(_untokenizable, id="tok"),
    pytest.param(_unparseable, id="ast"),
    pytest.param(_newer_grammar, id="313"),
    pytest.param(_beside_clean, id="clean"),
    pytest.param(_beside_marker, id="mark"),
    pytest.param(_undecodable, id="utf8"),
    pytest.param(_unreadable, id="perm"),
]


def _run(paths: list[Path]) -> tuple[int, list[str]]:
    """Run the gate with stdout and stderr in one buffer; return its exit status and every line it printed."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        status = main(paths)
    return status, buffer.getvalue().splitlines()


def _is_count_line(line: str) -> bool:
    return COUNT_LINE_SHAPE.fullmatch(line) is not None


@pytest.mark.parametrize("seed", SEEDS)
def test_last(tmp_path: Path, seed: Callable[[Path], list[Path]]) -> None:
    """The last line an unfinished run prints is a count line, never a line counting the files it did not finish.

    The count line is the one line of the run that counts `file(s)`; any other line that does is a line counting files.
    """
    status, lines = _run(seed(tmp_path))
    counting = [line for line in lines if "file(s)" in line]

    assert (status, counting, [_is_count_line(line) for line in lines[-1:]]) == (UNFINISHED, lines[-1:], [True])


@pytest.mark.parametrize("seed", SEEDS)
def test_after(tmp_path: Path, seed: Callable[[Path], list[Path]]) -> None:
    """What the checker reported for the unfinished file, the last one given, comes before the count line.

    The report is read only for the unfinished file's name, so another file's finding cannot stand in for it.
    """
    paths = seed(tmp_path)
    status, lines = _run(paths)
    reported = paths[-1].name in "\n".join(lines[:-1])

    assert (status, reported, [_is_count_line(line) for line in lines[-1:]]) == (UNFINISHED, True, [True])
