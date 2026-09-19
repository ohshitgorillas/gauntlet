#!/usr/bin/env python3
"""Gate: every subprocess this tree starts is given a deadline.

    scripts/gates/subprocess-timeout.py [<path>...]
    scripts/gates/subprocess-timeout.py --self-test

With no paths the gate walks every `*.py` under `hooks/` and `scripts/`, which
is the whole of what this repository ships as Python. Paths on argv override
that set.

A hook runs inside a tool call the session is waiting on, and a gate runs inside
a runner the report is waiting on. A child that never returns therefore does not
fail anything: it hangs the caller, and a hang reads as a slow machine rather
than as a defect, so nobody looks. `timeout=` is what turns that hang into an
exception the caller can report. The child is a `git` reading a lock another
process holds, a `claude` waiting on a network, a `bwrap` waiting on a mount —
none of them rare, all of them silent.

Two shapes carry the rule. `subprocess.run`, `.call`, `.check_call` and
`.check_output` each take `timeout=` directly. `Popen` does not: its deadline is
given to `communicate`, which is why a `communicate` call with no `timeout=` is
a hit however its receiver is spelled. `Popen.wait` is not checked, since a
`Popen` this tree never waits on is a shape that has not appeared here.

The import spelling does not matter. `import subprocess`, `import subprocess as
sp` and `from subprocess import run` all reach the same function, so the gate
resolves the module alias and the imported name before it judges a call.

One shape is knowingly a false positive: a call passing its keywords through as
`**kwargs`, where the deadline may well be in the mapping. Nothing in this tree
spells a subprocess call that way, and a gate that waved every `**kwargs` call
past would be a gate a caller could switch off by rewriting one line.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

#: The directories the gate walks when it picks the file set itself.
ROOTS = ("hooks", "scripts")

#: The `subprocess` functions that take a deadline as `timeout=`.
FUNCTIONS = ("run", "call", "check_call", "check_output")

#: The `Popen` method that takes the deadline `Popen` itself does not.
COMMUNICATE = "communicate"

#: The module whose functions this gate governs.
MODULE = "subprocess"


def module_aliases(tree: ast.Module) -> set[str]:
    """Return every name `subprocess` itself is bound to in a parsed file."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found |= {alias.asname or alias.name for alias in node.names if alias.name == MODULE}
    return found


def imported_functions(tree: ast.Module) -> set[str]:
    """Return every bare name bound to one of the governed functions by `from subprocess import`."""
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == MODULE:
            found |= {alias.asname or alias.name for alias in node.names if alias.name in FUNCTIONS}
    return found


def is_module_call(call: ast.Call, aliases: set[str]) -> bool:
    """Report whether a call is `subprocess.run(...)` under any alias of the module."""
    func = call.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr in FUNCTIONS
        and isinstance(func.value, ast.Name)
        and func.value.id in aliases
    )


def is_bare_call(call: ast.Call, names: set[str]) -> bool:
    """Report whether a call is a governed function reached by its imported bare name."""
    return isinstance(call.func, ast.Name) and call.func.id in names


def is_communicate(call: ast.Call) -> bool:
    """Report whether a call is `.communicate(...)`, whatever it is called on."""
    return isinstance(call.func, ast.Attribute) and call.func.attr == COMMUNICATE


def governed(call: ast.Call, aliases: set[str], names: set[str]) -> bool:
    """Report whether a call is one this gate demands a deadline of."""
    return is_module_call(call, aliases) or is_bare_call(call, names) or is_communicate(call)


def has_timeout(call: ast.Call) -> bool:
    """Report whether a call spells `timeout=` among its keywords."""
    return any(keyword.arg == "timeout" for keyword in call.keywords)


def spelling(call: ast.Call) -> str:
    """Return how a call names the function it reaches, for the report line."""
    func = call.func
    if isinstance(func, ast.Attribute):
        return f".{func.attr}"
    return func.id if isinstance(func, ast.Name) else "the call"


def faults(name: str, tree: ast.Module) -> list[str]:
    """Return one file's problems, in source order."""
    aliases = module_aliases(tree)
    names = imported_functions(tree)
    hits = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and governed(node, aliases, names) and not has_timeout(node)
    ]
    return [
        f"{name}:{node.lineno}: {spelling(node)} carries no timeout= "
        "— a child with no deadline hangs its caller silently"
        for node in sorted(hits, key=lambda node: (node.lineno, node.col_offset))
    ]


def walked_files(roots: tuple[str, ...] = ROOTS) -> list[str]:
    """Return every `*.py` under the shipped roots, sorted, cache files apart."""
    found = set()
    for root in roots:
        for path in Path(root).rglob("*.py"):
            if path.is_file() and "__pycache__" not in path.parts:
                found.add(path.as_posix())
    return sorted(found)


def check(names: list[str]) -> int:
    """Refuse a tree where any named file starts a child it never gives a deadline."""
    problems: list[str] = []
    for name in names:
        problems += faults(name, ast.parse(Path(name).read_text()))

    for problem in problems:
        print(problem)
    if problems:
        print(
            f"\n{len(problems)} problem(s). A subprocess with no timeout= is a hang, not an error."
        )
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the paths on argv, or every shipped Python file when argv names none."""
    names = [arg for arg in argv[1:] if not arg.startswith("--")]
    return check(names or walked_files())


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from subprocess_timeout_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
