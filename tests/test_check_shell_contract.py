# Copyright 2026 oh shit, gorillas!
"""Red tests for the shell-parsing gate's findings, scope and run contract.

Source: docs/superpowers/specs/m1-core-records-design.md, "`gates/check_shell.py`": "Every input Python file is
counted and parsed through the shared grammar home; findings apply to gauntlet/ code." and "One finding names the
source anchor and prohibited construct." Its second paragraph asks for tests of "malformed source and the shared
empty-run/exit contract". docs/design.md §1, "A check that did not run never passes", rules a file that cannot be
parsed and a run with no input out of passing.

The quality-gates design's Gates section requires exit 0 for no findings, 1 for findings or an empty run and 2 for
an unfinished check. A finding's source anchor associates a line number with its path, independently of preceding
diagnostic numbering. The shared runner writes gate lines to stdout, with the seeded root cut out first. Every run starts from the seeded root,
so each seeded folder is a top-level folder of the inputs.
"""

import re
import string
from pathlib import Path

import pytest

from gates.check_shell import main
from tests.support.capture import captured
from tests.support.project import scaffold

CLEAN = "VALUE = 1\n"

MALFORMED = "def broken(:\n    return\n"

UNFINISHED = 2

PUNCTUATION_TO_SPACE = str.maketrans(string.punctuation, " " * len(string.punctuation))


def _seed(root: Path, relative: str, source: str) -> Path:
    """Seed the file in a project tree carrying the repository's own pyproject.toml, so the gate runs under its settings."""
    scaffold(root, {relative: source})
    return Path(relative)


def _clean_status(root: Path) -> int:
    return main([_seed(root, "gauntlet/clean.py", CLEAN)])


def _lines(
    root: Path, paths: list[Path], capsys: pytest.CaptureFixture[str]
) -> tuple[list[str], list[str]]:
    with capsys.disabled():
        output = captured(lambda: main(paths))
    return (
        [line.replace(f"{root}/", "").rstrip("\n") for line in output.out],
        output.err,
    )


def _finding_lines(lines: list[str], name: str, line: int, construct: str) -> int:
    """Count full-path anchors with the source line before or after the path."""
    path = re.compile(
        r"(?<![\w./\\-])" + re.escape(f"gauntlet/{name}") + r"(?![\w./\\-])"
    )
    count = 0
    for text in lines:
        anchor = path.search(text)
        if anchor is None or construct not in text:
            continue
        after = text[anchor.end() :].translate(PUNCTUATION_TO_SPACE).split()
        before = text[: anchor.start()].translate(PUNCTUATION_TO_SPACE).split()
        following = [field for field in after if field.isdecimal()]
        preceding = [field for field in before if field.isdecimal()]
        source_line = following[:1] or preceding[-1:]
        count += source_line == [str(line)]
    return count


def test_import_finding_names_file_line_and_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An import of shlex on line 3 is one finding, on one line naming the file, line 3 and shlex."""
    monkeypatch.chdir(tmp_path)
    path = _seed(tmp_path, "gauntlet/alpha.py", "VALUE = 1\n\nimport shlex\n")
    lines, stderr = _lines(tmp_path, [path], capsys)

    assert (_finding_lines(lines, "alpha.py", 3, "shlex"), stderr) == (1, [])


def test_dynamic_import_finding_names_file_line_and_module(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An importlib.import_module call naming bashparserlib on line 4 is one finding naming the file, line 4 and bashparserlib."""
    monkeypatch.chdir(tmp_path)
    source = 'import importlib\n\n\nmodule = importlib.import_module("bashparserlib")\n'
    path = _seed(tmp_path, "gauntlet/alpha.py", source)
    lines, stderr = _lines(tmp_path, [path], capsys)

    assert (_finding_lines(lines, "alpha.py", 4, "bashparserlib"), stderr) == (1, [])


def test_shell_true_finding_names_file_line_and_keyword(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """shell=True passed to subprocess.run on line 5 is one finding naming the file, line 5 and the shell keyword."""
    monkeypatch.chdir(tmp_path)
    source = (
        'import subprocess\n\nVALUE = 1\n\nsubprocess.run("make check", shell=True)\n'
    )
    path = _seed(tmp_path, "gauntlet/alpha.py", source)
    lines, stderr = _lines(tmp_path, [path], capsys)

    assert (_finding_lines(lines, "alpha.py", 5, "shell"), stderr) == (1, [])


def test_two_uses_are_two_findings_each_at_its_own_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Two prohibited imports, on lines 1 and 3, give one finding each, each naming its own line and module."""
    monkeypatch.chdir(tmp_path)
    path = _seed(tmp_path, "gauntlet/alpha.py", "import shlex\n\nimport shellparse\n")
    lines, stderr = _lines(tmp_path, [path], capsys)

    assert (
        _finding_lines(lines, "alpha.py", 1, "shlex"),
        _finding_lines(lines, "alpha.py", 3, "shellparse"),
        stderr,
    ) == (1, 1, [])


def test_finding_names_the_file_holding_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """With a clean file and a dirty one, the finding names the dirty file and no line names the clean one with shlex."""
    monkeypatch.chdir(tmp_path)
    clean = _seed(tmp_path, "gauntlet/first.py", "import json\n\nimport os\n")
    dirty = _seed(tmp_path, "gauntlet/second.py", "import json\n\nimport shlex\n")
    lines, stderr = _lines(tmp_path, [clean, dirty], capsys)

    assert (
        _finding_lines(lines, "second.py", 3, "shlex"),
        _finding_lines(lines, "first.py", 3, "shlex"),
        stderr,
    ) == (1, 0, [])


def test_nested_product_module_is_in_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file in a package below gauntlet/ is gauntlet/ code, so its shlex import is a finding."""
    monkeypatch.chdir(tmp_path)
    dirty = _seed(tmp_path, "gauntlet/core/alpha.py", "import shlex\n")

    assert (main([dirty]), _clean_status(tmp_path)) == (1, 0)
    assert main([dirty]) != _clean_status(tmp_path)


@pytest.mark.parametrize(
    "relative",
    [
        pytest.param("tests/alpha.py", id="tests"),
        pytest.param("gates/alpha.py", id="gates"),
        pytest.param("gauntlet_extra/alpha.py", id="name-extending-product-folder"),
    ],
)
def test_file_outside_product_code_is_no_finding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    relative: str,
) -> None:
    """Findings apply to gauntlet/ code only, so a shlex import elsewhere ends the run as a clean file does and is named on no line."""
    monkeypatch.chdir(tmp_path)
    outside = _seed(tmp_path, relative, "import shlex\n")
    status = main([outside])
    captured = capsys.readouterr()
    text = (captured.out + captured.err).replace(str(tmp_path), "")
    clean = _clean_status(tmp_path)

    assert (status == clean, "shlex" in text) == (True, False)


def test_outside_file_alone_is_counted_as_a_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every input Python file is counted, so a run over one clean file outside gauntlet/ ends as a clean product file does."""
    monkeypatch.chdir(tmp_path)
    outside = _seed(tmp_path, "tests/alpha.py", CLEAN)
    with capsys.disabled():
        output = captured(lambda: main([outside]))

    assert main([outside]) == _clean_status(tmp_path)
    assert output.err == []
    assert (
        output.out[-1].rstrip("\n") == "check_shell: 0 finding(s) in 1 Python file(s)"
    )


def test_outside_dirty_file_beside_clean_product_file_ends_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A shlex import outside gauntlet/ next to a clean gauntlet/ file leaves the run ending as a clean run."""
    monkeypatch.chdir(tmp_path)
    outside = _seed(tmp_path, "tests/alpha.py", "import shlex\n")
    product = _seed(tmp_path, "gauntlet/beta.py", CLEAN)
    status = main([outside, product])

    assert status == _clean_status(tmp_path)


def test_dirty_product_file_among_clean_ones_fails_the_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One dirty gauntlet/ file between clean ones makes the run end unlike a clean run."""
    monkeypatch.chdir(tmp_path)
    first = _seed(tmp_path, "gauntlet/first.py", CLEAN)
    dirty = _seed(tmp_path, "gauntlet/dirty.py", "import bashlex\n")
    last = _seed(tmp_path, "gauntlet/last.py", CLEAN)
    status = main([first, dirty, last])

    assert status == 1
    assert status != _clean_status(tmp_path)


@pytest.mark.parametrize(
    "relative",
    [
        pytest.param("gauntlet/broken.py", id="product"),
        pytest.param("tests/broken.py", id="outside-product"),
    ],
)
def test_malformed_source_never_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relative: str
) -> None:
    """Every input Python file is parsed, and a check that did not run never passes, so a file that cannot be parsed fails the run."""
    monkeypatch.chdir(tmp_path)
    broken = _seed(tmp_path, relative, MALFORMED)

    assert main([broken]) == UNFINISHED
    assert main([broken]) != _clean_status(tmp_path)


def test_malformed_file_beside_clean_one_never_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A file that cannot be parsed fails the run even when a clean gauntlet/ file is checked beside it."""
    monkeypatch.chdir(tmp_path)
    product = _seed(tmp_path, "gauntlet/beta.py", CLEAN)
    broken = _seed(tmp_path, "gauntlet/broken.py", MALFORMED)

    assert main([product, broken]) == UNFINISHED
    assert main([product, broken]) != _clean_status(tmp_path)


def test_empty_run_never_passes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A run given no file checks nothing, and a check that did not run never passes."""
    monkeypatch.chdir(tmp_path)
    with capsys.disabled():
        output = captured(lambda: main([]))
    status = output.result
    assert output.err == []
    lines = [line.rstrip("\n") for line in output.out]

    assert status == 1
    assert status != _clean_status(tmp_path)
    assert len(lines) == len(("empty-run diagnostic", "count line"))
    assert "check" in lines[0].lower()
    assert any(word in lines[0].lower() for word in ("nothing", "no ", "0 "))
    assert lines[-1] == "check_shell: 0 finding(s) in 0 Python file(s)"
