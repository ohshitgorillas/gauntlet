"""Red tests for what the pytest gate prints over a test file pytest did not finish.

Source: the quality gates design spec under docs/superpowers/specs/, "Tests", the "pytest strictness" bullet: "over one
pytest did not finish it prints pytest's whole console output, stdout and stderr, as pytest's own error, so a run that
collected no test still prints what pytest said", and "Anything that stops pytest before or during collection is a run
the checker did not finish, exit 2, with pytest's own error printed and the count line still printed: a collection
error, ..., or no test collected from the test files given". The "Gates" intro: the count line "is the last line the
run prints", and a run whose checker could not finish prints it "as the last line it prints, after what the checker
reported".

The documents do not spell pytest's own text, so each run seeds its own: a `conftest.py` beside the test module prints
one token to pytest's stdout and another to pytest's stderr when pytest's session finishes, which it does over a module
that collected no test and over one whose import fails at collection alike. Each token must come back as a line of
the gate's output, before the count line. The gate runs in this interpreter under `tests/support/capture.py`, which
sees every line written to fd 1 or fd 2, by the gate or a child it starts, in the order written.

Test names are kept short so that each line of pytest's short summary names its exception.
"""

import re
from pathlib import Path

from gates.check_pytest import main
from tests.support.capture import captured

OUT_TOKEN = "SeededOut"

ERR_TOKEN = "SeededErr"

SPEAKING_CONFTEST = (
    "import sys\n\n\n"
    "def pytest_sessionfinish(session, exitstatus):\n"
    f"    print('{OUT_TOKEN}', file=sys.stdout, flush=True)\n"
    f"    print('{ERR_TOKEN}', file=sys.stderr, flush=True)\n"
)

NO_TESTS = "SEEDED_VALUE = 1\n"

MISSING_MODULE = "seededmissingmodule"

COLLECTION_ERROR = f"import {MISSING_MODULE}\n\n\ndef test_seeded():\n    pass\n"

COUNT_LINE = re.compile(r"check_pytest: 0 finding\(s\) in \d+ Python file\(s\)")


def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _printed(root: Path, source: str) -> tuple[list[str], str]:
    """The lines the gate printed over the seeded module and its speaking conftest, endings dropped, split off its last."""
    paths = [_seed(root, "tests/test_seeded.py", source), _seed(root, "tests/conftest.py", SPEAKING_CONFTEST)]
    lines = [line.rstrip("\n") for line in captured(lambda: main(paths)).merged]
    return lines[:-1], "".join(lines[-1:])


def test_empty(tmp_path: Path) -> None:
    """Over a module that collected no test, pytest's stdout line and its stderr line both print before the count line."""
    before, last = _printed(tmp_path, NO_TESTS)

    assert (OUT_TOKEN in before, ERR_TOKEN in before, COUNT_LINE.fullmatch(last) is not None) == (True, True, True)


def test_error(tmp_path: Path) -> None:
    """Over a module whose import fails, pytest's stdout line and its stderr line both print before the count line."""
    before, last = _printed(tmp_path, COLLECTION_ERROR)

    assert (OUT_TOKEN in before, ERR_TOKEN in before, COUNT_LINE.fullmatch(last) is not None) == (True, True, True)
