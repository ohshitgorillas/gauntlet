"""Red tests for the mypy gate run over `tests/` only, as `make check-tests` runs it.

Source: the agents design spec under docs/superpowers/specs/, "Decisions", the `make check-tests` bullet: the target runs each gate of `check` over `tests/` only and prints only findings located under `tests/`, while the type checkers follow imports out of `tests/` as the quality gates spec requires. Applied to the mypy gate of the quality gates spec, "Types", first bullet.
"""

from pathlib import Path

import pytest

from gates.check_mypy import main

TEST_MARKER = "SeededToken"

LIBRARY_MARKER = "LibraryMarker"

LIBRARY_SOURCE = (
    f"class {TEST_MARKER}:\n    pass\n\n\n"
    f"class {LIBRARY_MARKER}:\n    pass\n\n\n"
    f"def accept(token: {TEST_MARKER}) -> None:\n    pass\n\n\n"
    f"broken: {LIBRARY_MARKER} = 1\n"
)

TEST_SOURCE = (
    "from seededlib.helper import accept\n\n\ndef check() -> None:\n    accept(1)\n"
)


def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_report_scope(tmp_path: Path, capfd: pytest.CaptureFixture[str]) -> None:
    """A tests/ file's finding that needs the imported module's types is printed; the imported module's own finding is not.

    The test file never names `SeededToken`: it reaches the report only through a finding mypy can make by analysing
    the imported module, where the type is defined. `LibraryMarker` reaches the report only through the imported
    module's own finding.
    """
    _seed(tmp_path, "seededlib/__init__.py", "")
    _seed(tmp_path, "seededlib/helper.py", LIBRARY_SOURCE)
    _seed(tmp_path, "tests/__init__.py", "")
    test_file = _seed(tmp_path, "tests/test_seeded.py", TEST_SOURCE)

    main([test_file])
    captured = capfd.readouterr()
    report = captured.out + captured.err

    assert {marker for marker in (TEST_MARKER, LIBRARY_MARKER) if marker in report} == {
        TEST_MARKER
    }
