#!/usr/bin/env python3
"""The `--self-test` body of `wrap-concurrency.py`: one line per rule it holds.

`judge` is read against invented processes, so the bleed rule, the sharing
rule, the cross-tree rule and the race rule are each exercised on their own.
Two rules are not invented: the two trees are built and checked for what makes
them two trees, and one wrap is run for real, because a gate whose driving path
raises reports nothing at all.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "wrap-concurrency.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("wrap_concurrency_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def done(code: int, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    """One finished process, as the probes hand them to `judge`."""
    return subprocess.CompletedProcess(args=["bwrap"], returncode=code, stdout=out, stderr=err)


#: the answers a sound pair of sessions gives
SOUND = {
    "shared": done(0, GATE.WORD + "\n"),
    "bleed": done(1, "", f"cat: /tmp/{GATE.TOKEN}: No such file or directory"),
    "cross": done(1, "", f"bash: line 1: crossed.py: {GATE.EROFS}"),
}

#: eight wraps that all started and all finished
WON = [done(0, "/tree\n") for _ in range(GATE.RACERS)]


def _answers(
    **changed: subprocess.CompletedProcess[str],
) -> dict[str, subprocess.CompletedProcess[str]]:
    """The sound answers with one probe replaced."""
    return {**SOUND, **changed}


def _built() -> bool:
    """Two trees, side by side under one main checkout, each a checkout itself."""
    with tempfile.TemporaryDirectory(dir=GATE.BASE, prefix="races-self-") as base:
        one, other = GATE.trees(Path(base).resolve())
        return (
            one != other
            and Path(one).parent == Path(other).parent
            and Path(one).parent.name == "worktrees"
            and Path(one, ".git").exists()
            and Path(other, ".git").exists()
        )


def _drives() -> bool:
    """One real wrap at one real tree answers with that tree's own path."""
    wrap = GATE._load("bwrap-wrap")
    with tempfile.TemporaryDirectory(dir=GATE.BASE, prefix="races-live-") as base:
        one, _ = GATE.trees(Path(base).resolve())
        answered = GATE.run(wrap.wrap("pwd", one, ""))
        return bool(answered.returncode == 0 and answered.stdout.strip() == one)


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    lost = GATE.judge(SOUND, [done(1, "", "bwrap: No such file or directory"), *WON[1:]])
    unshared = GATE.judge(_answers(shared=done(1, "", "cat: no such file")), WON)
    bled = GATE.judge(_answers(bleed=done(0, GATE.WORD + "\n")), WON)
    wrote = GATE.judge(_answers(cross=done(0)), WON)
    other_fault = GATE.judge(_answers(cross=done(1, "", "bash: line 1: disk quota exceeded")), WON)
    return {
        "two sound sessions pass": GATE.judge(SOUND, WON) == [],
        "a tree that cannot read its own scratch fails": (
            len(unshared) == 1 and "scratch directory of its own" in unshared[0]
        ),
        "one tree reading the other's scratch fails": (
            len(bled) == 1 and "believes is private" in bled[0]
        ),
        "a cross-tree write that lands fails": (
            len(wrote) == 1 and "writable set is not its own" in wrote[0]
        ),
        "a cross-tree write refused for another reason fails too": len(other_fault) == 1,
        "a wrap that lost the race fails, counted": (
            len(lost) == 1 and f"1 of {GATE.RACERS}" in lost[0]
        ),
        "the race starts more wraps than it runs at a time": GATE.RACERS > GATE.WORKERS,
        "two trees are built side by side, not spelled": _built(),
        "a wrap is run for real, not assumed": _drives(),
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
