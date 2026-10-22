"""Red tests for the suppression gate's exit status on a marker in any Python file.

Sources: the quality-gates design spec under docs/superpowers/specs/, "Gates" (the
gate contract: exit 1 with one or more findings; what a Python file is; the count line
`<gate>: N finding(s) in M Python file(s)` is the last line a finished run prints) and
"Suppression gate" (the comment markers and the decorator it fails on).
"""

from pathlib import Path

import pytest

from gates.check_suppressions import main

FINDINGS_STATUS = 1
ONE_FINDING_COUNT_LINE = "check_suppressions: 1 finding(s) in 1 Python file(s)"

DIRECTIVE_SOURCES = [
    "# mypy: ignore-errors\nvalue = 1\n",
    "# pyright: basic\nvalue = 1\n",
    "# fmt: off\nvalue = 1\n# fmt: on\n",
    "value = 1  # fmt: skip\n",
]

PYTHON_SHEBANGS = ["#!/usr/bin/env python3\n", "#!/usr/bin/python\n"]


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize("source", DIRECTIVE_SOURCES)
def test_gate_exits_with_findings_status_on_directive_comment(
    tmp_path: Path, source: str
) -> None:
    """Exit with the findings status on a mypy, pyright or fmt directive comment."""
    path = _seed(tmp_path, "directive.py", source)

    assert main([path]) == FINDINGS_STATUS


@pytest.mark.parametrize("source", DIRECTIVE_SOURCES)
def test_gate_exits_with_findings_status_on_directive_in_stub_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], source: str
) -> None:
    """Exit with the findings status on a directive comment in a .pyi file, counted as one finding in one Python file."""
    path = _seed(tmp_path, "seeded.pyi", source)
    status = main([path])

    assert (status, capsys.readouterr().out.splitlines()[-1]) == (
        FINDINGS_STATUS,
        ONE_FINDING_COUNT_LINE,
    )


@pytest.mark.parametrize("source", DIRECTIVE_SOURCES)
@pytest.mark.parametrize("shebang", PYTHON_SHEBANGS)
def test_gate_exits_with_findings_status_on_directive_in_python_script(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], shebang: str, source: str
) -> None:
    """Exit with the findings status on a directive comment in an extensionless python-shebang script, counted as one finding in one Python file."""
    path = _seed(tmp_path, "seeded-script", shebang + source)
    status = main([path])

    assert (status, capsys.readouterr().out.splitlines()[-1]) == (
        FINDINGS_STATUS,
        ONE_FINDING_COUNT_LINE,
    )


def test_gate_exits_with_findings_status_on_no_type_check_decorator(
    tmp_path: Path,
) -> None:
    """Exit with the findings status on a typing.no_type_check decorator."""
    source = (
        "import typing\n\n\n@typing.no_type_check\ndef seeded() -> None:\n    pass\n"
    )
    path = _seed(tmp_path, "decorated.py", source)

    assert main([path]) == FINDINGS_STATUS
