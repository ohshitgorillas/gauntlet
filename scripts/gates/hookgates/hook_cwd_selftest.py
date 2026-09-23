#!/usr/bin/env python3
"""The `--self-test` body of `hook-cwd.py`: one line per rule the gate holds.

`judge` is read against invented answers, so the hole rule, the reach rule and
the crash rule are each exercised on their own. Two rules are not invented: the
five working directories are built and checked for what makes each one that
shape, and the real lane hook is driven from one of them, because a gate whose
driving path raises reports nothing at all.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "hook-cwd.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("hook_cwd_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

#: what a refusal looks like on the way out
DENY = (
    json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": "the tests lane is the scrivener's",
            }
        }
    ),
    "",
)

#: what letting a call through looks like
PASS = ("", "")

#: what a crashing hook leaves on stderr
CRASHED = ("", f'{GATE.CRASH}:\n  File "hooks/lanes.py", line 1\nValueError: no\n')


def _built() -> bool:
    """The five shapes are directories on disk, each one what its name says."""
    with tempfile.TemporaryDirectory(prefix="hook-cwd-self-") as base:
        built = GATE.shapes(Path(base))
        if len(built) != 5 or not all(Path(cwd).is_dir() for cwd, _ in built.values()):
            return False
        link = built["a route through a symlink"][0]
        detached = built["a checkout at a detached head"][0]
        loose = built["a directory that is no checkout"][0]
        return (
            Path(link).is_symlink()
            and Path(detached, ".git").exists()
            and not Path(loose, ".git").exists()
        )


def _drives() -> bool:
    """The real lane hook, driven from one built shape, refuses the lane write."""
    with tempfile.TemporaryDirectory(prefix="hook-cwd-live-") as base:
        cwd, prefix = GATE.shapes(Path(base))["a worktree the chain cut"]
        lane = f"{prefix}{GATE.lane_config.tests_dir()}/{GATE.LEAF}"
        return bool(GATE.denied(GATE.answer(cwd, lane)))


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    hole = GATE.judge("shape", PASS, PASS)
    reach = GATE.judge("shape", DENY, DENY)
    crash = GATE.judge("shape", CRASHED, PASS)
    hang = GATE.judge("shape", ("", f"did not answer in {GATE.TIMEOUT}s"), PASS)
    return {
        "a lane refused and a neighbour allowed is the shape that passes": (
            GATE.judge("shape", DENY, PASS) == []
        ),
        "a write into the lane that is allowed fails, named": (
            len(hole) == 1 and "does not hold here" in hole[0] and "shape" in hole[0]
        ),
        "a write beside the lane that is refused fails": (
            len(reach) == 1 and "reaches too far" in reach[0]
        ),
        "a traceback fails, quoting its last line": (
            len(crash) == 1 and "ValueError: no" in crash[0]
        ),
        "a hook that never answers fails": len(hang) == 1 and "crash" in hang[0],
        "an answer that is not JSON is no refusal": not GATE.denied(("not json", "")),
        "the five working directories are built, not spelled": _built(),
        "the lane hook is driven from a built shape, not assumed": _drives(),
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
