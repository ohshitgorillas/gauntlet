#!/usr/bin/env python3
"""Gate: no test sleeps on a real clock or holds a small real deadline.

    scripts/gates/test-clocks.py [<path>...]
    scripts/gates/test-clocks.py --self-test

With no paths the gate reads `git ls-files 'tests/*.py'`, which is the whole of
what this repository tests itself with. Paths on argv override that set.

`docs/testing.md` rule 7, two patterns in one AST pass.

A `time.sleep` or `asyncio.sleep` call is flagged unless its argument is the
literal `0`, which is a scheduler yield rather than a wait. Anything else is
flagged, literal or not: the house spelling for a wait is often a module
constant or an attribute, and a literal-only match reads a paced fake as clean.
A fixed sleep has no carve-out anywhere under `tests/`: rule 7 bans it in an
end-to-end test as flatly as in a unit test.

A `timeout` or `*_timeout` keyword or mapping key given a numeric literal above
zero and below SMALL is flagged. Rule 7 makes a timeout a ceiling on a
condition, never an expected duration, and the value is what separates the two:
a ceiling a test never reaches is at seconds, a deadline the code waits out is
at a fraction of a second.

A per-test duration threshold cannot see either pattern: a ten millisecond poll
spread over seventy call sites lifts no test over any threshold, and a deadline
waited out in a worker thread reads as CPU rather than as idle.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

#: The pathspec this gate reads when it picks the file set itself.
TRACKED = ("tests/*.py",)

#: Seconds below which a real deadline is a wait rather than a ceiling.
SMALL = 0.5


def _sleeps(node: ast.Call) -> bool:
    """Return whether the call is a real-clock sleep, by the module it is called on.

    `time` and `asyncio` are the two modules that hold a real clock. A `.sleep`
    on anything else is a seam the test controls, and waits on no clock at all.
    """
    func = node.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "sleep"
        and isinstance(func.value, ast.Name)
        and func.value.id in ("time", "asyncio")
    )


def _waits(node: ast.Call) -> bool:
    """Return whether a sleep call waits, rather than yielding to the scheduler."""
    if not node.args:
        return False
    first = node.args[0]
    return not (isinstance(first, ast.Constant) and isinstance(first.value, (int, float)) and first.value == 0)


def _deadline(name: str | None, value: ast.expr) -> bool:
    """Return whether a name and its value are a small real deadline.

    Zero is no deadline: it is the spelling for a socket or a route that returns
    on the first pass, and it waits on nothing, as `sleep(0)` does.
    """
    if name is None or not (name == "timeout" or name.endswith("_timeout")):
        return False
    return isinstance(value, ast.Constant) and isinstance(value.value, (int, float)) and 0 < value.value < SMALL


def _call_faults(name: str, node: ast.Call) -> list[str]:
    """Return one line per real clock a call holds: its own wait, and its deadline keywords."""
    found = [f"{name}:{node.lineno}: sleeps on a real clock"] if _sleeps(node) and _waits(node) else []
    found += [
        f"{name}:{keyword.value.lineno}: {keyword.arg}= is a real deadline under {SMALL}s"
        for keyword in node.keywords
        if _deadline(keyword.arg, keyword.value)
    ]
    return found


def _mapping_faults(name: str, node: ast.Dict) -> list[str]:
    """Return one line per deadline a mapping literal carries under a string key."""
    pairs = zip(node.keys, node.values, strict=True)
    return [
        f"{name}:{key.lineno}: {key.value!r} is a real deadline under {SMALL}s"
        for key, value in pairs
        if isinstance(key, ast.Constant) and isinstance(key.value, str) and _deadline(key.value, value)
    ]


def faults(name: str, source: str) -> list[str]:
    """Return one line per real clock in a module source."""
    found: list[str] = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            found += _call_faults(name, node)
        elif isinstance(node, ast.Dict):
            found += _mapping_faults(name, node)
    return sorted(found)


def tracked_tests() -> list[str]:
    """Return the tracked test modules of the tree the gate is run in."""
    listed = subprocess.run(
        ["git", "ls-files", "-z", *TRACKED],
        capture_output=True,
        text=True,
        check=True,
    )
    return [name for name in listed.stdout.split("\0") if name and Path(name).is_file()]


def check(names: list[str]) -> int:
    """Refuse a suite where a named file holds a real clock."""
    problems = [problem for name in names for problem in faults(name, Path(name).read_text())]
    for problem in problems:
        print(problem)
    if problems:
        print(
            f"\n{len(problems)} real clock(s) under tests/. A poll waits on a condition and a deadline"
            " comes from a seam the test controls; docs/testing.md rule 7 is the rule."
        )
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the paths on argv, or the tracked test modules when argv names none."""
    names = argv[1:]
    return check(names or tracked_tests())


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from test_clocks_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
