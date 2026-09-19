"""The argv surface of the three test-policy gates.

Each gate takes paths on argv and falls back to `git ls-files 'tests/*.py'`, and
each returns 0 when the files it read hold nothing and 1 when they do. What is
checked here is that pair -- the status, and the location on stdout -- over a
throwaway tree, never the gates' own internals.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

GATES = Path(__file__).resolve().parent.parent / "scripts" / "gates"


def _load(stem: str) -> ModuleType:
    """Import a gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location(stem.replace("-", "_"), GATES / f"{stem}.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {stem}")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(GATES))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(GATES))
    return module


ASSERTIONS = _load("test-assertions")
NO_COPY = _load("no-copy-assertions")
CLOCKS = _load("test-clocks")

ONE = "def test_one():\n    assert compute() == 3\n"
TWO = "def test_two():\n    assert compute() == 3\n    assert compute() == 4\n"
UNITTEST_TWO = (
    "import unittest\n\n\n"
    "class Suite(unittest.TestCase):\n"
    "    def test_pair(self):\n"
    "        self.assertEqual(compute(), 3)\n"
    "        self.assertEqual(compute(), 4)\n"
)
SEEDED = "def test_seeded():\n    reply = 'alpha beta gamma'\n    assert send(reply) == 'alpha beta gamma'\n"
COPY = "def test_copy():\n    assert send() == 'alpha beta gamma'\n"
UNITTEST_COPY = (
    "import unittest\n\n\n"
    "class Suite(unittest.TestCase):\n"
    "    def test_copy(self):\n"
    "        self.assertEqual(send(), 'alpha beta gamma')\n"
)
YIELD = "import time\n\n\ndef test_yield():\n    time.sleep(0)\n"
SLEEP = "import time\n\n\ndef test_sleep():\n    time.sleep(0.25)\n"
DEADLINE = "def test_deadline():\n    poll(timeout=0.05)\n"


def _module(tmp_path: Path, source: str) -> str:
    """Write a test module into a throwaway tests/ tree; return its path."""
    path = tmp_path / "tests" / "test_sample.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    return str(path)


def _repo(tmp_path: Path, source: str) -> Path:
    """Build a git checkout whose tests/ holds one committed module; return its root."""
    _module(tmp_path, source)
    for args in (("init",), ("add", "tests")):
        subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path


def test_a_single_assertion_test_passes_the_assertion_gate(tmp_path):
    assert ASSERTIONS.main(["gate", _module(tmp_path, ONE)]) == 0


def test_a_second_assertion_in_one_test_fails_the_assertion_gate(tmp_path):
    assert ASSERTIONS.main(["gate", _module(tmp_path, TWO)]) == 1


def test_the_assertion_gate_names_the_offending_test_and_its_count(tmp_path, capsys):
    ASSERTIONS.main(["gate", _module(tmp_path, TWO)])
    assert "test_two: 2 assertions" in capsys.readouterr().out


def test_a_framework_assertion_counts_as_an_assertion(tmp_path, capsys):
    ASSERTIONS.main(["gate", _module(tmp_path, UNITTEST_TWO)])
    assert "test_pair: 2 assertions" in capsys.readouterr().out


def test_the_assertion_gate_reads_the_tracked_tests_when_argv_names_none(tmp_path, monkeypatch):
    monkeypatch.chdir(_repo(tmp_path, TWO))
    assert ASSERTIONS.main(["gate"]) == 1


def test_a_seeded_literal_passes_the_copy_gate(tmp_path):
    assert NO_COPY.main(["gate", _module(tmp_path, SEEDED)]) == 0


def test_a_literal_the_test_never_seeded_fails_the_copy_gate(tmp_path):
    assert NO_COPY.main(["gate", _module(tmp_path, COPY)]) == 1


def test_the_copy_gate_names_the_line_and_the_literal(tmp_path, capsys):
    path = _module(tmp_path, COPY)
    NO_COPY.main(["gate", path])
    assert f"{path}:2 assert-literal: 'alpha beta gamma'" in capsys.readouterr().out


def test_a_framework_assertions_literal_is_copy_too(tmp_path):
    assert NO_COPY.main(["gate", _module(tmp_path, UNITTEST_COPY)]) == 1


def test_the_copy_gate_reads_the_tracked_tests_when_argv_names_none(tmp_path, monkeypatch):
    monkeypatch.chdir(_repo(tmp_path, COPY))
    assert NO_COPY.main(["gate"]) == 1


def test_a_scheduler_yield_passes_the_clock_gate(tmp_path):
    assert CLOCKS.main(["gate", _module(tmp_path, YIELD)]) == 0


def test_a_real_sleep_fails_the_clock_gate(tmp_path):
    assert CLOCKS.main(["gate", _module(tmp_path, SLEEP)]) == 1


def test_a_small_timeout_fails_the_clock_gate(tmp_path):
    assert CLOCKS.main(["gate", _module(tmp_path, DEADLINE)]) == 1


def test_the_clock_gate_names_the_line_the_sleep_sits_on(tmp_path, capsys):
    path = _module(tmp_path, SLEEP)
    CLOCKS.main(["gate", path])
    assert capsys.readouterr().out.startswith(f"{path}:5:")


def test_the_clock_gate_reads_the_tracked_tests_when_argv_names_none(tmp_path, monkeypatch):
    monkeypatch.chdir(_repo(tmp_path, SLEEP))
    assert CLOCKS.main(["gate"]) == 1
