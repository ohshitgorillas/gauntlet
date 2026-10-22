"""Red tests for the scope of the pyright gate's report under `make check-tests`.

Source: the agents design spec under docs/superpowers/specs/, "Decisions", the
`make check-tests` bullet, applied to the pyright gate of the quality gates
design spec, "Types", second bullet.

The type checker follows imports out of the files it is given, and the report
keeps to the given files: a finding in a followed import is not printed, and a
finding in a given file is.

Each seeded file carries one finding strict mode raises, a parameter with no
type annotation, on a parameter whose seeded name appears in no other file, so
the name shows in the output only where that file's finding is printed.
"""

from pathlib import Path

import pytest

from gates.check_pyright import main

DEPENDENCY_MARKER = "dependency_marker"

FIRST_MARKER = "first_marker"

SECOND_MARKER = "second_marker"

DEPENDENCY = f"LIMIT = 2\n\n\ndef echo({DEPENDENCY_MARKER}) -> int:\n    return {DEPENDENCY_MARKER}\n"

FIRST = f"import dependency\n\n\ndef double({FIRST_MARKER}) -> int:\n    return dependency.LIMIT * {FIRST_MARKER}\n"

SECOND = f"import dependency\n\n\ndef triple({SECOND_MARKER}) -> int:\n    return dependency.LIMIT * {SECOND_MARKER} + {SECOND_MARKER}\n"


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _printed(capfd: pytest.CaptureFixture[str]) -> str:
    captured = capfd.readouterr()
    return captured.out + captured.err


def test_report_names_the_given_file_and_not_its_import(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """A finding in the given file is printed; a finding in a module it imports is not."""
    _seed(tmp_path, "dependency.py", DEPENDENCY)
    first = _seed(tmp_path, "first.py", FIRST)

    main([first])
    printed = _printed(capfd)

    assert {
        marker for marker in (DEPENDENCY_MARKER, FIRST_MARKER) if marker in printed
    } == {FIRST_MARKER}


def test_report_names_every_given_file_and_not_their_import(
    tmp_path: Path, capfd: pytest.CaptureFixture[str]
) -> None:
    """Findings in each of several given files are printed; the shared import's are not."""
    _seed(tmp_path, "dependency.py", DEPENDENCY)
    first = _seed(tmp_path, "first.py", FIRST)
    second = _seed(tmp_path, "second.py", SECOND)

    main([first, second])
    printed = _printed(capfd)

    assert {
        marker
        for marker in (DEPENDENCY_MARKER, FIRST_MARKER, SECOND_MARKER)
        if marker in printed
    } == {FIRST_MARKER, SECOND_MARKER}
