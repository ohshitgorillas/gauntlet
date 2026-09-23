"""The self-test of `blind-write.py`: one line per rule the hook holds.

`python3 hooks/blind-write.py --self-test` runs it, importing this module from
its own `--self-test` branch; nothing else here is wired to anything.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent / "lib"))

import hook_payload  # noqa: E402
import hook_shape  # noqa: E402

HOOKS = Path(__file__).resolve().parent
MANIFEST = HOOKS.parent / ".claude-plugin" / "plugin.json"


def _hook_module() -> Any:
    """The hook these lines judge: the running one when started there, else a fresh load."""
    running = sys.modules.get("blind-write")
    if running is not None:
        return running
    path = HOOKS / "blind-write.py"
    spec = importlib.util.spec_from_file_location("blind-write", path)
    if spec is None or spec.loader is None:  # pragma: no cover - a broken checkout
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["blind-write"] = module
    spec.loader.exec_module(module)
    return module


impl = _hook_module()
FORMAT = impl.GUARDS[0]


def _call(who: str | None, tool: str = FORMAT) -> str | None:
    payload: dict[str, Any] = {"cwd": str(HOOKS.parent)}
    if who is not None:
        payload["agent_type"] = who
    said: str | None = impl.verdict(tool, {"path": "tests/test_x.py"}, payload)
    return said


def _matchers() -> list[str]:
    """Every `PreToolUse` matcher the manifest wires this hook under."""
    wiring = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [
        str(group.get("matcher", ""))
        for group in wiring.get("hooks", {}).get("PreToolUse", [])
        if any("hooks/blind-write.py" in hook.get("command", "") for hook in group["hooks"])
    ]


def _rules() -> dict[str, bool]:
    denied, allowed = hook_shape.denied, hook_shape.allowed
    matchers = _matchers()
    others = ("arbiter", "bailiff", "juror", "auditor", "prosecutor", "detective", "examiner")
    return {
        "the scrivener is admitted": allowed(_call("scrivener")),
        "the plugin-namespaced scrivener is admitted": allowed(_call("gauntlet:scrivener")),
        "the main agent is denied": denied(_call(None)),
        "an empty agent_type is denied as the main agent": denied(_call("")),
        "every other kit agent is denied": all(denied(_call(name)) for name in others),
        "an agent from outside the kit is denied": denied(_call("general-purpose")),
        "a tool outside the server is not decided": allowed(_call("bailiff", "Write")),
        "the manifest wires it once, on a matcher naming the server": len(matchers) == 1
        and all(re.fullmatch(m, FORMAT) for m in matchers),
        "the matcher leaves the reading server alone": not any(
            re.fullmatch(m, "mcp__plugin_gauntlet_blind__test") for m in matchers
        ),
        "every hostile payload is survived, and an unreadable one refused": (
            hook_payload.survives_hostile_payloads(
                str(HOOKS / "blind-write.py"), guards=impl.GUARDS
            )
        ),
    }


def self_test() -> int:
    """Print one PASS or FAIL per rule; exit 1 if any failed."""
    return hook_shape.report(_rules())
