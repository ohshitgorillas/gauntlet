#!/usr/bin/env python3
"""The `--self-test` body of `blind-no-shell.py`: one line per rule the gate holds.

Each rule builds a throwaway tree beside the real one: the real hook and the
real agent definitions copied in, then one definition changed. So the rule that
`Bash` on the arbiter fails is read against the arbiter as it ships, not against
an invented file that happens to agree with the gate.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "blind-no-shell.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("blind_no_shell_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()


def _tree(change: Callable[[Path], None]) -> list[str]:
    """The gate's findings over a copy of the real kit with one change made."""
    with tempfile.TemporaryDirectory() as scratch:
        root = Path(scratch)
        (root / "hooks").mkdir()
        shutil.copy(GATE.ROOT / GATE.HOOK, root / GATE.HOOK)
        shutil.copytree(GATE.ROOT / GATE.AGENTS, root / GATE.AGENTS)
        change(root)
        return list(GATE.audit(root))


def _grant(name: str, extra: str) -> Callable[[Path], None]:
    """A change that adds one tool to one agent's `tools:` line."""

    def change(root: Path) -> None:
        path = root / GATE.AGENTS / f"{name}.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text.replace("\ntools: ", f"\ntools: {extra}, ", 1), encoding="utf-8")

    return change


def _drop_tools(root: Path) -> None:
    path = root / GATE.AGENTS / "juror.md"
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text("".join(line for line in lines if not line.startswith("tools:")))


def _drop_definition(root: Path) -> None:
    (root / GATE.AGENTS / "auditor.md").unlink()


def _drop_tuple(root: Path) -> None:
    path = root / GATE.HOOK
    path.write_text(path.read_text(encoding="utf-8").replace("BLIND = (", "SEEING = ("))


def _unchanged(root: Path) -> None:
    del root


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    shell = _tree(_grant("arbiter", "Bash"))
    scoped = _tree(_grant("scrivener", "Bash(git log:*)"))
    pair = _tree(_grant("bailiff", "mcp__plugin_gauntlet_pair__merge"))
    wildcard = _tree(_grant("juror", "mcp__plugin_gauntlet_pair__*"))
    untooled = _tree(_drop_tools)
    missing = _tree(_drop_definition)
    return {
        "the tree as it ships passes": _tree(_unchanged) == [] and GATE.audit() == [],
        "Bash re-added to the arbiter fails, naming the arbiter": (
            len(shell) == 1 and "arbiter.md" in shell[0] and "Bash" in shell[0]
        ),
        "a scoped Bash grant fails too": len(scoped) == 1 and "scrivener.md" in scoped[0],
        "a pair server tool fails": len(pair) == 1 and "bailiff.md" in pair[0],
        "a pair server wildcard fails": len(wildcard) == 1 and "juror.md" in wildcard[0],
        "a blind server tool passes": _tree(_grant("juror", "mcp__plugin_gauntlet_blind__show"))
        == [],
        "a definition with no tools line fails": len(untooled) == 1 and "juror.md" in untooled[0],
        "a blind name with no definition fails": len(missing) == 1 and "auditor" in missing[0],
        "a hook with no BLIND tuple fails rather than holding nobody": len(_tree(_drop_tuple)) == 1,
        "the tuple is read from the hook, all five names": GATE.blind(
            (GATE.ROOT / GATE.HOOK).read_text(encoding="utf-8")
        )
        == ["arbiter", "scrivener", "juror", "bailiff", "auditor"],
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
