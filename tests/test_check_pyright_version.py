"""Red tests for the Python version the pyright gate checks against.

Source: the quality gates design spec under docs/superpowers/specs/, "Types",
the last sentence of the first bullet: `python_version = "3.12"`,
`requires-python = ">=3.12"`, ruff `target-version = "py312"`. Applied to the
pyright gate of "Types", second bullet.

A gate that checks against Python 3.12 rejects what only a later Python
offers. Each seeded source is clean under pyright's strict mode on Python 3.13
or later and uses one name or one piece of syntax that 3.12 lacks.
"""

from pathlib import Path

import pytest

from gates.check_pyright import main

WARNINGS_DEPRECATED = 'from warnings import deprecated\n\n\n@deprecated("use another")\ndef old() -> None:\n    pass\n'

TYPING_TYPEIS = "from typing import TypeIs\n\n\ndef is_int(value: object) -> TypeIs[int]:\n    return isinstance(value, int)\n"

TYPE_PARAMETER_DEFAULT = "def first[T = int](items: list[T]) -> T:\n    return items[0]\n"


def _seed(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "seeded.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "source",
    [
        pytest.param(WARNINGS_DEPRECATED, id="warnings-deprecated"),
        pytest.param(TYPING_TYPEIS, id="typeis"),
        pytest.param(TYPE_PARAMETER_DEFAULT, id="param-default"),
    ],
)
def test_rejects_newer_than_312(tmp_path: Path, source: str) -> None:
    """A file using a name or syntax Python 3.12 lacks fails the gate."""
    path = _seed(tmp_path, source)

    assert main([path]) != 0
