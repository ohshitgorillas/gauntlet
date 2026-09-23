#!/usr/bin/env python3
"""The `--self-test` body of `consumer-smoke.py`: one line per rule it holds.

`judge` is read against invented answers, so the crash rule, the readability
rule, the held-turn rule and the lane rule are each exercised on their own. Two
rules are not invented: the kit is installed into a scratch directory and read
back, and the whole session is driven, because a gate whose driving path raises
reports nothing at all.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "consumer-smoke.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("consumer_smoke_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

#: a refusal, as a hook prints one
DENY = json.dumps(
    {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "the tests lane is the scrivener's",
        }
    }
)


def done(code: int, out: str = "", err: str = "") -> subprocess.CompletedProcess[str]:
    """One finished hook, as the driver hands them to `judge`."""
    return subprocess.CompletedProcess(args=["hook"], returncode=code, stdout=out, stderr=err)


#: a whole session in which every hook behaved
SOUND = [
    ("SessionStart", "hooks/kit-probe.py", done(0)),
    ("PreToolUse", "hooks/lanes.py", done(0)),
    ("Stop", "hooks/lanes.py --stop", done(0)),
]

#: the refusal the tests lane gives, as the lane step reads it
REFUSED = [done(0, DENY)]


def _listing(names: list[str]) -> str:
    """A `tools/list` reply naming these tools, as a server's stdout carries one."""
    tools = [{"name": name, "description": "", "inputSchema": {}} for name in names]
    return json.dumps({"jsonrpc": "2.0", "id": 2, "result": {"tools": tools}}) + "\n"


def _installed() -> bool:
    """The kit copies into a directory of its own, carrying its manifest and hooks."""
    with tempfile.TemporaryDirectory(prefix="consumer-self-") as base:
        kit = GATE.install(Path(base))
        root = GATE.project(Path(base))
        return (
            (kit / GATE.MANIFEST).is_file()
            and (kit / "hooks" / "lanes.py").is_file()
            and not (kit / "tests").exists()
            and (root / "tests").is_dir()
            and not (root / "gauntlet").exists()
            and len(GATE.wired(kit)) > 0
        )


def _drives() -> bool:
    """One session runs through one installed kit, and nothing is wrong with it."""
    with tempfile.TemporaryDirectory(prefix="consumer-live-") as base:
        return bool(GATE.readings(Path(base)) == [])


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    fell = done(1, "", GATE.CRASH + "\nKeyError: x\n")
    crash = GATE.judge([("Stop", "hooks/lanes.py", fell)], REFUSED)
    noise = GATE.judge([("PreToolUse", "hooks/lanes.py", done(0, "about to deny\n"))], REFUSED)
    held = GATE.judge([("Stop", "hooks/lanes.py --stop", done(2, "", "no verdict"))], REFUSED)
    allowed = GATE.judge(SOUND, [done(0)])
    server_fell = done(1, "", GATE.CRASH + "\nKeyError: x\n")
    server_crash = GATE.judge_servers([("blind", ["x"], server_fell)], {"blind": {"status"}})
    server_silent = GATE.judge_servers([("blind", ["x"], done(0, ""))], {"blind": {"status"}})
    server_empty = GATE.judge_servers(
        [("blind", ["x"], done(0, _listing([])))], {"blind": {"status"}}
    )
    server_absent = GATE.judge_servers(
        [("blind", ["x"], done(0, _listing(["ping"])))], {"blind": {"status"}}
    )
    server_sound = GATE.judge_servers(
        [("blind", ["x"], done(0, _listing(["status"])))], {"blind": {"status"}}
    )
    return {
        "a session in which every hook behaved passes": GATE.judge(SOUND, REFUSED) == [],
        "a hook that crashed fails, quoting its last line": (
            len(crash) == 1 and "KeyError: x" in crash[0]
        ),
        "output the host cannot read fails": (len(noise) == 1 and "cannot read" in noise[0]),
        "a Stop gate that holds a fresh project fails": (
            len(held) == 1 and "writes no spec" in held[0]
        ),
        "a tests write the kit allows in a consumer project fails": (
            len(allowed) == 1 and "holds in this repository and nowhere else" in allowed[0]
        ),
        "the session carries a start, a prompt, both tool sides and a stop": (
            {event for event, _ in GATE.STEPS}
            == {"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"}
        ),
        "the lane step names the consumer's own tests directory": (
            "/tests/" in GATE.lane_step("/somewhere")[1]["tool_input"]["file_path"]
        ),
        "the kit installs into a project holding none of this one's history": _installed(),
        "the session is driven through the installed kit, not assumed": _drives(),
        "a server that crashed fails, quoting its last line": (
            len(server_crash) == 1 and "KeyError: x" in server_crash[0]
        ),
        "a server giving no answer to tools/list fails": (
            len(server_silent) == 1 and "tools/list" in server_silent[0]
        ),
        "a server whose tools/list answers with no tools fails": (
            len(server_empty) == 1 and "no tools" in server_empty[0]
        ),
        "a server whose tools/list omits a granted tool fails, naming it": (
            len(server_absent) == 1 and "status" in server_absent[0]
        ),
        "a server whose tools/list covers every granted tool passes": server_sound == [],
        "a wildcard grant names no one tool": (
            "*" not in {tool for tools in GATE.granted(GATE.ROOT).values() for tool in tools}
        ),
        "the live agents grant tools this kit's own MCP servers actually serve": bool(
            GATE.granted(GATE.ROOT)
        ),
        "the live manifest's MCP servers each build a runnable argv": (
            len(GATE.served(GATE.ROOT)) >= 1
            and all(argv for argv in GATE.served(GATE.ROOT).values())
        ),
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
