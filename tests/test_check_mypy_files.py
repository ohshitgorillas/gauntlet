# Copyright 2026 oh shit, gorillas!
"""Red tests: the mypy gate applies to every Python file, stub files included.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph:
"Every gate applies to every Python file in the tree" and "A Python file is a file whose name
ends in `.py` or `.pyi`".
"""

from pathlib import Path

from gates.check_mypy import main

TYPED_STUB = "def ping() -> int: ...\n"

UNTYPED_STUB = "def ping(): ...\n"


def test_passes_typed_stub(tmp_path: Path) -> None:
    """A .pyi file is a Python file: the gate passes a fully annotated stub and fails an untyped one."""
    typed = tmp_path / "typed.pyi"
    typed.write_text(TYPED_STUB, encoding="utf-8")
    untyped = tmp_path / "untyped.pyi"
    untyped.write_text(UNTYPED_STUB, encoding="utf-8")

    assert main([typed]) == 0
    assert main([untyped]) == 1
