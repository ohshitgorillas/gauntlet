"""Red tests for how far the ban on `typing.cast` reaches.

Source: the quality-gates design spec under docs/superpowers/specs/, "Gates", "Types", third bullet:
"`typing.cast` is banned (ruff `TID251`)." The same spec, "Gates", intro paragraph: a gate exits 0 with no
finding and 1 with one or more findings.

The ban names the function `typing.cast`, so it holds however that function is reached and wherever in a
file it is called, and it does not hold for text that only spells the name or for another module's `cast`.
"""

from pathlib import Path

from gates.check_cast import main


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def test_gate_fails_on_cast_through_aliased_typing_module(tmp_path: Path) -> None:
    """`typing` imported under another name still reaches `typing.cast`, so its call is a finding."""
    path = _seed(tmp_path, "aliased.py", "import typing as t\n\nvalue = t.cast(int, 1)\n")

    assert main([path]) == 1


def test_gate_fails_on_cast_inside_method_body(tmp_path: Path) -> None:
    """The ban holds in every scope of a file, so a call inside a method is a finding."""
    source = "import typing\n\n\nclass Box:\n    def get(self) -> int:\n        return typing.cast(int, 1)\n"
    path = _seed(tmp_path, "method.py", source)

    assert main([path]) == 1


def test_gate_fails_on_cast_under_type_checking_guard(tmp_path: Path) -> None:
    """Code read only by type checkers is still code, so a call under `TYPE_CHECKING` is a finding."""
    source = "import typing\n\nif typing.TYPE_CHECKING:\n    VALUE = typing.cast(int, 1)\n"
    path = _seed(tmp_path, "guarded.py", source)

    assert main([path]) == 1


def test_gate_passes_cast_named_only_in_comment(tmp_path: Path) -> None:
    """A comment that spells the banned name calls nothing, so it is not a finding."""
    source = "# typing.cast is banned here\n# from typing import cast\nvalue = 1\n"
    path = _seed(tmp_path, "comment.py", source)

    assert main([path]) == 0


def test_gate_passes_cast_imported_from_another_module(tmp_path: Path) -> None:
    """Only `typing.cast` is banned, so a function named `cast` imported from elsewhere is not a finding."""
    path = _seed(tmp_path, "other.py", "from helpers import cast\n\nvalue = cast(1)\n")

    assert main([path]) == 0
