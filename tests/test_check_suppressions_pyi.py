# Copyright 2026 oh shit, gorillas!
"""Red tests: a stub file is a Python file, so every gate applies to it.

Source: the quality-gates design spec under docs/superpowers/specs/, "Gates", intro paragraph:
"A Python file is a file whose name ends in `.py` or `.pyi`, ..."
"Suppression gate", first bullet: "a `noqa` ... comment, found by tokenizing".
"Gates", intro paragraph: "A gate exits 0 with no finding, 1 with one or more findings,
and 2 when its checker could not finish".
"""

from pathlib import Path

from gates.check_suppressions import main


def test_pyi_file_is_python_source(tmp_path: Path) -> None:
    """Verify pyi file is python source."""
    path = tmp_path / "module.pyi"
    path.write_text("def value() -> int: ...  # noqa\n", encoding="utf-8")

    assert main([path]) == 1
