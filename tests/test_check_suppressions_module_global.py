"""Red tests for the suppression gate on a module that uses `global` at module level.

Source: the quality gates design spec under docs/superpowers/specs/, "Suppression gate", third bullet: "a file the gate reads and parses is a file the gate finishes, with exit 0 or 1, and an error in the gate's own resolution of names on such a file is a defect of the gate"; and "Gates": "A gate exits 0 with no finding" and its count line reads `<gate>: N finding(s) in M Python file(s)`, the last line the run prints.
"""

from pathlib import Path

import pytest

from gates.check_suppressions import main

CLEAN_COUNT_LINE = "check_suppressions: 0 finding(s) in 1 Python file(s)"

SOURCES = [
    pytest.param("global value\nvalue = 1\nprint(value)\n", id="bound-and-read"),
    pytest.param(
        "global value\nvalue = 1\n\n\ndef read():\n    global value\n    return value\n",
        id="also-in-function",
    ),
]


@pytest.mark.parametrize("source", SOURCES)
def test_module_level_global_finishes_with_no_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], source: str
) -> None:
    path = tmp_path / "module_global.py"
    path.write_text(source, encoding="utf-8")

    code = main([path])
    last_line = capsys.readouterr().out.splitlines()[-1]

    assert (code, last_line) == (0, CLEAN_COUNT_LINE)
