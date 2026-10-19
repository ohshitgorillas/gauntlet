"""Red tests for the gate that bans `typing.cast`.

Source: the quality-gates design spec under docs/superpowers/specs/, "Gates", "Types", third bullet:
"`typing.cast` is banned (ruff `TID251`)."
"""

from pathlib import Path

from gates.check_cast import main


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_gate_fails_on_cast_imported_from_typing(tmp_path: Path) -> None:
    path = _seed(tmp_path, "seeded.py", "from typing import cast\n\nvalue = cast(int, 1)\n")

    assert main([path]) == 1


def test_gate_fails_on_cast_reached_through_typing_module(tmp_path: Path) -> None:
    path = _seed(tmp_path, "seeded.py", "import typing\n\nvalue = typing.cast(int, 1)\n")

    assert main([path]) == 1


def test_gate_fails_on_cast_imported_under_an_alias(tmp_path: Path) -> None:
    path = _seed(tmp_path, "seeded.py", "from typing import cast as convert\n\nvalue = convert(int, 1)\n")

    assert main([path]) == 1


def test_gate_passes_file_without_cast(tmp_path: Path) -> None:
    path = _seed(tmp_path, "clean.py", "from typing import Final\n\nVALUE: Final = 1\n")

    assert main([path]) == 0


def test_gate_passes_local_function_named_cast(tmp_path: Path) -> None:
    source = "def cast(value: int) -> int:\n    return value\n\n\nresult = cast(1)\n"
    path = _seed(tmp_path, "local.py", source)

    assert main([path]) == 0


def test_gate_passes_cast_named_only_inside_string_literal(tmp_path: Path) -> None:
    path = _seed(tmp_path, "literal.py", 'text = "typing.cast"\nother = "from typing import cast"\n')

    assert main([path]) == 0


def test_gate_fails_when_any_listed_file_uses_cast(tmp_path: Path) -> None:
    first = _seed(tmp_path, "first.py", "value = 1\n")
    dirty = _seed(tmp_path, "dirty.py", "import typing\n\nvalue = typing.cast(int, 1)\n")
    last = _seed(tmp_path, "last.py", "value = 1\n")

    assert main([first, dirty, last]) == 1
