#!/usr/bin/env python3
"""The `--self-test` body of `selftest-honest.py`: one line per rule it holds.

Each rule is read against a body written for it, so the three spellings, the
floor, the constant rule and the repeated name are exercised one at a time. Two
rules are not invented: the repository's own bodies are found on disk, and they
are all audited, because a gate whose reading path raises reports nothing.
"""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "selftest-honest.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since its name is hyphenated."""
    if str(GATE_PATH.parent) not in sys.path:
        sys.path.insert(0, str(GATE_PATH.parent))
    spec = importlib.util.spec_from_file_location("selftest_honest_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

#: the first spelling: a table returned by `_rules`
TABLE = """
FIXTURE = {"tool_name": "Bash", "cwd": "/repo", "agent_type": "juror"}


def _rules():
    return {
        "one": GATE.judge([]) == [],
        "two": len(GATE.judge(["x"])) == 1,
        "three": GATE.audit() == [],
    }
"""

#: the second spelling: a table handed to `hook_shape.report`
REPORTED = """
def self_test():
    lines = {
        "one": GATE.judge([]) == [],
        "two": len(GATE.judge(["x"])) == 1,
        "three": GATE.audit() == [],
    }
    return hook_shape.report(lines)
"""

#: the third spelling: a table filled a row at a time
ROWS = """
def self_test():
    rules = {}
    rules["one"] = GATE.judge([]) == []
    rules["two"] = len(GATE.judge(["x"])) == 1
    rules["three"] = GATE.audit() == []
"""

#: the fourth spelling: a local printer called once per rule
PRINTED = """
def self_test():
    def check(rule, got, want):
        if got == want:
            print(f"PASS {rule}")
        else:
            print(f"FAIL {rule}")

    status, out = _run("a")
    check("one", status, 0)
    check("two", out, "b")
    check("three", GATE.audit(), [])
"""

#: a table carrying a rule that is a constant
CONSTANT = TABLE.replace("GATE.audit() == []", "True")

#: a table naming one rule twice
REPEATED = TABLE.replace('"three"', '"one"')

#: a table under the floor
SMALL = """
def _rules():
    return {"one": GATE.judge([]) == [], "two": GATE.audit() == []}
"""

#: a body holding no rules at all
BARE = "def self_test():\n    return 0\n"


def _judged(body: str) -> list[str]:
    """What the gate says about one invented self-test body."""
    said: list[str] = GATE.judge("invented_selftest.py", ast.parse(body))
    return said


def _rules() -> dict[str, bool]:
    """One entry per rule the gate exists to hold, name to whether it held."""
    constant = _judged(CONSTANT)
    repeated = _judged(REPEATED)
    small = _judged(SMALL)
    bare = _judged(BARE)
    found = GATE.bodies()
    return {
        "a table returned by _rules is read, and a fixture beside it is not": (
            [name for name, _ in GATE.rules(ast.parse(TABLE))] == ["one", "two", "three"]
        ),
        "a table handed to report is read": (
            [name for name, _ in GATE.rules(ast.parse(REPORTED))] == ["one", "two", "three"]
        ),
        "a table filled a row at a time is read": (
            [name for name, _ in GATE.rules(ast.parse(ROWS))] == ["one", "two", "three"]
        ),
        "a local printer's calls are read as rules": (
            [name for name, _ in GATE.rules(ast.parse(PRINTED))] == ["one", "two", "three"]
        ),
        "a body whose rules each read something passes": (
            _judged(TABLE) == []
            and _judged(REPORTED) == []
            and _judged(ROWS) == []
            and _judged(PRINTED) == []
        ),
        "a rule that is a constant fails, named": (
            len(constant) == 1 and "reads nothing" in constant[0] and "three" in constant[0]
        ),
        "a rule named twice fails": len(repeated) == 1 and "named twice" in repeated[0],
        "a body under the floor fails, and so does one with no rules": (
            len(small) == 1
            and "under the floor" in small[0]
            and len(bare) == 1
            and "read as a bar" in bare[0]
        ),
        "a name is followed back to the call that made it": (
            GATE.reads(
                ast.parse("status", mode="eval").body,
                GATE.bound(ast.parse("status, out = _run('a')")),
            )
            and not GATE.reads(ast.parse("True", mode="eval").body, {})
        ),
        "every self-test body in the repository is found": (
            len(found) > 20 and all(path.name.endswith(GATE.SUFFIX) for path in found)
        ),
        "every one of them is audited, and they stand": GATE.audit() == [],
    }


def self_test() -> int:
    """One PASS or FAIL per rule the gate exists to hold. Non-zero on any FAIL."""
    rules = _rules()
    for name, held in sorted(rules.items()):
        print(f"{'PASS' if held else 'FAIL'} {name}")
    return 0 if all(rules.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test())
