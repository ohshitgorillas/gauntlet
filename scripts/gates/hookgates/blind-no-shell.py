#!/usr/bin/env python3
"""Gate: no blind agent holds a shell or the pair server.

    scripts/gates/hookgates/blind-no-shell.py [--check]
    scripts/gates/hookgates/blind-no-shell.py --self-test

A blind agent is blind because every route it has to the tree is a route a hook
can judge by path. `Read`, `Grep` and `Glob` name a path; a `Bash` call names a
command, and no hook reads a command. A blind agent that holds `Bash` can `cat`
the implementation through a mount table that was never built to hide it, and
nothing denies the call. The pair server runs `pair.sh`, which reads and merges
the implementation on the caller's behalf, so it is the same hole behind an MCP
name. MCP is the only path a blind agent has to a script, and the blind servers
are the ones built for it.

So the rule is one line long: for every agent named in the `BLIND` tuple of
`hooks/no-impl-reads.py`, the `tools:` line of `agents/<name>.md` carries no
`Bash` and no `mcp__plugin_gauntlet_pair__` name. The tuple is read with `ast`
rather than imported, so a hook that fails to import cannot make this gate
report nothing, and an agent added to the tuple is held without this file
changing.

A definition with no `tools:` line fails too: the harness reads an absent line
as every tool, `Bash` included. So does a blind name with no definition, and a
`BLIND` tuple that cannot be found, since a gate with no subject passes
everything.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

#: the hook whose `BLIND` tuple names the agents this gate holds
HOOK = "hooks/no-impl-reads.py"

#: the tuple's name in that hook
TUPLE = "BLIND"

#: where each agent's definition lives, by name
AGENTS = "agents"

#: the tool that is a shell
SHELL = "Bash"

#: every tool name the pair server grants starts with this
PAIR = "mcp__plugin_gauntlet_pair__"

#: the frontmatter block at the top of an agent definition
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)

#: the `tools:` line inside it
TOOLS = re.compile(r"^tools:(.*)$", re.M)


def blind(source: str) -> list[str] | None:
    """The names in the hook's `BLIND` tuple, or None when there is no such tuple."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, (ast.Tuple, ast.List)):
            continue
        if any(isinstance(target, ast.Name) and target.id == TUPLE for target in node.targets):
            return [
                one.value
                for one in node.value.elts
                if isinstance(one, ast.Constant) and isinstance(one.value, str)
            ]
    return None


def tools(definition: str) -> list[str] | None:
    """The tool names an agent definition grants, or None when it names none."""
    head = FRONTMATTER.match(definition)
    line = TOOLS.search(head.group(1)) if head else None
    if line is None:
        return None
    return [word.strip() for word in line.group(1).split(",") if word.strip()]


def forbidden(granted: list[str]) -> list[str]:
    """The granted names a blind agent may not hold, in the order they were granted."""
    return [
        name
        for name in granted
        if name == SHELL or name.startswith(f"{SHELL}(") or name.startswith(PAIR)
    ]


def judge(name: str, definition: str | None) -> list[str]:
    """Why one blind agent's definition cannot stand, if it cannot."""
    where = f"{AGENTS}/{name}.md"
    if definition is None:
        return [f"{where}: {name} is blind and has no definition to hold"]
    granted = tools(definition)
    if granted is None:
        return [f"{where}: no `tools:` line, which the harness reads as every tool"]
    return [f"{where}: blind, and granted {one}" for one in forbidden(granted)]


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def audit(root: Path = ROOT) -> list[str]:
    """Every blind agent's definition, read against the rule."""
    names = blind(_read(root / HOOK) or "")
    if not names:
        return [f"{HOOK}: no `{TUPLE}` tuple found, so no agent is held"]
    problems: list[str] = []
    for name in names:
        problems += judge(name, _read(root / AGENTS / f"{name}.md"))
    return problems


def check(root: Path = ROOT) -> int:
    """Refuse a tree where a blind agent holds a shell or the pair server."""
    problems = audit(root)
    for problem in problems:
        print(problem)
    print(f"{len(blind(_read(root / HOOK) or '') or [])} blind agent(s)")
    if problems:
        print(f"\n{len(problems)} problem(s). A blind agent reaches a script through MCP only.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from blind_no_shell_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
