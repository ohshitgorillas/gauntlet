"""Red tests for the pytest gate on a host whose CPU count it cannot read.

Source: the quality gates design spec under docs/superpowers/specs/, "Tests", the "pytest strictness" bullet, the
sub-bullet beginning "Each test module": "a host whose CPU count the gate cannot read is a run the checker did not
finish, exit 2." The "Gates" intro: a gate exits 2 when its checker could not finish, prints its count line on every
run, and a run whose checker could not finish prints that count line "as the last line it prints".

The gate's `main` takes the CPU reader as `read_cpus`; a reader that returns None is a host whose count cannot be read.
The seeded test module passes, so a gate that ran it anyway on some fallback count would find nothing and exit 0, and
reads no failing test either way, so N in the count line is 0. M is 1, the one module given: the gates core design spec,
runner.py, makes M `len(sources)` for every gate. The gate runs in this interpreter under `tests/support/capture.py`.

Test names are kept short so that each line of pytest's short summary names its exception.
"""

import re
from pathlib import Path

from gates.check_pytest import main
from tests.support.capture import captured

NOT_FINISHED = 2

PASSING = "def test_seeded():\n    pass\n"

COUNT_LINE = re.compile(r"check_pytest: 0 finding\(s\) in 1 Python file\(s\)")


def _unreadable() -> int | None:
    return None


def _seed(root: Path) -> Path:
    path = root / "tests" / "test_seeded.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PASSING, encoding="utf-8")
    return path


def test_exit(tmp_path: Path) -> None:
    """An unreadable CPU count ends the run unfinished, exit 2, though the one module given would pass."""
    module = _seed(tmp_path)

    assert main([module], read_cpus=_unreadable) == NOT_FINISHED


def test_count(tmp_path: Path) -> None:
    """An unreadable CPU count still prints the count line, with no finding, as the last line of the run."""
    module = _seed(tmp_path)
    run = captured(lambda: main([module], read_cpus=_unreadable))
    last = "".join(line.rstrip("\n") for line in run.merged[-1:])

    assert (run.result, COUNT_LINE.fullmatch(last) is not None) == (NOT_FINISHED, True)
