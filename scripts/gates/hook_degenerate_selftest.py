#!/usr/bin/env python3
"""The `--self-test` body of `hook-degenerate.py`: one line per rule the gate holds.

`judge` is read against invented answers, so the crash rule and the hang rule
are each exercised on their own. Two rules are not invented: the table is
checked for the shapes it exists to carry, and one wired hook is driven with one
real payload, because a gate whose driving path raises reports nothing at all.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "hook-degenerate.py"

COMMAND = 'python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/lanes.py'


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("hook_degenerate_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

#: what a crashing hook leaves on stderr
CRASHED = f'{GATE.CRASH}:\n  File "hooks/lanes.py", line 1\nValueError: no\n'


def _drives() -> bool:
    """One wired hook, driven with one real payload, answers without crashing."""
    wired = GATE.commands()
    if not wired:
        return False
    said = GATE.answer(wired[0], GATE.PAYLOADS["an empty object"], GATE.ROOT)
    return bool(GATE.judge(wired[0], "an empty object", said) == [])


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    crash = GATE.judge(COMMAND, "not JSON", ("", CRASHED))
    on_stdout = GATE.judge(COMMAND, "not JSON", (CRASHED, ""))
    hang = GATE.judge(COMMAND, "not JSON", ("", f"did not answer in {GATE.TIMEOUT}s"))
    refusal = GATE.judge(COMMAND, "not JSON", ('{"decision": "deny"}', "some warning\n"))
    return {
        "a hook that refuses is not a failure": refusal == [],
        "a hook that says nothing is not a failure": GATE.judge(COMMAND, "x", ("", "")) == [],
        "a traceback on stderr fails, quoting its last line": (
            len(crash) == 1 and "ValueError: no" in crash[0] and "lanes.py" in crash[0]
        ),
        "a traceback on stdout fails too": len(on_stdout) == 1,
        "a hook that never answers fails": len(hang) == 1 and "did not answer" in hang[0],
        "the table carries a truncated payload, a wrong type and an oversized one": (
            "not JSON" in GATE.PAYLOADS
            and "a tool_input that is a string" in GATE.PAYLOADS
            and len(GATE.PAYLOADS["a command of a megabyte"]) > 1024 * 1024
        ),
        "the manifest's wired commands are read, once each": (
            len(GATE.commands()) == len(set(GATE.commands())) and len(GATE.commands()) > 0
        ),
        "a wired hook is driven for real, not assumed": _drives(),
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
