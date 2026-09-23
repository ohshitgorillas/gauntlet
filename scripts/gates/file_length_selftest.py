#!/usr/bin/env python3
"""The `--self-test` body of `file-length.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays readable as a
pair of rules and a table, and `python3 scripts/gates/file-length.py --self-test`
runs it.

Each case writes real files of a known length into a throwaway tree, changes
into it so the paths reaching the gate are repo-relative the way a real run
passes them, and hands the gate its own allowance table. What is checked is the
pair the gate offers a caller: the exit code, and what lands on stdout.
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

GATE_PATH = Path(__file__).resolve().parent / "file-length.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    spec = importlib.util.spec_from_file_location("file_length_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _write(root: Path, relpath: str, lines: int) -> str:
    """Write a file of exactly `lines` lines under `root`; return its relative path."""
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"x = {n}\n" for n in range(lines)))
    return relpath


def _run(
    files: dict[str, int], names: list[str] | None, allowance: dict[str, int]
) -> tuple[int, str]:
    """Build a tree of `files`, run the gate over `names`, and return its status and stdout.

    With `names` None the tree is a git checkout the files sit in untracked, and
    the gate picks its own file set.
    """
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relpath, lines in files.items():
            _write(root, relpath, lines)
        if names is None:
            subprocess.run(["git", "init", "-q", tmp], check=True, capture_output=True, timeout=60)
        os.chdir(root)
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                status = GATE.check(GATE.tracked_files() if names is None else names, allowance)
        finally:
            os.chdir(cwd)
    return status, out.getvalue()


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

    WATCH = GATE.WATCH_LINE
    small = "hooks/small.py"
    long_file = "hooks/long.py"
    suite = "tests/test_many.py"

    status, out = _run({small: 120}, [small], {})
    check("a short source file with no entry passes", (status, out), (0, ""))

    status, _ = _run({small: WATCH}, [small], {})
    check("a source file at the watch line passes with no entry", status, 0)

    status, out = _run({long_file: WATCH + 1}, [long_file], {})
    check("a source file over the watch line with no entry fails", status, 1)
    check("the file over the watch line is named on stdout", long_file in out, True)
    check("the entry it is told to add states its length", str(WATCH + 1) in out, True)

    status, out = _run({long_file: 437}, [long_file], {long_file: 437})
    check("a source file matching its allowance exactly passes", (status, out), (0, ""))

    status, out = _run({long_file: 452}, [long_file], {long_file: 437})
    check("a source file longer than its allowance fails", status, 1)
    check("the grown file is named on stdout", long_file in out, True)

    status, out = _run({long_file: 421}, [long_file], {long_file: 437})
    check("a source file shorter than its allowance fails", status, 1)
    check("the shrunk file is told the lower number", "421" in out, True)

    status, out = _run({small: 120}, [small], {"hooks/deleted.py": 437})
    check("an allowance naming no file on disk fails as stale", status, 1)
    check("the stale entry is named on stdout", "hooks/deleted.py" in out, True)

    status, _ = _run({"hooks/untouched.py": 437, small: 90}, [small], {"hooks/untouched.py": 437})
    check("a live allowance for a file not on argv passes", status, 0)

    status, _ = _run({"hooks/untouched.py": 180, small: 90}, [small], {"hooks/untouched.py": 437})
    check("a stale allowance for a file not on argv still fails", status, 1)

    status, out = _run({long_file: 180}, [long_file], {long_file: 437})
    check("an allowance for a file back under the watch line fails as stale", status, 1)
    check("the dead entry is named on stdout", long_file in out, True)

    status, _ = _run({long_file: WATCH}, [long_file], {long_file: WATCH})
    check("an allowance for a file at the watch line fails as stale", status, 1)

    cap = GATE.MAX_LINES
    status, _ = _run({long_file: cap}, [long_file], {long_file: cap})
    check("a source file at the hard cap passes with a matching allowance", status, 0)

    status, _ = _run({long_file: cap + 1}, [long_file], {long_file: cap + 1})
    check("an allowance cannot sell permission past the hard cap", status, 1)

    status, _ = _run({long_file: cap + 1}, [long_file], {})
    check("a source file over the hard cap with no entry fails", status, 1)

    status, _ = _run({suite: 640}, [suite], {})
    check("a test file over the watch line passes with no entry", status, 0)

    tests_cap = GATE.MAX_LINES_TESTS
    status, _ = _run({suite: tests_cap}, [suite], {})
    check("a test file at the 800-line cap passes", status, 0)

    status, _ = _run({suite: tests_cap + 1}, [suite], {})
    check("a test file over the 800-line cap fails", status, 1)

    status, out = _run({suite: 640}, [suite], {suite: 640})
    check("an allowance naming a test path fails as stale", status, 1)
    check("the test-path entry is named on stdout", suite in out, True)

    files = {"hooks/one.py": 90, "hooks/two.py": 455, "hooks/three.py": 470, "hooks/four.py": 44}
    status, out = _run(files, list(files), {})
    check("one offender among compliant files fails the gate", status, 1)
    check(
        "every offender is reported, not only the first",
        ("hooks/two.py" in out, "hooks/three.py" in out),
        (True, True),
    )
    check("a compliant file beside an offender is not named", "hooks/one.py" in out, False)

    status, out = _run({long_file: cap + 1}, None, {})
    check("with no paths an untracked code file is read", (status, long_file in out), (1, True))

    check("the shipped tree passes its own gate", GATE.main(["file-length.py"]), 0)

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
