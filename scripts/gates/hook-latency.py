#!/usr/bin/env python3
"""Gate: a wired hook decides fast enough to sit in front of every tool call.

    scripts/gates/hook-latency.py [--check]
    scripts/gates/hook-latency.py --self-test

Every lane in this kit runs as its own process, and three of them run in front
of every `Bash` call. That cost is paid by the agent on every tool use, and
nothing else in the repository measures it: a hook that grows an import, walks a
tree, or shells out once per call stays correct and makes the session slower,
one call at a time, with no line anywhere saying so.

So each wired command is run as a process against a representative payload and
timed. Two ceilings:

  * `PER_HOOK_MS` for one hook, so a single slow decision is named as itself;
  * `PER_CALL_MS` for the whole chain of one event, since a `Bash` call pays
    for every hook wired at `PreToolUse` and the agent waits for all of them.

The figure taken is the fastest of `RUNS` runs. A gate that reads a mean would
fail on whatever else the host was doing; the fastest run is the closest thing
to the hook's own cost, and a hook that cannot make the ceiling *once* in three
tries is slow for its own reasons.

The commands come from the manifest rather than from a list kept here, so a
lane wired later is measured without this file changing.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

MANIFEST = ".claude-plugin/plugin.json"

#: one hook, one payload, measured at its fastest
PER_HOOK_MS = 900

#: every hook wired at one event, which is what a single tool call waits for
PER_CALL_MS = 2500

#: the fastest of this many runs is the figure
RUNS = 3

#: a hook that has not answered in this long is not slow, it is stuck
TIMEOUT = 30

#: what a hook is handed: an ordinary `Bash` call from the main agent
PAYLOAD: dict[str, Any] = {
    "tool_name": "Bash",
    "tool_input": {"command": "pwd"},
    "cwd": str(ROOT),
    "session_id": "hook-latency",
}


def commands(root: Path = ROOT) -> list[tuple[str, str]]:
    """Every wired hook as `(event, command)`, in the order the manifest lists them."""
    try:
        data = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return []
    hooks = data.get("hooks") if isinstance(data, dict) else None
    if not isinstance(hooks, dict):
        return []
    return [
        (event, entry["command"])
        for event, listed in hooks.items()
        for group in listed
        for entry in group.get("hooks", [])
        if isinstance(entry, dict) and isinstance(entry.get("command"), str)
    ]


def _argv(command: str, root: Path) -> list[str]:
    """One wired command as an argument list, with the plugin root filled in."""
    filled = command.replace('"${CLAUDE_PLUGIN_ROOT}"', str(root))
    filled = filled.replace("${CLAUDE_PLUGIN_ROOT}", str(root))
    filled = filled.replace('"${CLAUDE_PROJECT_DIR}"', str(root))
    filled = filled.replace("${CLAUDE_PROJECT_DIR}", str(root))
    parts = filled.split()
    return [sys.executable if parts[0] == "python3" else parts[0], *parts[1:]]


def once(command: str, root: Path = ROOT) -> float:
    """Milliseconds one wired command takes to decide one payload."""
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    environment["CLAUDE_PLUGIN_ROOT"] = str(root)
    started = time.monotonic()
    subprocess.run(
        _argv(command, root),
        input=json.dumps(PAYLOAD),
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=False,
        env=environment,
    )
    return (time.monotonic() - started) * 1000


def fastest(command: str, root: Path = ROOT, runs: int = RUNS) -> float:
    """The lowest of `runs` readings for one command, in milliseconds."""
    return min(once(command, root) for _ in range(runs))


def judge(measured: list[tuple[str, str, float]]) -> list[str]:
    """Why the wired hooks cannot stand in front of a tool call, if they cannot."""
    problems = [
        f"{command}: {ms:.0f}ms at its fastest, over the per-hook ceiling of {PER_HOOK_MS}ms"
        for _, command, ms in measured
        if ms > PER_HOOK_MS
    ]
    for event in dict.fromkeys(event for event, _, _ in measured):
        total = sum(ms for one, _, ms in measured if one == event)
        if total > PER_CALL_MS:
            problems.append(
                f"{event}: {total:.0f}ms for the whole chain, over the per-call ceiling "
                f"of {PER_CALL_MS}ms. Every tool call of that kind waits for it"
            )
    return problems


def check(root: Path = ROOT) -> int:
    """Time every wired hook against one payload, and refuse a chain that is slow."""
    measured = [(event, command, fastest(command, root)) for event, command in commands(root)]
    problems = judge(measured)

    for problem in problems:
        print(problem)
    for event, command, ms in measured:
        print(f"{ms:7.0f}ms  {event:<16} {command.rsplit('/', 1)[-1]}")
    if problems:
        print(f"\n{len(problems)} problem(s). Every tool call pays for every hook in front of it.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from hook_latency_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
