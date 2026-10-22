# Copyright 2026 oh shit, gorillas!
"""Red tests for the ban on `typing.cast` as `typing_extensions` exports it.

Source: the quality-gates design spec under docs/superpowers/specs/, "Gates", "Types", third bullet:
"`typing.cast` is banned (ruff `TID251`). The ban is on the function, not its spelling: it covers `typing.cast`
under every name it is imported by, `typing_extensions.cast` included, and the banned-api table lists each such
name." The same spec, "Gates", intro paragraph: a gate exits 0 with no finding and 1 with one or more findings.

The ban is on the function, so `typing_extensions.cast` is a finding however a file reaches it.
"""

from pathlib import Path

from gates.check_cast import main


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_gate_fails_on_cast_imported_from_typing_extensions(tmp_path: Path) -> None:
    """`typing_extensions.cast` is `typing.cast` under another name, so importing it is a finding."""
    source = "from typing_extensions import cast\n\nvalue = cast(int, 1)\n"
    path = _seed(tmp_path, "from_extensions.py", source)

    assert main([path]) == 1


def test_gate_fails_on_cast_reached_through_typing_extensions_module(
    tmp_path: Path,
) -> None:
    """A call spelled `typing_extensions.cast` reaches the banned function, so it is a finding."""
    source = "import typing_extensions\n\nvalue = typing_extensions.cast(int, 1)\n"
    path = _seed(tmp_path, "extensions_module.py", source)

    assert main([path]) == 1


def test_gate_fails_on_cast_through_aliased_typing_extensions_module(
    tmp_path: Path,
) -> None:
    """`typing_extensions` imported under another name still reaches its `cast`, so the call is a finding."""
    source = "import typing_extensions as te\n\nvalue = te.cast(int, 1)\n"
    path = _seed(tmp_path, "extensions_aliased.py", source)

    assert main([path]) == 1


def test_gate_fails_on_typing_extensions_cast_imported_under_an_alias(
    tmp_path: Path,
) -> None:
    """`typing_extensions.cast` bound to another local name is still the banned function, so it is a finding."""
    source = (
        "from typing_extensions import cast as convert\n\nvalue = convert(int, 1)\n"
    )
    path = _seed(tmp_path, "extensions_cast_alias.py", source)

    assert main([path]) == 1
