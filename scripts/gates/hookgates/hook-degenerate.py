#!/usr/bin/env python3
"""Gate: no wired hook answers a hostile payload with a traceback.

    scripts/gates/hookgates/hook-degenerate.py [--check]
    scripts/gates/hookgates/hook-degenerate.py --self-test

A hook stands between the agent and a tool call, and what reaches it is whatever
the host sends. The shapes in `PAYLOADS` are the ones that arrive when something
upstream is wrong: a truncated payload, a field of the wrong type, a working
directory that has been cut, a command of a megabyte. Each hook has prose about
refusing what it cannot decide, and prose is not a check.

A traceback is the failure this names. It is not a denial the agent can read, it
is not silence, and on a `Stop` hook it is a turn held open by a crash. So the
rule is one line long: for every wired command and every payload in the table,
the process finishes inside `TIMEOUT` and prints no traceback.

Exit status is deliberately not a rule. A hook that refuses a call and a hook
that crashes can both exit 1, and reading the status would either miss the crash
or refuse the refusal. What separates them is the traceback on stderr.

The commands come from the manifest, so a lane wired later is exercised against
the whole table without this file changing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

MANIFEST = ".claude-plugin/plugin.json"

#: a hook that has not answered this hostile payload by now will not
TIMEOUT = 30

#: what a crash looks like on the way out
CRASH = "Traceback (most recent call last)"

#: the payload shapes that arrive when something upstream is wrong. Each is the
#: raw bytes of stdin, because half of these never become an object at all.
PAYLOADS: dict[str, str] = {
    "nothing at all": "",
    "whitespace": "   \n",
    "not JSON": "{",
    "JSON that is not an object": "[1, 2, 3]",
    "an empty object": "{}",
    "a null tool_name": json.dumps({"tool_name": None, "tool_input": {}}),
    "a tool_name that is a list": json.dumps({"tool_name": ["Bash"], "tool_input": {}}),
    "a tool_input that is a string": json.dumps({"tool_name": "Bash", "tool_input": "pwd"}),
    "a command that is a number": json.dumps({"tool_name": "Bash", "tool_input": {"command": 7}}),
    "a cwd that is not there": json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "pwd"}, "cwd": "/nowhere/at/all"}
    ),
    "an agent_type that is an object": json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "pwd"}, "agent_type": {"name": "juror"}}
    ),
    "a command of a megabyte": json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "echo " + "x" * 1024 * 1024}}
    ),
    "a command of control bytes and scripts": json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": "echo ‮\u0007﻿ مرحبا \t\r\n"}}
    ),
    "a file_path that is a directory": json.dumps(
        {"tool_name": "Write", "tool_input": {"file_path": "/", "content": ""}}
    ),
    "a deeply nested tool_input": json.dumps(
        {"tool_name": "Write", "tool_input": json.loads('{"a":' * 60 + "1" + "}" * 60)}
    ),
}


def commands(root: Path = ROOT) -> list[str]:
    """Every wired hook command, in the order the manifest lists them, once each."""
    try:
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return []
    found = [
        entry["command"]
        for listed in hooks.values()
        for group in listed
        for entry in group.get("hooks", [])
        if isinstance(entry, dict) and isinstance(entry.get("command"), str)
    ]
    return list(dict.fromkeys(found))


def _argv(command: str, root: Path) -> list[str]:
    """One wired command as an argument list, with the plugin root filled in."""
    for spelling in ('"${CLAUDE_PLUGIN_ROOT}"', "${CLAUDE_PLUGIN_ROOT}"):
        command = command.replace(spelling, str(root))
    for spelling in ('"${CLAUDE_PROJECT_DIR}"', "${CLAUDE_PROJECT_DIR}"):
        command = command.replace(spelling, str(root))
    parts = command.split()
    return [sys.executable if parts[0] == "python3" else parts[0], *parts[1:]]


def answer(command: str, payload: str, root: Path = ROOT) -> tuple[str, str]:
    """What one wired command says about one payload: `(stdout, stderr)`.

    A hook that does not finish is reported as a crash of its own kind, since a
    hook that never returns is a tool call that never happens.
    """
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    environment["CLAUDE_PLUGIN_ROOT"] = str(root)
    try:
        done = subprocess.run(
            _argv(command, root),
            input=payload,
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return "", f"did not answer in {TIMEOUT}s"
    return done.stdout, done.stderr


def judge(command: str, name: str, said: tuple[str, str]) -> list[str]:
    """Why one answer to one payload cannot stand, if it cannot."""
    out, err = said
    if CRASH in out or CRASH in err:
        last = (err or out).strip().splitlines()[-1]
        return [f"{command.rsplit('/', 1)[-1]} on {name}: traceback, {last!r}"]
    if err.startswith("did not answer"):
        return [f"{command.rsplit('/', 1)[-1]} on {name}: {err}"]
    return []


def check(root: Path = ROOT) -> int:
    """Drive every wired hook through the whole table, and refuse a crash."""
    problems: list[str] = []
    for command in commands(root):
        for name, payload in PAYLOADS.items():
            problems += judge(command, name, answer(command, payload, root))

    for problem in problems:
        print(problem)
    print(f"{len(commands(root))} hook(s) x {len(PAYLOADS)} payload(s)")
    if problems:
        print(f"\n{len(problems)} problem(s). A hook refuses or stays silent; it never crashes.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from hook_degenerate_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
