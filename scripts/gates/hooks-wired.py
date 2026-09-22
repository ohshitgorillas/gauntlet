#!/usr/bin/env python3
"""Gate: every hook this repository wires exists, compiles, and can be checked.

    scripts/gates/hooks-wired.py [--check]
    scripts/gates/hooks-wired.py --self-test

`gates-wired.py` reads the gate runner and answers a different question: does
every gate script run somewhere. This one reads the wiring a *consumer* gets --
`.claude-plugin/plugin.json`, and the settings files this checkout wires for
itself -- and asks whether each entry in it can fire at all.

An entry that cannot fire is silent. Claude Code prints `Hook script appears to
be missing` into the consumer's session and carries on with the lane
unenforced; a matcher that is not a regex matches nothing and denies nothing; an
event name with a typo in it is read by no dispatcher. None of those is a test
failure anywhere, because the suite imports the hook module directly and never
reads the manifest that names it. Four consumer outages of this repository came
back to exactly that gap: wiring left behind by a rename, and wiring left behind
by a consolidation.

So every rule here is read off the wiring rather than off the tree:

  * a command names a file, and the file is there;
  * a `*.py` it names compiles, so an import-time error is not first seen by a
    consumer;
  * a hook it names offers `--self-test`, so the bar the repository holds its
    hooks to reaches every hook it ships;
  * an event key is one a dispatcher reads;
  * a matcher is a regex `re` accepts;
  * an entry is `type: command` and carries a command string.

Paths are read relative to the working directory, which is the tree
`check-gates.sh` cds into before it runs anything.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

#: Every wiring file this repository ships or keeps. A file that is not there
#: is not a problem: `.claude/settings.local.json` is per-checkout and the
#: manifest is the only one a consumer installs.
WIRINGS = (
    ".claude-plugin/plugin.json",
    ".claude/settings.json",
    ".claude/settings.local.json",
)

#: The event keys a dispatcher reads. A key outside this set is a hook that
#: never fires, which reads in the file exactly like one that does.
KNOWN_EVENTS = (
    "PreToolUse",
    "PostToolUse",
    "Notification",
    "UserPromptSubmit",
    "Stop",
    "SubagentStop",
    "PreCompact",
    "SessionStart",
    "SessionEnd",
)

#: A script path as a wired command spells one, after the variable prefixes
#: (`${CLAUDE_PLUGIN_ROOT}`, `${CLAUDE_PROJECT_DIR}`) are dropped.
PATH_RE = re.compile(r"(?:hooks|scripts)/[\w./-]+\.(?:py|sh)")

#: What offering `--self-test` looks like: the flag itself, or the shared hook
#: entry point that routes it.
SELF_TEST_RE = re.compile(r"--self-test|hook_shape\.entry\(")


def read(name: str) -> str:
    """Return the text of a file, or the empty string when it is unreadable."""
    try:
        return Path(name).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def wired(name: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse one wiring file: its object, plus why it could not be read."""
    text = read(name)
    if not text.strip():
        return None, []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as broken:
        return None, [f"{name}: not JSON ({broken.msg} at line {broken.lineno})"]
    if not isinstance(data, dict):
        return None, [f"{name}: the top level is not an object"]
    return data, []


def groups(data: dict[str, Any]) -> list[tuple[str, Any]]:
    """Every (event, group) pair a wiring object holds, in file order."""
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return []
    found: list[tuple[str, Any]] = []
    for event, listed in hooks.items():
        if not isinstance(listed, list):
            found.append((event, None))
            continue
        found += [(event, group) for group in listed]
    return found


def event_problems(name: str, event: str, group: Any) -> list[str]:
    """Why one group's event key or matcher cannot fire, if it cannot."""
    problems = []
    if event not in KNOWN_EVENTS:
        problems.append(f"{name}: {event!r} is no hook event, so nothing dispatches it")
    if group is None:
        return problems + [f"{name}: the {event} entry is not a list of groups"]
    if not isinstance(group, dict):
        return problems + [f"{name}: a {event} group is not an object"]
    matcher = group.get("matcher")
    if matcher is not None:
        problems += matcher_problems(name, event, matcher)
    return problems


def matcher_problems(name: str, event: str, matcher: Any) -> list[str]:
    """Why one matcher matches nothing, if it matches nothing."""
    if not isinstance(matcher, str):
        return [f"{name}: the {event} matcher is not a string"]
    try:
        re.compile(matcher)
    except re.error as broken:
        return [f"{name}: the {event} matcher {matcher!r} is no regex ({broken})"]
    return []


def commands(name: str, event: str, group: Any) -> tuple[list[str], list[str]]:
    """The command strings one group wires, plus why any entry wires none."""
    if not isinstance(group, dict):
        return [], []
    listed = group.get("hooks")
    if not isinstance(listed, list):
        return [], [f"{name}: the {event} group carries no hooks list"]
    found: list[str] = []
    problems: list[str] = []
    for entry in listed:
        if not isinstance(entry, dict):
            problems.append(f"{name}: a {event} hook entry is not an object")
            continue
        if entry.get("type") != "command":
            problems.append(f"{name}: a {event} hook entry is not type 'command'")
            continue
        command = entry.get("command")
        if not isinstance(command, str) or not command.strip():
            problems.append(f"{name}: a {event} hook entry carries no command")
            continue
        found.append(command)
    return found, problems


def script_problems(name: str, command: str) -> list[str]:
    """Why the scripts one command names cannot answer, if they cannot.

    A command naming no repository path at all is left alone: a consumer's
    wiring may call something this tree does not hold.
    """
    problems: list[str] = []
    for path in PATH_RE.findall(command):
        if not Path(path).is_file():
            problems.append(f"{name}: {path} is wired and is not a file")
            continue
        problems += file_problems(name, path)
    return problems


def file_problems(name: str, path: str) -> list[str]:
    """Why one wired script cannot answer: it fails to compile, or offers no check."""
    problems: list[str] = []
    source = read(path)
    if path.endswith(".py"):
        try:
            compile(source, path, "exec")
        except SyntaxError as broken:
            problems.append(f"{name}: {path} is wired and does not compile ({broken.msg})")
            return problems
    if not SELF_TEST_RE.search(source):
        problems.append(f"{name}: {path} is wired and offers no --self-test")
    return problems


def audit(wirings: tuple[str, ...] = WIRINGS) -> list[str]:
    """Every reason a wired hook cannot fire, in the order the wirings list them."""
    problems: list[str] = []
    for name in wirings:
        data, unreadable = wired(name)
        problems += unreadable
        if data is None:
            continue
        for event, group in groups(data):
            problems += event_problems(name, event, group)
            found, wrong = commands(name, event, group)
            problems += wrong
            for command in found:
                problems += script_problems(name, command)
    return problems


def check(wirings: tuple[str, ...] = WIRINGS) -> int:
    """Refuse a tree where a wired hook cannot fire.

    Every rule runs every time, so one fix per run is never the shape of this.
    """
    problems = audit(wirings)
    for problem in problems:
        print(problem)
    if problems:
        print(
            f"\n{len(problems)} problem(s). "
            "A wired hook names a file that exists, compiles and answers --self-test."
        )
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from hooks_wired_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
