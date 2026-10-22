"""Red tests for the mypy gate's count line.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "The count line of a run whose checker finished reads `<gate>: N finding(s) in M Python file(s)`, where `<gate>` is the name of the gate script without its extension, and it is the last line the run prints." Applied to the mypy gate of "Types", first bullet, whose script is `gates/check_mypy.py`, so `<gate>` is `check_mypy`.

The documents name no stream, so stdout and stderr are captured into one buffer, in the order the run prints them. The same sentence says "`finding(s)` and `file(s)` are printed as written whatever N and M are", so only that spelling is read, never the plural that agrees with the count.
"""

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from gates.check_mypy import main

TWO_TYPE_ERRORS = 'count: int = "none"\nname: str = 0\n'

ONE_TYPE_ERROR = 'count: int = "none"\n'

WELL_TYPED = "def double(value: int) -> int:\n    return value * 2\n"

TYPED_STUB = "def ping() -> int: ...\n"

SHEBANG_SCRIPT = (
    "#!/usr/bin/env python3\ndef triple(value: int) -> int:\n    return value * 3\n"
)

FINDING_WORD = "finding(s)"

FILE_WORD = "file(s)"


def _seed(root: Path, name: str, source: str) -> Path:
    path = root / name
    path.write_text(source, encoding="utf-8")
    return path


def _last_line(paths: list[Path]) -> str:
    """The last line the run prints, stdout and stderr read together in print order."""
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        main(paths)
    lines = buffer.getvalue().splitlines()
    return lines[-1] if lines else ""


def _count(line: str) -> tuple[str, int, int] | None:
    """The gate name, N and M of a line shaped `<gate>: N finding(s) in M Python file(s)`, or None."""
    gate, separator, rest = line.partition(": ")
    words = rest.split(" ")
    shaped = separator == ": " and len(words) == 6
    if not shaped:
        return None
    findings, finding_word, in_word, files, python_word, file_word = words
    if not (findings.isdigit() and files.isdigit()):
        return None
    if finding_word != FINDING_WORD or file_word != FILE_WORD:
        return None
    if in_word != "in" or python_word != "Python":
        return None
    return (gate, int(findings), int(files))


def test_count_clean(tmp_path: Path) -> None:
    """A run over two well-typed files ends on the count line naming zero findings in two files."""
    files = [
        _seed(tmp_path, "first.py", WELL_TYPED),
        _seed(tmp_path, "second.py", WELL_TYPED),
    ]

    assert _count(_last_line(files)) == ("check_mypy", 0, 2)


def test_count_findings(tmp_path: Path) -> None:
    """A run whose one file holds two type errors ends on the count line naming two findings, not one file with findings."""
    files = [
        _seed(tmp_path, "broken.py", TWO_TYPE_ERRORS),
        _seed(tmp_path, "first.py", WELL_TYPED),
        _seed(tmp_path, "second.py", WELL_TYPED),
    ]

    assert _count(_last_line(files)) == ("check_mypy", 2, 3)


def test_count_across_files(tmp_path: Path) -> None:
    """Findings in several files are summed into the one count line that ends the run."""
    files = [
        _seed(tmp_path, "broken.py", TWO_TYPE_ERRORS),
        _seed(tmp_path, "cracked.py", ONE_TYPE_ERROR),
        _seed(tmp_path, "first.py", WELL_TYPED),
        _seed(tmp_path, "second.py", WELL_TYPED),
    ]

    assert _count(_last_line(files)) == ("check_mypy", 3, 4)


def test_count_stub_file(tmp_path: Path) -> None:
    """A .pyi file is a Python file, so it is counted in M."""
    files = [
        _seed(tmp_path, "first.py", WELL_TYPED),
        _seed(tmp_path, "second.py", WELL_TYPED),
        _seed(tmp_path, "typed.pyi", TYPED_STUB),
    ]

    assert _count(_last_line(files)) == ("check_mypy", 0, 3)


def test_count_shebang_file(tmp_path: Path) -> None:
    """An extensionless file whose shebang names python is a Python file, so it is counted in M."""
    files = [
        _seed(tmp_path, "first.py", WELL_TYPED),
        _seed(tmp_path, "second.py", WELL_TYPED),
        _seed(tmp_path, "tool", SHEBANG_SCRIPT),
    ]

    assert _count(_last_line(files)) == ("check_mypy", 0, 3)
