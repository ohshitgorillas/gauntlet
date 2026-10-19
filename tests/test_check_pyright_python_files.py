"""Red test: the pyright gate checks a stub file, because a stub file is a Python file.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph:
"Every gate applies to every Python file in the tree ... A Python file is a file whose name
ends in `.py` or `.pyi`". The pyright gate is "Types", second bullet.

The tests seed an undefined name that pyright reports in its message. The gate fails on that
finding, as it fails on any finding in a `.py` file, and the name reaching the gate's output
shows the finding carries pyright's message ("Gate code", third bullet). The documents name no
stream, so stdout and stderr are read together.
"""

from pathlib import Path

import pytest

from gates.check_pyright import main

STUB_MISSING = "gamma_missing_axolotl"

STUB_SOURCE = f"def value() -> {STUB_MISSING}: ...\n"


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _output(capfd: pytest.CaptureFixture[str]) -> str:
    captured = capfd.readouterr()
    return captured.out + captured.err


def test_rejects_stub_file(tmp_path: Path) -> None:
    """A `.pyi` file is a Python file, so pyright's finding in it fails the gate with exit 1."""
    path = _seed(tmp_path, "seeded.pyi", STUB_SOURCE)

    assert main([path]) == 1


def test_checks_stub_file(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    """A `.pyi` file is a Python file, so pyright's finding in it reaches the gate's output."""
    path = _seed(tmp_path, "seeded.pyi", STUB_SOURCE)
    main([path])

    assert STUB_MISSING in _output(capfd)
