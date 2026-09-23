#!/usr/bin/env python3
"""The `--self-test` body of `hook-latency.py`: one line per rule the gate holds.

The ceilings are read against invented readings, so each rule is exercised
without waiting on a real hook. Two rules are not invented: the manifest is
parsed as it ships, and one wired hook is timed for real, because a gate whose
measuring path raises reports nothing at all.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "hook-latency.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("hook_latency_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

#: a reading well under both ceilings
QUICK = 50.0


def _measures() -> bool:
    """One wired hook, timed for real, answers with a positive number of milliseconds."""
    wired = GATE.commands()
    return bool(wired) and GATE.fastest(wired[0][1], GATE.ROOT, 1) > 0


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    quick = [("PreToolUse", "a.py", QUICK), ("PreToolUse", "b.py", QUICK)]
    slow = [("PreToolUse", "a.py", GATE.PER_HOOK_MS + 1.0)]
    chain = [("PreToolUse", f"h{n}.py", GATE.PER_HOOK_MS - 1.0) for n in range(3)]
    both = [("PreToolUse", f"h{n}.py", GATE.PER_HOOK_MS + 1.0) for n in range(3)]
    split = [("PreToolUse", "a.py", QUICK), ("Stop", "b.py", GATE.PER_HOOK_MS + 1.0)]
    return {
        "a chain inside both ceilings passes": GATE.judge(quick) == [],
        "one hook over the per-hook ceiling fails, named": (
            len(GATE.judge(slow)) == 1 and "a.py" in GATE.judge(slow)[0]
        ),
        "hooks that are each quick but slow together fail as a chain": (
            len(GATE.judge(chain)) == 1 and "the whole chain" in GATE.judge(chain)[0]
        ),
        "an event's chain is summed over that event alone": len(GATE.judge(split)) == 1,
        "every rule is read every run, never one failure at a time": (len(GATE.judge(both)) == 4),
        "the manifest's wired commands are read, and there are some": (
            len(GATE.commands()) > 0
            and all(event and command for event, command in GATE.commands())
        ),
        "a wired command is timed for real, not assumed": _measures(),
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
