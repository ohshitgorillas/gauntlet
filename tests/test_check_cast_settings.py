"""Red tests for where the cast gate takes its checker's settings from.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "a gate whose checker
is an external tool runs that tool over the tree's Python files with the settings in `pyproject.toml`, which holds
those settings and nothing else does, and returns the checker's findings." The checker comes from "Types", third
bullet: "`typing.cast` is banned (ruff `TID251`)." "Principles", fourth: "No suppressions. No inline suppression
comment". A gate exits 0 with no finding and 1 with one or more findings; "it prints each finding on its own line".
"Gate code", third bullet: "a finding carries the checker's whole message".

The settings are the tree's `pyproject.toml` and nothing else, so a comment in a checked file that would switch the
ban off for a line or for the whole file is not a setting, and the checker's finding is still returned: the run exits 1
and a line of its output carries the file's name, ruff's rule code `TID251` and the banned name `typing.cast`. An exit
of 1 alone is not enough, since a gate that dropped ruff's finding could still exit 1 on a finding of its own.

The documents name no stream, so stdout and stderr are read together.
"""

from pathlib import Path

import pytest

from gates.check_cast import main

LINE_NOQA_WITH_CODE = "import typing\n\nvalue = typing.cast(int, 1)  # noqa: TID251\n"

LINE_NOQA_BARE = "import typing\n\nvalue = typing.cast(int, 1)  # noqa\n"

FILE_NOQA_WITH_CODE = "# ruff: noqa: TID251\nimport typing\n\nvalue = typing.cast(int, 1)\n"

FILE_NOQA_BARE = "# ruff: noqa\nimport typing\n\nvalue = typing.cast(int, 1)\n"

FILE_FLAKE8_NOQA = "# flake8: noqa\nimport typing\n\nvalue = typing.cast(int, 1)\n"


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _run(path: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, bool]:
    """Run the gate on one file and return its exit status and whether a line carries the cast finding.

    The finding line is one that names the file, ruff's rule code `TID251` from "Types", third bullet, and the banned
    name `typing.cast` from ruff's message.
    """
    status = main([path])
    captured = capsys.readouterr()
    lines = (captured.out + captured.err).splitlines()
    return status, any(path.name in line and "TID251" in line and "typing.cast" in line for line in lines)


def test_line_noqa_naming_the_rule_does_not_drop_the_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A `# noqa: TID251` on the call's line is not `pyproject.toml`, so the cast is still a finding."""
    path = _seed(tmp_path, "line_code.py", LINE_NOQA_WITH_CODE)

    assert _run(path, capsys) == (1, True)


def test_bare_line_noqa_does_not_drop_the_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A bare `# noqa` on the call's line is not `pyproject.toml`, so the cast is still a finding."""
    path = _seed(tmp_path, "line_bare.py", LINE_NOQA_BARE)

    assert _run(path, capsys) == (1, True)


def test_file_noqa_naming_the_rule_does_not_drop_the_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A file-level `# ruff: noqa: TID251` is not `pyproject.toml`, so the cast is still a finding."""
    path = _seed(tmp_path, "file_code.py", FILE_NOQA_WITH_CODE)

    assert _run(path, capsys) == (1, True)


def test_bare_file_noqa_does_not_drop_the_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A file-level `# ruff: noqa` is not `pyproject.toml`, so the cast is still a finding."""
    path = _seed(tmp_path, "file_bare.py", FILE_NOQA_BARE)

    assert _run(path, capsys) == (1, True)


def test_flake8_file_noqa_does_not_drop_the_finding(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """A file-level `# flake8: noqa` is not `pyproject.toml`, so the cast is still a finding."""
    path = _seed(tmp_path, "file_flake8.py", FILE_FLAKE8_NOQA)

    assert _run(path, capsys) == (1, True)
