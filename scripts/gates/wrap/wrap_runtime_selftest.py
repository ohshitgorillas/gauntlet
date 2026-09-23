#!/usr/bin/env python3
"""The `--self-test` body of `wrap-runtime.py`: one line per rule the gate holds.

The gate's `--check` runs the live hook's wrap and reads the processes back.
This body hands `judge` invented processes instead, so each rule is read on its
own: a rule that stopped firing is caught here rather than by a report that was
green because every probe happened to pass.

One rule is not invented. The last builds a checkout and runs one wrapped
command for real, so the executing path -- build the wrap, hand it to `bash`,
read the result -- is exercised whatever the invented cases say.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "wrap-runtime.py"

ROOT = "/checkout"

EROFS = "bash: line 1: tests/test_pinned.py: Read-only file system"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("wrap_runtime_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _done(code: int, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    """One finished process, as `judge` reads one."""
    return subprocess.CompletedProcess(args=["bash"], returncode=code, stdout=out, stderr=err)


def _answered(
    **changed: subprocess.CompletedProcess[str],
) -> dict[str, subprocess.CompletedProcess[str]]:
    """The four probes as they answer in a sandbox that holds, with overrides."""
    good: dict[str, subprocess.CompletedProcess[str]] = {
        "runs": _done(0, ROOT + "\n"),
        "nested": _done(0, "fixture\n"),
        "pinned": _done(1, "", EROFS),
        "writable": _done(0),
    }
    good.update(changed)
    return good


def _live() -> bool:
    """One real wrapped command, built by the live hook and run by `bash`."""
    wrap = GATE._load("bwrap-wrap")
    lane_config = GATE._load("lane_config", GATE.LIB)
    if GATE._load("bwrap_probe", GATE.LIB).bwrap_fault() is not None:
        return False
    with tempfile.TemporaryDirectory() as name:
        root = Path(name).resolve()
        GATE.checkout(root, lane_config.tests_dir())
        done = GATE.run(wrap.wrap("pwd", str(root), ""))
    return bool(done.returncode == 0 and done.stdout.strip() == str(root))


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    dead = GATE.judge(ROOT, _answered(runs=_done(1, "", "bwrap: No permissions")))
    flat = GATE.judge(ROOT, _answered(nested=_done(1, "", "cat: no such file")))
    loose = GATE.judge(ROOT, _answered(pinned=_done(0)))
    sealed = GATE.judge(ROOT, _answered(writable=_done(1, "", EROFS)))
    every = GATE.judge(ROOT, _answered(pinned=_done(0), writable=_done(1, "", EROFS)))
    return {
        "a sandbox that holds every rule passes": GATE.judge(ROOT, _answered()) == [],
        "a wrap that does not exec fails, quoting what refused it": (
            len(dead) == 1 and "No permissions" in dead[0]
        ),
        "a nested wrap that lost the outer scratch fails": (
            len(flat) == 1 and "nested wrap" in flat[0]
        ),
        "a collected test file a shell can rewrite fails": (
            len(loose) == 1 and "rewrote a collected test file" in loose[0]
        ),
        "a sandbox that refuses every write fails too": (
            len(sealed) == 1 and "cannot write beside the lane" in sealed[0]
        ),
        "every rule is read every run, never one failure at a time": len(every) == 2,
        "the live hook's wrap runs, and prints the checkout it was pointed at": _live(),
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
