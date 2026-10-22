"""Red tests for the suppression gate on a tree whose `pyproject.toml` pins no Python it can parse with.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "A gate that parses a
Python file parses it with the grammar of the pinned Python, which is pyright's `pythonVersion` in `pyproject.toml`,
and a `pyproject.toml` that sets no `pythonVersion`, or one that is not a `major.minor` version, is one the checker
could not finish: the gate prints an error that names the key, then its count line as the last line it prints, and
exits 2, and never falls back to the grammar of the interpreter it runs under." The same paragraph: the gate "prints
its count line on every run", and "The count line of a run whose checker finished reads `<gate>: N finding(s) in M
Python file(s)`, where `<gate>` is the name of the gate script without its extension". The suppression gate parses
every file it checks ("Suppression gate", third item).

The gate takes its settings from the tree's `pyproject.toml`, so each test builds a tree of its own: a copy of the
`gates` package beside a seeded `pyproject.toml` and one seeded Python file, and runs the gate script there as a module
with that tree as its working directory, in a fresh interpreter. The documents name no stream, so stdout and stderr go
to one unbuffered pipe, which keeps the order the run printed its lines in.

The documents spell the count line of an unfinished run nowhere but in the count line's own shape, so the last line is
held to that shape with any N and M. A run that ends on a count line but did not exit 2 finished, so the key and the
count line are each held together with the exit status. Every seeded `pyproject.toml` sets pyright's strict mode, so
no seed is a pyright rule downgraded from strict.

The test names and ids are kept short so that pytest's one-line summary has room to name the exception a test fails
with.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gates import check_suppressions

GATE = "check_suppressions"

KEY = "pythonVersion"

UNFINISHED = 2

COUNT_LINE_SHAPE = re.compile(rf"{GATE}: \d+ finding\(s\) in \d+ Python file\(s\)")

STRICT = '[tool.pyright]\ntypeCheckingMode = "strict"\n'

UNPINNED = [
    pytest.param('[tool.mypy]\npython_version = "3.12"\n', id="table"),
    pytest.param(STRICT, id="nokey"),
    pytest.param(STRICT + '\n[tool.mypy]\npythonVersion = "3.12"\n', id="mypy"),
    pytest.param(STRICT + 'pythonVersion = "3"\n', id="major"),
    pytest.param(STRICT + 'pythonVersion = "3.12.0"\n', id="micro"),
    pytest.param(STRICT + 'pythonVersion = "py312"\n', id="py312"),
    pytest.param(STRICT + 'pythonVersion = "3.x"\n', id="x"),
    pytest.param(STRICT + 'pythonVersion = ""\n', id="empty"),
    pytest.param(STRICT + "pythonVersion = 312\n", id="int"),
]

CLEAN = "value = 1\n"

MARKED = "value = 1  # noqa\n"


def _caches(_directory: str, names: list[str]) -> set[str]:
    """The bytecode cache directories among `names`, left out of the copy."""
    return {name for name in names if name == "__pycache__"}


def _tree(tmp_path: Path, pyproject: str) -> Path:
    """A tree holding a copy of the `gates` package and the seeded `pyproject.toml`."""
    root = tmp_path / "tree"
    shutil.copytree(
        Path(check_suppressions.__file__).parent, root / "gates", ignore=_caches
    )
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    return root


def _run(tmp_path: Path, pyproject: str, source: str) -> tuple[int, list[str]]:
    """Run the gate in its own tree on one seeded file; return its exit status and every line it printed."""
    root = _tree(tmp_path, pyproject)
    seeded = root / "seeded.py"
    seeded.write_text(source, encoding="utf-8")
    run = subprocess.run(
        [sys.executable, "-u", "-B", "-m", f"gates.{GATE}", str(seeded)],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return run.returncode, run.stdout.splitlines()


@pytest.mark.parametrize("source", [CLEAN, MARKED], ids=["c", "m"])
@pytest.mark.parametrize("pyproject", UNPINNED)
def test_exit(tmp_path: Path, pyproject: str, source: str) -> None:
    """A tree with no `major.minor` pyright `pythonVersion` is one the checker could not finish, whatever the file holds."""
    status, _ = _run(tmp_path, pyproject, source)

    assert status == UNFINISHED


@pytest.mark.parametrize("pyproject", UNPINNED)
def test_key(tmp_path: Path, pyproject: str) -> None:
    """The unfinished run prints an error naming the key before its last line."""
    status, lines = _run(tmp_path, pyproject, CLEAN)

    assert (status, KEY in "\n".join(lines[:-1])) == (UNFINISHED, True)


@pytest.mark.parametrize("pyproject", UNPINNED)
def test_last(tmp_path: Path, pyproject: str) -> None:
    """The last line the unfinished run prints is its count line."""
    status, lines = _run(tmp_path, pyproject, CLEAN)

    assert (
        status,
        [COUNT_LINE_SHAPE.fullmatch(line) is not None for line in lines[-1:]],
    ) == (UNFINISHED, [True])
