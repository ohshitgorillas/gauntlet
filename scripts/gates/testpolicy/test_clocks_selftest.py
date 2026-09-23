"""The `--self-test` body of `test-clocks.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays readable as two
patterns and a threshold, and `python3 scripts/gates/testpolicy/test-clocks.py --self-test`
runs it.

Each case writes a real module into a throwaway tree, changes into it so the
paths reaching the gate are repo-relative the way a real run passes them, and
reads back the pair the gate offers a caller: the exit code, and what lands on
stdout.
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "test-clocks.py"
MODULE = "tests/test_sample.py"
E2E = "tests/e2e/test_browser.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location("test_clocks_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _run(source: str, name: str = MODULE, listed: bool = False) -> tuple[int, str]:
    """Write `source` into a throwaway tree, run the gate over it, and return its
    status and stdout. With `listed` the tree is a git checkout the module sits in
    untracked, and the gate picks its own file set."""
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source)
        if listed:
            subprocess.run(["git", "init", "-q", tmp], check=True, capture_output=True, timeout=60)
        os.chdir(tmp)
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                status = GATE.check(GATE.tracked_tests() if listed else [name])
        finally:
            os.chdir(cwd)
    return status, out.getvalue()


SLEEP = "import time\n\n\ndef test_wait():\n    time.sleep(0.25)\n"
ASYNC_SLEEP = "import asyncio\n\n\nasync def test_wait():\n    await asyncio.sleep(0.25)\n"
YIELD = "import time\n\n\ndef test_yield():\n    time.sleep(0)\n"
NAMED_WAIT = "import time\n\n\ndef test_named():\n    time.sleep(GAP)\n"
SEAM_SLEEP = "def test_seam(clock):\n    clock.sleep(5)\n"
DEADLINE = "def test_deadline():\n    poll(timeout=0.05)\n"
SUFFIX_DEADLINE = "def test_deadline():\n    poll(read_timeout=0.05)\n"
CEILING = "def test_ceiling():\n    poll(timeout=5)\n"
ZERO = "def test_zero():\n    poll(timeout=0)\n"
MAPPING = "def test_mapping():\n    request(CONFIG, {'read_timeout': 0.05})\n"
OTHER_KEYWORD = "def test_other():\n    poll(interval=0.05)\n"


def self_test() -> int:
    """One PASS or FAIL per rule this gate exists to hold."""
    failed = 0

    def check(rule: str, got: object, want: object) -> None:
        nonlocal failed
        if got == want:
            print(f"PASS {rule}")
        else:
            failed += 1
            print(f"FAIL {rule}: {got!r} != {want!r}")

    status, out = _run(SLEEP)
    check("a real sleep fails", status, 1)
    check("the sleeping line is named on stdout", f"{MODULE}:5" in out, True)

    status, _ = _run(ASYNC_SLEEP)
    check("an asyncio sleep fails", status, 1)

    status, out = _run(YIELD)
    check("a sleep of zero is a scheduler yield and passes", (status, out), (0, ""))

    status, _ = _run(NAMED_WAIT)
    check("a sleep of a named constant fails", status, 1)

    status, out = _run(SEAM_SLEEP)
    check("a sleep on a seam the test controls passes", (status, out), (0, ""))

    status, out = _run(DEADLINE)
    check("a timeout under half a second fails", status, 1)
    check("the deadline keyword is named on stdout", "timeout=" in out, True)

    status, _ = _run(SUFFIX_DEADLINE)
    check("a suffixed timeout keyword under half a second fails", status, 1)

    status, out = _run(CEILING)
    check("a timeout of seconds is a ceiling and passes", (status, out), (0, ""))

    status, out = _run(ZERO)
    check("a timeout of zero waits on nothing and passes", (status, out), (0, ""))

    status, out = _run(MAPPING)
    check("a small deadline under a mapping key fails", status, 1)
    check("the mapping key is quoted on stdout", "read_timeout" in out, True)

    status, out = _run(OTHER_KEYWORD)
    check("a small number under another keyword passes", (status, out), (0, ""))

    status, _ = _run(SLEEP, name=E2E)
    check("an end-to-end test gets no carve-out from the sleep ban", status, 1)

    status, out = _run(SLEEP, listed=True)
    check("with no paths an untracked test module is read", (status, MODULE in out), (1, True))

    check("the shipped suite passes its own gate", GATE.main(["test-clocks.py"]), 0)

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
