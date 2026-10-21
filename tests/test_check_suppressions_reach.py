"""Tests for the reach of the suppression gate: which files it counts as Python files, and that it covers every one of them in the tree.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", first paragraph: every gate applies to every Python file in the tree, `gauntlet/`, `tests/`, gate scripts and any hook or tool script, and no path is excluded. A Python file is a file whose name ends in `.py` or `.pyi`, or an extensionless file whose first line is a shebang that names python; a `.pyw` file is not one. Applied to the gate of "Suppression gate", whose first bullet names the `noqa` comment.
"""

from pathlib import Path

import pytest

from gates.check_suppressions import main
from gates.core.project import is_python_file

PYTHON_SHEBANG = "#!/usr/bin/env python3\n"

CLEAN_BODY = "value = 1\n"

MARKED_BODY = "value = 1  # noqa\n"

PYTHON_SOURCES = [
    pytest.param("module.py", CLEAN_BODY, id="py-suffix"),
    pytest.param("module.py", "#!/bin/sh\n" + CLEAN_BODY, id="py-suffix-with-shell-shebang"),
    pytest.param("script", PYTHON_SHEBANG + CLEAN_BODY, id="extensionless-env-python3"),
    pytest.param("script", "#!/usr/bin/python\n" + CLEAN_BODY, id="extensionless-python"),
    pytest.param("script", "#!/usr/bin/python3.12\n" + CLEAN_BODY, id="extensionless-python3.12"),
]

NOT_PYTHON_SOURCES = [
    pytest.param("module.py.bak", CLEAN_BODY, id="py-then-other-suffix"),
    pytest.param("script", "#!/bin/sh\necho one\n", id="extensionless-sh"),
    pytest.param("script", "#!/usr/bin/env bash\necho one\n", id="extensionless-env-bash"),
    pytest.param("script", "import os\n", id="extensionless-no-shebang"),
    pytest.param("script", "# python helper\nimport os\n", id="extensionless-python-comment-not-shebang"),
    pytest.param("script", "\n" + PYTHON_SHEBANG + "import os\n", id="extensionless-shebang-on-second-line"),
    pytest.param("script", "", id="extensionless-empty"),
]

TREE_FILES = [
    "gauntlet/core/decide.py",
    "gauntlet/seams/runner.py",
    "tests/test_decide.py",
    "gates/check_sample.py",
    ".claude/hooks/guard.py",
    "tools/sweep",
]

LOCATIONS = [
    pytest.param("gauntlet/core/decide.py", id="core"),
    pytest.param("gauntlet/seams/runner.py", id="seams"),
    pytest.param("tests/test_decide.py", id="tests"),
    pytest.param("gates/check_sample.py", id="gates"),
    pytest.param(".claude/hooks/guard.py", id="hook"),
    pytest.param("tools/sweep", id="extensionless-tool"),
]


def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _tree_source(relative: str, body: str) -> str:
    return body if relative.endswith(".py") else PYTHON_SHEBANG + body


def _seed_tree(root: Path, marked: str) -> list[Path]:
    return [_seed(root, relative, _tree_source(relative, MARKED_BODY if relative == marked else CLEAN_BODY)) for relative in TREE_FILES]


def _gate_with_marked(root: Path, name: str, source: str) -> int:
    clean = _seed(root, "clean.py", CLEAN_BODY)
    marked = _seed(root, name, source)
    return main([clean, marked])


@pytest.mark.parametrize(("name", "source"), PYTHON_SOURCES)
def test_python_source(tmp_path: Path, name: str, source: str) -> None:
    """A `.py` file, or an extensionless file whose first line is a shebang naming python, is a Python file."""
    path = _seed(tmp_path, name, source)

    assert is_python_file(path) is True


@pytest.mark.parametrize(("name", "source"), NOT_PYTHON_SOURCES)
def test_not_python_source(tmp_path: Path, name: str, source: str) -> None:
    """A file with another suffix, or an extensionless file without a python shebang on its first line, is not a Python file."""
    path = _seed(tmp_path, name, source)

    assert is_python_file(path) is False


def test_pyw(tmp_path: Path) -> None:
    """A `.pyw` file is not a Python file."""
    path = _seed(tmp_path, "window.pyw", CLEAN_BODY)

    assert is_python_file(path) is False


def test_pyw_python(tmp_path: Path) -> None:
    """A `.pyw` file is not a Python file even when its first line is a shebang that names python."""
    path = _seed(tmp_path, "window.pyw", PYTHON_SHEBANG + CLEAN_BODY)

    assert is_python_file(path) is False


def test_sh_python(tmp_path: Path) -> None:
    """A python shebang makes only an extensionless file a Python file, not one with another suffix."""
    path = _seed(tmp_path, "tool.sh", PYTHON_SHEBANG + CLEAN_BODY)

    assert is_python_file(path) is False


def test_gate_pyw(tmp_path: Path) -> None:
    """The gate does not apply to a `.pyw` file, so a marker in one does not fail it."""
    assert _gate_with_marked(tmp_path, "window.pyw", MARKED_BODY) == 0


def test_gate_pyw_py(tmp_path: Path) -> None:
    """The gate does not apply to a `.pyw` file whose first line names python, so a marker in it does not fail it."""
    assert _gate_with_marked(tmp_path, "window.pyw", PYTHON_SHEBANG + MARKED_BODY) == 0


def test_gate_sh_py(tmp_path: Path) -> None:
    """The gate does not apply to a suffixed non-`.py` file with a python shebang, so a marker in it does not fail it."""
    assert _gate_with_marked(tmp_path, "tool.sh", PYTHON_SHEBANG + MARKED_BODY) == 0


def test_gate_sh(tmp_path: Path) -> None:
    """The gate does not apply to an extensionless shell script, so a marker in it does not fail it."""
    assert _gate_with_marked(tmp_path, "script", "#!/bin/sh\necho one  # noqa\n") == 0


@pytest.mark.parametrize("relative", LOCATIONS)
def test_tree_verdict(tmp_path: Path, relative: str) -> None:
    """A suppression comment in any one Python file of the tree fails the gate run over the tree's files."""
    marked = _seed_tree(tmp_path, relative)

    assert main(marked) != 0


def test_clean_tree(tmp_path: Path) -> None:
    """A tree whose every Python file is free of suppressions passes the gate."""
    files = _seed_tree(tmp_path, "")

    assert main(files) == 0
