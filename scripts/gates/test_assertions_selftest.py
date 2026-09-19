"""The `--self-test` body of `test-assertions.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays readable as a
table of categories, and `python3 scripts/gates/test-assertions.py --self-test`
runs it.

Each case writes a real module into a throwaway tree, changes into it so the
paths reaching the gate are repo-relative the way a real run passes them, and
hands the gate its own exemption table. What is checked is the pair the gate
offers a caller: the exit code, and what lands on stdout.
"""

from __future__ import annotations

import importlib.util
import io
import os
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "test-assertions.py"
MODULE = "tests/test_sample.py"
SUPPORT = "tests/support/fake.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location("test_assertions_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _run(source: str, exempt: dict[str, str] | None = None, name: str = MODULE) -> tuple[int, str]:
    """Write `source` into a throwaway tree, run the gate over it, and return its status and stdout."""
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        os.chdir(tmp)
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                status = GATE.check([name], exempt or {})
        finally:
            os.chdir(cwd)
    return status, out.getvalue()


ONE = "def test_one():\n    assert compute() == 3\n"
TWO = "def test_two():\n    assert compute() == 3\n    assert compute() == 4\n"
NONE = "def test_none():\n    compute()\n"
RAISES = "import pytest\n\n\ndef test_raises():\n    with pytest.raises(ValueError):\n        compute()\n"
FRAMEWORK = (
    "import unittest\n\n\n"
    "class Suite(unittest.TestCase):\n"
    "    def test_one(self):\n"
    "        self.assertEqual(compute(), 3)\n"
)
FRAMEWORK_TWO = FRAMEWORK + "        self.assertEqual(compute(), 4)\n"
CONJUNCTION = "def test_both():\n    assert compute() == 3 and other() == 4\n"
IN_LOOP = "def test_sweep():\n    for case in CASES:\n        assert compute(case) == 3\n"
ALL_SWEEP = "def test_all():\n    assert all(compute(c) == 3 for c in CASES)\n"
HELPER = "def helper():\n    assert compute() == 3\n\n\ndef test_one():\n    assert compute() == 3\n"
HELPER_METHOD = (
    "import unittest\n\n\n"
    "class Suite(unittest.TestCase):\n"
    "    def _both(self):\n"
    "        self.assertEqual(compute(), 3)\n\n"
    "    def test_one(self):\n"
    "        self.assertEqual(self._both(), None)\n"
)
NESTED ="def test_one():\n    def inner():\n        assert compute() == 4\n\n    assert inner() == 3\n"
EXISTENCE = "def test_present():\n    assert compute() is not None\n"
LENGTH = "def test_length():\n    assert len(compute()) > 0\n"
SKIPPED = "import pytest\n\n\n@pytest.mark.skip\ndef test_one():\n    assert compute() == 3\n"
PRIVATE = "def test_one():\n    assert widget._hidden == 3\n"
DUNDER = "def test_one():\n    assert widget.__class__ == Widget\n"
OWN_PRIVATE = (
    "import unittest\n\n\n"
    "class Suite(unittest.TestCase):\n"
    "    def test_one(self):\n"
    "        self.assertEqual(self._widget(), 3)\n"
)


def self_test() -> int:  # noqa: PLR0915
    """One PASS or FAIL per rule this gate exists to hold."""
    failed = 0

    def check(rule: str, got: object, want: object) -> None:
        nonlocal failed
        if got == want:
            print(f"PASS {rule}")
        else:
            failed += 1
            print(f"FAIL {rule}: {got!r} != {want!r}")

    status, out = _run(ONE)
    check("a test with one assertion passes", (status, out), (0, ""))

    status, out = _run(TWO)
    check("a test with two assertions fails", status, 1)
    check("the offending test is named on stdout", "test_two" in out, True)
    check("the count it holds is on stdout", "2 assertions" in out, True)

    status, _ = _run(NONE)
    check("a test with no assertion fails", status, 1)

    status, out = _run(RAISES)
    check("a pytest.raises context is the one assertion", (status, out), (0, ""))

    status, out = _run(FRAMEWORK)
    check("a framework assertion is the one assertion", (status, out), (0, ""))

    status, _ = _run(FRAMEWORK_TWO)
    check("two framework assertions in one test fail", status, 1)

    status, out = _run(CONJUNCTION)
    check("a conjunction counts one assertion per operand", status, 1)
    check("the conjunction is counted, not the statement", "2 assertions" in out, True)

    status, out = _run(IN_LOOP)
    check("an assertion inside a loop fails", status, 1)
    check("the loop is named as the category", "loop" in out, True)

    status, out = _run(ALL_SWEEP)
    check("all() at the root of an assertion fails", status, 1)
    check("the sweep is named as the category", "loop" in out, True)

    status, out = _run(HELPER)
    check("an assertion in a module-level helper fails", status, 1)
    check("the helper is named as the category", "outside" in out, True)

    status, out = _run(HELPER_METHOD)
    check("an assertion in a helper method fails", status, 1)
    check("the helper method is named as the category", "outside" in out, True)

    status, out = _run(NESTED)
    check("an assertion inside a nested function is not counted", (status, out), (0, ""))

    status, out = _run(EXISTENCE)
    check("an existence-only assertion fails", status, 1)
    check("the existence shape is named as the category", "existence" in out, True)

    status, _ = _run(LENGTH)
    check("a length-only assertion fails", status, 1)

    status, out = _run(EXISTENCE, {f"{MODULE}::test_present": "owner-approved"})
    check("an exempted existence site passes", (status, out), (0, ""))

    status, out = _run(SKIPPED)
    check("a skip decorator fails", status, 1)
    check("the skip is named as the category", "skip" in out, True)

    status, out = _run(SKIPPED, {f"{MODULE}::test_one": "owner-approved"})
    check("an exempted skip passes", (status, out), (0, ""))

    status, out = _run(PRIVATE)
    check("a private reach fails", status, 1)
    check("the private reach is named as the category", "private" in out, True)

    status, out = _run(DUNDER)
    check("a dunder reach passes as protocol", (status, out), (0, ""))

    status, out = _run(OWN_PRIVATE)
    check("a private reach on self passes", (status, out), (0, ""))

    status, out = _run(PRIVATE, name=SUPPORT)
    check("a support fake reaching its own state is not scanned", (status, out), (0, ""))

    check("the shipped suite passes its own gate", GATE.main(["test-assertions.py"]), 0)

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
