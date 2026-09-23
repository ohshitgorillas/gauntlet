#!/usr/bin/env python3
"""The `--self-test` body of `kit-shipped.py`: one line per rule the gate holds.

Each judge is read against invented descriptions, so the tracking rule, the
frontmatter rule, the roster rule, the blind-table rule and the version rule are
each exercised on their own. Two rules are not invented: the index is read as
git answers it, and the shipped kit is audited whole, because a gate whose
reading path raises reports nothing at all.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "kit-shipped.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("kit_shipped_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

#: one agent definition as the host reads it
DEFINITION = (
    "---\nname: juror\ndescription: rules on a run\ntools: Read\nmodel: sonnet\n---\n\nbody\n"
)

#: the paths a sound kit carries
CARRIED = {"hooks/lanes.py", "docs/agents.md", "agents/juror.md"}


def _untracked_prose() -> dict[str, set[str]]:
    """The paths the gate reads out of a git tree whose one document is untracked."""
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "init", "-q", tmp], check=True, capture_output=True, timeout=60)
        (Path(tmp) / "docs").mkdir()
        (Path(tmp) / "docs/new.md").write_text("See `hooks/gone.py`.\n", encoding="utf-8")
        found: dict[str, set[str]] = GATE.prose_paths(Path(tmp))
    return found


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    untracked = GATE.judge_paths(["hooks/gone.py"], {}, CARRIED)
    in_prose = GATE.judge_paths([], {"docs/agents.md": {"hooks/gone.py"}}, CARRIED)
    renamed = GATE.judge_agents(
        {"juror": DEFINITION.replace("name: juror", "name: bailiff")}, {"juror": set()}
    )
    orphan_row = GATE.judge_agents({}, {"juror": set()})
    orphan_file = GATE.judge_agents({"juror": DEFINITION}, {})
    headless = GATE.judge_agents({"juror": "no frontmatter here\n"}, {"juror": set()})
    partial = GATE.judge_agents({"juror": "---\nname: juror\n---\n"}, {"juror": set()})
    unlisted = GATE.judge_blind({"no-impl-reads": ("juror",)}, {"juror": set()})
    unheld = GATE.judge_blind({"no-impl-reads": ()}, {"juror": {"no-impl-reads"}})
    return {
        "a manifest path no commit carries fails": (
            len(untracked) == 1 and "hooks/gone.py" in untracked[0]
        ),
        "a path the prose names and no commit carries fails": (
            len(in_prose) == 1 and "docs/agents.md" in in_prose[0]
        ),
        "a kit whose descriptions all resolve passes": (
            GATE.judge_paths(["hooks/lanes.py"], {"docs/agents.md": {"agents/juror.md"}}, CARRIED)
            == []
            and GATE.judge_agents({"juror": DEFINITION}, {"juror": set()}) == []
            and GATE.judge_blind({"no-impl-reads": ("juror",)}, {"juror": {"no-impl-reads"}}) == []
        ),
        "frontmatter is read into its fields, and its absence is no fields": (
            (GATE.frontmatter(DEFINITION) or {}).get("model") == "sonnet"
            and GATE.frontmatter("body only\n") is None
        ),
        "a definition whose name and stem part fails": (
            len(renamed) == 1 and "bailiff" in renamed[0]
        ),
        "a definition missing a key the host reads fails, naming the keys": (
            len(partial) == 1 and "description" in partial[0] and "tools" in partial[0]
        ),
        "a definition with no frontmatter at all fails": len(headless) == 1,
        "a roster row with no definition fails, and a definition with no row too": (
            len(orphan_row) == 1 and len(orphan_file) == 1
        ),
        "a hook holding an agent the roster does not fails": (
            len(unlisted) == 1 and "does not say so" in unlisted[0]
        ),
        "a roster naming an agent the hook does not hold fails": (
            len(unheld) == 1 and "BLIND tuple does not" in unheld[0]
        ),
        "a version and a head that agree pass, and every other pairing fails": (
            GATE.judge_version("0.5.0", "0.5.0") == []
            and GATE.judge_version(None, None) == []
            and len(GATE.judge_version("0.5.0", "0.4.0")) == 1
            and len(GATE.judge_version(None, "0.5.0")) == 1
            and len(GATE.judge_version("0.5.0", None)) == 1
        ),
        "an untracked document is read for the paths it names": (
            _untracked_prose() == {"docs/new.md": {"hooks/gone.py"}}
        ),
        "the index is read as git answers it": (
            GATE.MANIFEST in GATE.tracked() and "hooks/lanes.py" in GATE.tracked()
        ),
        "the shipped kit is audited whole, not assumed": GATE.audit() == [],
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
