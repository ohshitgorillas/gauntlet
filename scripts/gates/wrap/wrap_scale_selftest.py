#!/usr/bin/env python3
"""The `--self-test` body of `wrap-scale.py`: one line per rule the gate holds.

The gate's `--check` measures the live hook. This body measures the gate: the
three rules are handed numbers directly, so a rule that stopped firing is caught
here rather than by a green report on a small checkout.

One case is not invented. The last rule builds a real checkout and asks the live
hook for a wrap, so the measuring path itself -- import the hyphenated module,
write a lane, read a string back -- is exercised whether or not the numbers it
returns are in bounds. A gate whose measurement raises reports nothing at all.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "wrap-scale.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("wrap_scale_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

#: a wrap that is flat, small and sparsely bound: every rule holds
FLAT = 4096


def _measures() -> bool:
    """The live measuring path returns a positive size and a positive bind count."""
    with tempfile.TemporaryDirectory():
        chars, binds = GATE.measure(1)
    return bool(chars > 0 and binds > 0)


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    over = GATE.judge(GATE.MAX_COMMAND + 1, GATE.MAX_COMMAND + 1, 1)
    grows = GATE.judge(FLAT, FLAT + 1, 1)
    mounts = GATE.judge(FLAT, FLAT, GATE.MAX_BINDS + 1)
    every = GATE.judge(FLAT, GATE.MAX_COMMAND + 1, GATE.MAX_BINDS + 1)
    return {
        "a flat wrap under both ceilings passes": GATE.judge(FLAT, FLAT, 1) == [],
        "a wrap over the character ceiling fails, naming E2BIG": (
            len(over) == 1 and "E2BIG" in over[0]
        ),
        "a wrap that grows with the checkout fails, at any size": (
            len(grows) == 1 and "grows with the checkout" in grows[0]
        ),
        "a mount table over the bind ceiling fails": (
            len(mounts) == 1 and "binds" in mounts[0] and str(GATE.MAX_BINDS) in mounts[0]
        ),
        "every rule is read every run, never one failure at a time": len(every) == 3,
        "the ceiling leaves the kernel room for the command and the environment": (
            GATE.MAX_COMMAND * 4 <= 128 * 1024
        ),
        "the live hook is measured, not an invented profile": _measures(),
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
