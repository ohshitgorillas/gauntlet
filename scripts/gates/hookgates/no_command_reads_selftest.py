#!/usr/bin/env python3
"""The `--self-test` body of `no-command-reads.py`: one line per rule the gate holds.

The static leg is read against fixture modules of each shape, each a few lines
of source judged under the path it would sit at: a sample payload that passes,
a hook that reads the command and fails, and the wrap hook's own shape with one
forbidden use swapped in at a time. The behavioral leg's judge is read against
invented answers, and one wired hook is driven for real, because a gate whose
driving path raises reports nothing at all.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "no-command-reads.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("no_command_reads_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

HOOK = "hooks/some-hook.py"

#: sample payloads as a selftest spells them: literals, never subscripts
SAMPLES = """
PAYLOAD = '{"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}'
CALL = {"tool_name": "Bash", "tool_input": {"command": "pwd"}}
def server(entry):
    return entry.get("command", "")
"""

#: a hook that decides a call by what its command says
READER = """
def verdict(name, tool_input, payload):
    command = tool_input.get("command")
    if "rm" in command:
        return "no"
"""

#: the same read, reached through a name bound from the payload
DERIVED = """
def verdict(payload):
    got = payload.get("tool_input") or {}
    return got["command"]
"""

#: the wrap hook's shape: one read, one guard, one hand-off, one here-document
WRAPPED = """
import re
def _answer(payload):
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str):
        return None
    return wrap(command, "/", "")
def wrap(command, root, agent):
    return "bwrap " + _heredoc(command)
def _heredoc(command):
    return f"<<'EOF'\\n{command}\\nEOF"
"""

#: a hook that tokenizes the command it was handed
SPLITTER = """
import shlex
def verdict(name, tool_input, payload):
    words = shlex.split(tool_input.get("command", ""))
    return "no" if "rm" in words else None
"""

#: a module that tokenizes a runner line it read from a config file
CONFIGURED = """
import json
import shlex
from pathlib import Path
def runner(path):
    conf = json.loads(Path(path).read_text())
    return shlex.split(conf.get("pytest_command", ""))
"""

GUARD = "    if not isinstance(command, str):\n"

#: every use of the command the wrap hook may not make, swapped in for the guard
FORBIDDEN = {
    "in": '    if "rm" in command:\n',
    "split": "    if command.split():\n",
    "startswith": '    if command.startswith("sudo"):\n',
    "==": '    if command == "pwd":\n',
    "re": '    if re.match("x", command):\n',
    "f-string": '    if f"{command}":\n',
    "slicing": "    if command[:3]:\n",
}


def _wrap_with(line: str) -> list[str]:
    return list(GATE.judge(GATE.WRAP, WRAPPED.replace(GUARD, line)))


def _answer(command: str) -> tuple[str, str]:
    """A wrap hook's answer to `command`, as the real one shapes it."""
    body = f"bwrap --ro-bind / / -- bash -s <<'GAUNTLET_COMMAND_EOF'\\n{command}\\nX"
    return '{"hookSpecificOutput": {"updatedInput": {"command": "' + body + '"}}}', ""


def _drives() -> bool:
    """The wired Bash hook, driven for real, answers two texts alike for one caller."""
    hooks = GATE.bash_hooks()
    if not hooks:
        return False
    answer = GATE._load("hook-degenerate").answer
    said = {
        name: GATE.normalize(text, answer(hooks[0], GATE.payload(text, "juror"), GATE.ROOT))
        for name, text in (("sudo", "sudo ls"), ("pwd", "pwd"))
    }
    return bool(GATE.judge_answers(hooks[0], "juror", said) == [] and said["pwd"][0])


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    forbidden = {name: _wrap_with(line) for name, line in FORBIDDEN.items()}
    same = {text: GATE.normalize(text, _answer(text)) for text in ("pwd", "sudo ls", "")}
    differ = {"pwd": ("allow", ""), "sudo": ("deny", "")}
    split = GATE.judge_answers("hooks/x.py", "arbiter", differ)
    twice = WRAPPED.replace("_heredoc(command)", "_heredoc(command) + _heredoc(command)")
    return {
        "sample payloads and a manifest entry pass": GATE.judge(HOOK, SAMPLES) == [],
        "a hook that reads tool_input's command fails": len(GATE.judge(HOOK, READER)) == 1,
        "a read through a name bound from tool_input fails": len(GATE.judge(HOOK, DERIVED)) == 1,
        "the wrap shape passes: an isinstance test and one call into _heredoc": (
            GATE.judge(GATE.WRAP, WRAPPED) == []
        ),
        "the wrap shape outside the wrap hook fails": len(GATE.judge(HOOK, WRAPPED)) == 1,
        "every forbidden use of the command in the wrap hook fails": all(
            len(found) == 1 for found in forbidden.values()
        ),
        "a second call into _heredoc fails": len(GATE.judge(GATE.WRAP, twice)) == 1,
        "a read bound to no name fails in the wrap hook": (
            len(
                GATE.judge(
                    GATE.WRAP,
                    WRAPPED.replace(
                        "return wrap(command,", "return wrap(payload['tool_input']['command'],"
                    ),
                )
            )
            >= 1
        ),
        "a hook that runs shlex.split on the command fails": len(GATE.judge(HOOK, SPLITTER)) >= 1
        and any("shlex" in found for found in GATE.judge(HOOK, SPLITTER)),
        "shlex.split on a string read from a config file passes": (
            GATE.judge(HOOK, CONFIGURED) == []
        ),
        "the real wrap hook passes the static leg": GATE.judge(
            GATE.WRAP, (GATE.ROOT / GATE.WRAP).read_text(encoding="utf-8")
        )
        == [],
        "answers alike once the text and here-document are out pass": (
            GATE.judge_answers("hooks/x.py", "", same) == []
        ),
        "two texts answered differently fail, naming hook, caller and both texts": (
            len(split) == 1 and "x.py" in split[0] and "arbiter" in split[0] and "sudo" in split[0]
        ),
        "a matcher covers Bash by regex, and only then": (
            GATE.covers("Bash") and GATE.covers(None) and not GATE.covers("Read|Grep")
        ),
        "the manifest's Bash hooks are read": any(
            "bwrap-wrap.py" in hook for hook in GATE.bash_hooks()
        ),
        "the wired Bash hook is driven for real, not assumed": _drives(),
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
