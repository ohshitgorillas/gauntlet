"""Red tests: the mypy gate on a Python file its checker cannot read or cannot parse.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "A Python file the checker cannot read or cannot parse is a file the checker did not finish: the gate prints what the checker reported for that file and exits 2, whatever it found in the other files." Applied to the mypy gate of "Types", first bullet.

The documents name no stream, so stdout and stderr are read together. The documents do not spell the checker's report, so a report is read only for the seeded file name and, where the file was parsed, the seeded line of its syntax error as the first number printed after that name on the same line, in whatever form the gate prints them. Where the file could not be read, the report is the line mypy itself prints naming that file when run on it alone, and the gate's output must hold that line.
"""

import subprocess
import sys
from pathlib import Path

import pytest

from gates.check_mypy import main

SYNTAX_ERROR = "count: int = 1\n\ndef broken(:\n"

SYNTAX_NAME = "broken.py"

SYNTAX_LINE = 3

STUB_SYNTAX_ERROR = "def ping() -> int: ...\n\ndef broken(: ...\n"

STUB_NAME = "typed_stub.pyi"

STUB_LINE = 3

SHEBANG_SYNTAX_ERROR = "#!/usr/bin/env python3\ncount: int = 1\n\ndef broken(:\n"

SHEBANG_NAME = "tool"

SHEBANG_LINE = 4

NULL_BYTE = "count: int = 1\x00\n"

UNDECODABLE = b"name = '\xff'\n"

UNREADABLE_NAME = "locked.py"

TYPE_ERROR = 'count: int = "none"\n'

WELL_TYPED = "def double(value: int) -> int:\n    return value * 2\n"


def _seed(root: Path, name: str, source: str) -> Path:
    path = root / name
    path.write_text(source, encoding="utf-8")
    return path


def _locked(root: Path) -> Path:
    """A well-typed file no one may read."""
    path = _seed(root, UNREADABLE_NAME, WELL_TYPED)
    path.chmod(0)
    return path


def _printed(capsys: pytest.CaptureFixture[str]) -> str:
    captured = capsys.readouterr()
    return captured.out + captured.err


def _first_number(text: str) -> int | None:
    """The first run of decimal digits in `text`, read as a number, or None where `text` holds no digit."""
    digits = ""
    for character in text:
        if character in "0123456789":
            digits += character
        elif digits:
            break
    return int(digits) if digits else None


def _places(name: str, printed: str) -> set[int | None]:
    """For each printed line that names `name`, the first number printed after that name."""
    return {_first_number(line.partition(name)[2]) for line in printed.splitlines() if name in line}


def test_syntax_alone(tmp_path: Path) -> None:
    """A file the checker cannot parse is a checker that did not finish, not a finding."""
    files = [_seed(tmp_path, SYNTAX_NAME, SYNTAX_ERROR)]

    assert main(files) == 2


def test_syntax_beside_finding(tmp_path: Path) -> None:
    """A finding in another file does not turn an unparsed file into a run that finished."""
    files = [_seed(tmp_path, SYNTAX_NAME, SYNTAX_ERROR), _seed(tmp_path, "typed.py", TYPE_ERROR)]

    assert main(files) == 2


def test_syntax_before_clean(tmp_path: Path) -> None:
    """A clean file checked after an unparsed one does not clear the unfinished verdict."""
    files = [_seed(tmp_path, SYNTAX_NAME, SYNTAX_ERROR), _seed(tmp_path, "clean.py", WELL_TYPED)]

    assert main(files) == 2


def test_syntax_after_finding(tmp_path: Path) -> None:
    """An unparsed file checked after a file with a finding still makes the run unfinished."""
    files = [_seed(tmp_path, "typed.py", TYPE_ERROR), _seed(tmp_path, SYNTAX_NAME, SYNTAX_ERROR)]

    assert main(files) == 2


def test_syntax_stub(tmp_path: Path) -> None:
    """A .pyi file is a Python file, so one the checker cannot parse leaves it unfinished."""
    files = [_seed(tmp_path, "typed.py", TYPE_ERROR), _seed(tmp_path, STUB_NAME, STUB_SYNTAX_ERROR)]

    assert main(files) == 2


def test_syntax_stub_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The checker's report on an unparsed .pyi file places the syntax error on its seeded line."""
    main([_seed(tmp_path, "typed.py", TYPE_ERROR), _seed(tmp_path, STUB_NAME, STUB_SYNTAX_ERROR)])

    assert STUB_LINE in _places(STUB_NAME, _printed(capsys))


def test_syntax_shebang(tmp_path: Path) -> None:
    """An extensionless file whose shebang names python is a Python file, so one the checker cannot parse leaves it unfinished."""
    files = [_seed(tmp_path, "typed.py", TYPE_ERROR), _seed(tmp_path, SHEBANG_NAME, SHEBANG_SYNTAX_ERROR)]

    assert main(files) == 2


def test_syntax_shebang_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The checker's report on an unparsed shebang file places the syntax error on its seeded line."""
    main([_seed(tmp_path, "typed.py", TYPE_ERROR), _seed(tmp_path, SHEBANG_NAME, SHEBANG_SYNTAX_ERROR)])

    assert SHEBANG_LINE in _places(SHEBANG_NAME, _printed(capsys))


def test_null_byte(tmp_path: Path) -> None:
    """A file holding a null byte is source the checker cannot parse."""
    files = [_seed(tmp_path, "typed.py", TYPE_ERROR), _seed(tmp_path, "nulled.py", NULL_BYTE)]

    assert main(files) == 2


def test_unreadable_alone(tmp_path: Path) -> None:
    """A file the checker cannot read is a checker that did not finish."""
    files = [_locked(tmp_path)]

    assert main(files) == 2


def test_unreadable_beside_finding(tmp_path: Path) -> None:
    """A finding in another file does not turn an unread file into a run that finished."""
    files = [_seed(tmp_path, "typed.py", TYPE_ERROR), _locked(tmp_path)]

    assert main(files) == 2


def test_undecodable(tmp_path: Path) -> None:
    """A file whose bytes are not text the checker can decode is a file it cannot read or parse."""
    path = tmp_path / "garbled.py"
    path.write_bytes(UNDECODABLE)

    assert main([path]) == 2


def test_syntax_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The gate prints the checker's report on the unparsed file, which places the syntax error on its seeded line."""
    main([_seed(tmp_path, SYNTAX_NAME, SYNTAX_ERROR)])

    assert SYNTAX_LINE in _places(SYNTAX_NAME, _printed(capsys))


def test_syntax_report_beside_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The checker's report on the unparsed file is printed even when another file holds a finding."""
    main([_seed(tmp_path, "typed.py", TYPE_ERROR), _seed(tmp_path, SYNTAX_NAME, SYNTAX_ERROR)])

    assert SYNTAX_LINE in _places(SYNTAX_NAME, _printed(capsys))


def _checker_line(path: Path) -> str:
    """The first line mypy itself prints naming `path` when run on that file alone."""
    run = subprocess.run([sys.executable, "-m", "mypy", str(path)], capture_output=True, text=True, check=False)
    return next(line for line in (run.stdout + run.stderr).splitlines() if path.name in line)


def test_unreadable_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The gate prints the checker's own report on the unread file, the line mypy prints naming that file."""
    locked = _locked(tmp_path)
    reported = _checker_line(locked)
    main([_seed(tmp_path, "clean.py", WELL_TYPED), locked])

    assert reported in _printed(capsys)
