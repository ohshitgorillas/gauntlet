"""Red tests for the pyright gate on a tree that pins no Python, or pins it in the wrong form.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph:
"A gate that parses a Python file parses it with the grammar of the pinned Python, which is
pyright's `pythonVersion` in `pyproject.toml`, and a `pyproject.toml` that sets no
`pythonVersion`, or one that is not a `major.minor` version, is one the checker could not finish:
the gate prints an error that names the key, then its count line as the last line it prints, and
exits 2". The same paragraph: the gate "prints its count line on every run", and "The count line
of a run whose checker finished reads `<gate>: N finding(s) in M Python file(s)`, where `<gate>`
is the name of the gate script without its extension". The pyright gate is "Types", second bullet.

The gate takes its settings from the tree's `pyproject.toml`, so each test builds a tree of its
own: a copy of the `gates` package beside a seeded `pyproject.toml` and one seeded Python file, and
runs the gate script there as a module with that tree as its working directory, in a fresh
interpreter. The documents name no stream, so stdout and stderr go to one unbuffered pipe, which
keeps the order the run printed its lines in. The count line of an unfinished run is spelled
nowhere but in the count line's own shape, so the last line is held to that shape with any N and M.

Every seeded file is one the gate would otherwise pass (exit 0) or fail with one finding (exit 1),
so only a gate that lets the missing or malformed pin decide its verdict exits 2. Test names and
ids are kept short so that pytest's one-line summary has room to name the exception a test fails
with.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from gates import check_pyright

GATE = "check_pyright"

KEY = "pythonVersion"

UNFINISHED = 2

COUNT_LINE_SHAPE = re.compile(rf"{GATE}: \d+ finding\(s\) in \d+ Python file\(s\)")

STRICT = '[tool.pyright]\ntypeCheckingMode = "strict"\n'

UNPINNED = [
    pytest.param(STRICT, id="nokey"),
    pytest.param('[project]\nname = "seeded"\nrequires-python = ">=3.12"\n', id="table"),
    pytest.param("", id="blank"),
    pytest.param(STRICT + '\n[tool.mypy]\npython_version = "3.12"\n\n[tool.ruff]\ntarget-version = "py312"\n', id="other"),
    pytest.param(STRICT + 'pythonversion = "3.12"\n', id="case"),
    pytest.param(STRICT + 'pythonVersion = "3"\n', id="major"),
    pytest.param(STRICT + 'pythonVersion = "3.12.1"\n', id="micro"),
    pytest.param(STRICT + 'pythonVersion = "py312"\n', id="py312"),
    pytest.param(STRICT + 'pythonVersion = ""\n', id="empty"),
    pytest.param(STRICT + 'pythonVersion = "3."\n', id="nominor"),
    pytest.param(STRICT + 'pythonVersion = ".12"\n', id="nomajor"),
    pytest.param(STRICT + 'pythonVersion = "three.twelve"\n', id="words"),
    pytest.param(STRICT + 'pythonVersion = "3.12rc1"\n', id="rc"),
    pytest.param(STRICT + "pythonVersion = 312\n", id="int"),
]

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

ONE_FINDING = 'first_value: int = "alpha"\n'


def _caches(_directory: str, names: list[str]) -> set[str]:
    """The bytecode cache directories among `names`, left out of the copy."""
    return {name for name in names if name == "__pycache__"}


def _tree(tmp_path: Path, pyproject: str) -> Path:
    """A tree holding a copy of the `gates` package and the seeded `pyproject.toml`."""
    root = tmp_path / "tree"
    shutil.copytree(Path(check_pyright.__file__).parent, root / "gates", ignore=_caches)
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


@pytest.mark.parametrize("source", [CLEAN, ONE_FINDING], ids=["c", "f"])
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

    assert (status, [COUNT_LINE_SHAPE.fullmatch(line) is not None for line in lines[-1:]]) == (UNFINISHED, [True])
