#!/usr/bin/env python3
"""The `--self-test` body of `kit-live.py`: one line per rule the gate holds.

The wiring rules are read against real manifests written into throwaway trees.
The process rules are handed finished processes, so each is read on its own: a
gate whose three rules collapsed into one is caught here rather than by a report
that was green because the probe happened to behave.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from typing import Any

GATE_PATH = Path(__file__).resolve().parent / "kit-live.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("kit_live_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

#: one entry wiring the probe, as the manifest spells one
ENTRY = {"type": "command", "command": f'python3 "${{CLAUDE_PLUGIN_ROOT}}"/{GATE.PROBE}'}

#: an entry wiring something else at the same event
OTHER = {"type": "command", "command": 'python3 "${CLAUDE_PLUGIN_ROOT}"/hooks/gauntlet-off.py'}


def _wiring(groups: list[dict[str, Any]] | None) -> list[str]:
    """What the gate says about a manifest whose SessionStart holds these groups."""
    hooks: dict[str, Any] = {} if groups is None else {"SessionStart": groups}
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        (root / GATE.MANIFEST).parent.mkdir(parents=True)
        (root / GATE.MANIFEST).write_text(json.dumps({"hooks": hooks}), encoding="utf-8")
        return list(GATE.wiring_problems(root))


def _done(code: int, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    """One finished process, as `judge` reads one."""
    return subprocess.CompletedProcess(args=["probe"], returncode=code, stdout=out, stderr=err)


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    named = _done(0, f"gauntlet: 1 wired hook(s) absent from this kit: {GATE.ABSENT}.")
    nothing = _wiring(None)
    matched = _wiring([{"matcher": "Bash", "hooks": [ENTRY]}])
    elsewhere = _wiring([{"hooks": [OTHER]}])
    silent = GATE.judge(_done(0, ""), _done(0))
    failed = GATE.judge(named, _done(0))
    noisy = GATE.judge(named, _done(0, "gauntlet: ready"))
    return {
        "a probe wired bare at SessionStart passes": _wiring([{"hooks": [ENTRY]}]) == [],
        "a probe wired beside another hook passes": _wiring([{"hooks": [OTHER, ENTRY]}]) == [],
        "a SessionStart with nothing wired fails": (
            len(nothing) == 1 and "nothing is wired" in nothing[0]
        ),
        "a SessionStart wiring other hooks but not the probe fails": (
            len(elsewhere) == 1 and "is not wired at SessionStart" in elsewhere[0]
        ),
        "a probe wired under a matcher fails": (
            len(matched) == 1 and "carries a matcher" in matched[0]
        ),
        "a probe silent about an incomplete kit fails": (
            len(silent) == 1 and "did not name" in silent[0]
        ),
        "a probe that exits non-zero fails, whatever it printed": (
            len(GATE.judge(_done(1, named.stdout), _done(0))) == 1
        ),
        "a probe that speaks about a whole kit fails": (
            len(noisy) == 1 and "spoke about a whole kit" in noisy[0]
        ),
        "a probe that names the absent hook and is otherwise silent passes": failed == [],
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
