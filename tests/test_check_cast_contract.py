# Copyright 2026 oh shit, gorillas!
"""Red tests for the cast gate's contract as a gate.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates",
intro paragraph: a gate whose checker is an external tool runs that tool over the
tree's Python files with the settings in `pyproject.toml`, which holds those
settings and nothing else does; it prints each finding on its own line and prints
its count line on every run. A Python file is a file whose name ends in `.py` or
`.pyi`, or an extensionless file whose first line is a shebang that names python.
The banned name comes from "Types", third bullet: "`typing.cast` is banned".

The documents name no stream, so stdout and stderr are read together. One file
holding one use of `typing.cast` is one finding, and one file holding two uses is
two findings.
"""

import string
from pathlib import Path

import pytest

from gates.check_cast import main

DIRTY = "import typing\n\nvalue = typing.cast(int, 1)\n"

TWICE_DIRTY = (
    "import typing\n\nvalue = typing.cast(int, 1)\nother = typing.cast(int, 2)\n"
)

CLEAN = "VALUE = 1\n"

SHEBANG_DIRTY = "#!/usr/bin/env python3\nimport typing\n\nvalue = typing.cast(int, 1)\n"

LOOSER_SETTINGS = '[tool.ruff.lint]\nselect = ["E"]\n'


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _lines(paths: list[Path], capsys: pytest.CaptureFixture[str]) -> list[str]:
    main(paths)
    captured = capsys.readouterr()
    return (captured.out + captured.err).splitlines()


def _names_cast_in(name: str, lines: list[str]) -> bool:
    """Tell whether one line carries the file's name, ruff's rule code `TID251` and the banned name `typing.cast` from ruff's message.

    The rule code comes from "Types", third bullet; a line that drops it has cut the checker's message down.
    """
    return any(
        name in line and "TID251" in line and "typing.cast" in line for line in lines
    )


def _count_cast_lines(name: str, lines: list[str]) -> int:
    """Count the lines that each carry the file's name, ruff's rule code `TID251` and the banned name `typing.cast`."""
    return sum(
        1
        for line in lines
        if name in line and "TID251" in line and "typing.cast" in line
    )


PUNCTUATION_TO_SPACE = str.maketrans(string.punctuation, " " * len(string.punctuation))


def _lines_stating(
    count: int,
    paths: list[Path],
    root: Path,
    capsys: pytest.CaptureFixture[str],
    finding_names: tuple[str, ...] = (),
) -> list[bool]:
    """Run the gate and tell, line by line, whether the line states `count` as a word of its own.

    The seeded directory is cut out of the output first, so digits in the temporary path are not read as a count.
    A line naming any of `finding_names` is a finding line, not the count line, and is skipped: the documents do not
    say how a finding line spells its path or what else it holds, so a digit in it is not read as a count.
    """
    main(paths)
    captured = capsys.readouterr()
    text = (captured.out + captured.err).replace(str(root), "")
    return [
        str(count) in line.translate(PUNCTUATION_TO_SPACE).split()
        for line in text.splitlines()
        if not any(name in line for name in finding_names)
    ]


def test_count_line_states_the_number_of_findings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With no finding, a line, the count line, states 0; with one finding, a line states 1; with two findings, a line states 2.

    The documents ask for a count line and do not forbid other output beside the findings and the count line, so each run
    is held to at least one line stating its count, not to exactly one such line, nor to one line in all.
    The two-finding run tells a count of findings from a flag: a gate whose only number is the exit status states no 2 there.
    Its two findings sit in one file, so it also tells a count of findings from a count of files with a finding: a gate
    that counts dirty files states 1 there, not 2.
    """
    clean = _seed(tmp_path, "clean.py", CLEAN)
    dirty = _seed(tmp_path, "dirty.py", DIRTY)
    twice = _seed(tmp_path, "twice.py", TWICE_DIRTY)
    clean_run = _lines_stating(0, [clean], tmp_path, capsys)
    one_finding_run = _lines_stating(
        1, [clean, dirty], tmp_path, capsys, finding_names=("dirty.py",)
    )
    two_finding_run = _lines_stating(
        2, [clean, twice], tmp_path, capsys, finding_names=("twice.py",)
    )

    assert (
        clean_run.count(True) >= 1,
        one_finding_run.count(True) >= 1,
        two_finding_run.count(True) >= 1,
    ) == (True, True, True)


def test_one_finding_adds_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A finding is printed on its own line and carries the checker's whole message, so one finding adds exactly one line carrying it: one line names the file, the rule code `TID251` and `typing.cast`.

    The documents do not forbid output that appears only when findings exist, such as a header line, so the run is not
    held to one line more in all than a run with no finding; only the lines carrying the finding are counted. A finding
    split across lines leaves no line carrying all three, and a finding printed twice leaves two.
    """
    clean = _seed(tmp_path, "clean.py", CLEAN)
    dirty = _seed(tmp_path, "dirty.py", DIRTY)
    with_one = _lines([clean, dirty], capsys)

    assert (
        _count_cast_lines("dirty.py", with_one),
        _names_cast_in("dirty.py", with_one),
    ) == (1, True)


def test_second_finding_adds_one_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Each finding gets its own line and carries the checker's whole message, so a second finding adds exactly one more finding line, and a line names the second file, the rule code `TID251` and `typing.cast`.

    The documents do not forbid other output beside the findings and the count line, such as a line per checked file or
    a blank line after each finding, so the run is not held to one line more in all; only the lines carrying a finding,
    each naming its file, `TID251` and `typing.cast`, are counted in both runs.
    """
    first = _seed(tmp_path, "first.py", DIRTY)
    second = _seed(tmp_path, "second.py", DIRTY)
    with_one = _lines([first], capsys)
    with_two = _lines([first, second], capsys)
    finding_lines_one = _count_cast_lines("first.py", with_one) + _count_cast_lines(
        "second.py", with_one
    )
    finding_lines_two = _count_cast_lines("first.py", with_two) + _count_cast_lines(
        "second.py", with_two
    )

    assert (
        finding_lines_two - finding_lines_one,
        _names_cast_in("second.py", with_two),
    ) == (1, True)


def test_settings_beside_checked_file_do_not_apply(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Only the tree's pyproject.toml holds the settings, so a nearer one that drops the ban changes nothing.

    The exit status 1 alone cannot tell the checker's finding from a gate that ran the checker under the nearer settings
    and flagged the cast some other way, so a line must also name the file, the rule code `TID251` and `typing.cast`:
    the checker's own finding, which the nearer settings, selecting only `E`, would not produce.
    """
    _seed(tmp_path, "pyproject.toml", LOOSER_SETTINGS)
    dirty = _seed(tmp_path, "dirty.py", DIRTY)
    status = main([dirty])
    captured = capsys.readouterr()
    lines = (captured.out + captured.err).splitlines()

    assert (status, _names_cast_in("dirty.py", lines)) == (1, True)


def test_stub_file_is_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `.pyi` file is a Python file, so a cast in it is a finding.

    The exit status 1 alone cannot tell a finding from a checker that refused the `.pyi` file, so a line must also
    name the file, the rule code `TID251` and `typing.cast`: the finding itself, printed on its own line.
    """
    stub = _seed(tmp_path, "dirty.pyi", DIRTY)
    status = main([stub])
    captured = capsys.readouterr()
    lines = (captured.out + captured.err).splitlines()

    assert (status, _names_cast_in("dirty.pyi", lines)) == (1, True)


def test_python_shebang_file_is_checked(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An extensionless file with a python shebang is a Python file, so a cast in it is a finding.

    The exit status 1 alone cannot tell a finding from a checker that refused the extensionless file, so a line must also
    name the file, the rule code `TID251` and `typing.cast`: the finding itself, printed on its own line.
    """
    script = _seed(tmp_path, "dirty_script", SHEBANG_DIRTY)
    status = main([script])
    captured = capsys.readouterr()
    lines = (captured.out + captured.err).splitlines()

    assert (status, _names_cast_in("dirty_script", lines)) == (1, True)
