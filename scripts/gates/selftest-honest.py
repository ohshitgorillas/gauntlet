#!/usr/bin/env python3
"""Gate: a `--self-test` holds rules, and no rule passes without reading anything.

    scripts/gates/selftest-honest.py [--check]
    scripts/gates/selftest-honest.py --self-test

`check-gates.sh` runs every `--self-test` and fails on a non-zero exit. What it
cannot see is a self-test that has stopped asking anything: a rule table trimmed
to one row, a rule whose value is the constant `True`, two rules sharing a name
so the second quietly replaces the first. Each of those is green forever, and
green is what a bar is read for.

So the rule tables are read rather than run. Three spellings are in use here and
all three are found:

  * a `_rules()` function returning `{name: held}`;
  * a `lines = {name: held}` table handed to `hook_shape.report`;
  * a `rules["name"] = held` table filled a row at a time;
  * a local printer, `check(rule, got, want)`, called once per rule.

Three things hold about every body:

  * **There are rules, and enough of them.** `MIN_RULES` at least, and a body
    whose rules cannot be found at all is a body nothing can check.
  * **Every rule reads something.** A rule whose values carry no call, no
    attribute and no name bound to one is a constant dressed as a rule. A name
    is followed to what it was assigned, so `check(..., status, 0)` is read as
    the call that produced `status`.
  * **Every rule is named once.** A repeated name drops the row before it, and
    the count on screen is the only place that shows.

Reading rather than running is also what keeps this gate cheap: every
`--self-test` already runs once per `check-gates.sh`, and a second run of all of
them would cost the suite more than this bar is worth.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: where the self-test bodies live
BODIES = ("hooks", "scripts", "scripts/gates")

#: how a self-test body is named
SUFFIX = "_selftest.py"

#: the fewest rules a body can hold and still be a bar
MIN_RULES = 3

#: the function whose returned table is the rules, where a body has one
TABLE_FUNCTION = "_rules"

#: the names the other table spellings take, as a literal or a row at a time
TABLE_NAMES = ("lines", "rules")

#: how far a name is followed back to what was assigned to it
DEPTH = 3

#: one rule: its name and the expressions that decide it
Rule = tuple[str, tuple[ast.expr, ...]]


def bodies(root: Path = ROOT) -> list[Path]:
    """Every self-test body in the repository, sorted."""
    found = {path for name in BODIES for path in (root / name).glob(f"*{SUFFIX}")}
    return sorted(found)


def _entries(table: ast.Dict) -> list[Rule]:
    """One rule per named row of a table."""
    return [
        (key.value, (value,))
        for key, value in zip(table.keys, table.values, strict=True)
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    ]


def printers(tree: ast.AST) -> set[str]:
    """The functions a body defines that print one rule's verdict."""
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or len(node.args.args) < 2:
            continue
        for inner in ast.walk(node):
            if (
                isinstance(inner, ast.Constant)
                and isinstance(inner.value, str)
                and inner.value.startswith("PASS ")
            ):
                found.add(node.name)
    return found


def _returned(tree: ast.AST) -> list[Rule]:
    """The rules of a body that returns a table from its table function."""
    return [
        rule
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == TABLE_FUNCTION
        for inner in ast.walk(node)
        if isinstance(inner, ast.Return) and isinstance(inner.value, ast.Dict)
        for rule in _entries(inner.value)
    ]


def _assigned(tree: ast.AST) -> list[Rule]:
    """The rules of a body that assigns a table, whole or a row at a time."""
    found: list[Rule] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            named = isinstance(target, ast.Name) and target.id in TABLE_NAMES
            if named and isinstance(node.value, ast.Dict):
                found += _entries(node.value)
            if (
                isinstance(target, ast.Subscript)
                and isinstance(target.value, ast.Name)
                and target.value.id in TABLE_NAMES
                and isinstance(target.slice, ast.Constant)
                and isinstance(target.slice.value, str)
            ):
                found.append((target.slice.value, (node.value,)))
    return found


def _spoken(tree: ast.AST) -> list[Rule]:
    """The rules of a body that calls a printer of its own once per rule."""
    said = printers(tree)
    return [
        (node.args[0].value, tuple(node.args[1:]))
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in said
        and len(node.args) >= 2
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
    ]


def rules(tree: ast.AST) -> list[Rule]:
    """Every rule one body holds, in whichever of the four spellings it uses."""
    return _returned(tree) + _assigned(tree) + _spoken(tree)


def _names(target: ast.expr) -> list[str]:
    """Every name one assignment target binds, a tuple or list unpack included."""
    if isinstance(target, ast.Name):
        return [target.id]
    if isinstance(target, (ast.Tuple, ast.List)):
        return [one.id for one in target.elts if isinstance(one, ast.Name)]
    return []


def bound(tree: ast.AST) -> dict[str, ast.expr]:
    """What each name in a body was last assigned, for following a rule back."""
    out: dict[str, ast.expr] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            for name in _names(target):
                out[name] = node.value
    return out


def reads(value: ast.expr, names: dict[str, ast.expr], depth: int = DEPTH) -> bool:
    """Does this rule read anything, following a name back to what made it?"""
    for node in ast.walk(value):
        if isinstance(node, (ast.Call, ast.Attribute)):
            return True
        if (
            depth > 0
            and isinstance(node, ast.Name)
            and node.id in names
            and reads(names[node.id], names, depth - 1)
        ):
            return True
    return False


def judge(path: str, tree: ast.AST) -> list[str]:
    """Why one self-test body cannot stand as a bar, if it cannot."""
    held = rules(tree)
    if not held:
        return [f"{path}: no rules found. Nothing here can be read as a bar"]
    problems = []
    if len(held) < MIN_RULES:
        problems.append(f"{path}: {len(held)} rule(s), under the floor of {MIN_RULES}")
    names = [name for name, _ in held]
    problems += [
        f"{path}: rule {name!r} is named twice, and the first is dropped"
        for name in sorted({one for one in names if names.count(one) > 1})
    ]
    followed = bound(tree)
    problems += [
        f"{path}: rule {name!r} reads nothing. It passes whatever the kit does"
        for name, values in held
        if not any(reads(value, followed) for value in values)
    ]
    return problems


def audit(root: Path = ROOT) -> list[str]:
    """Every self-test body in the repository, read one after another."""
    problems = []
    for path in bodies(root):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, SyntaxError) as exc:
            problems.append(f"{path.name}: cannot be read ({exc})")
            continue
        problems += judge(str(path.relative_to(root)), tree)
    return problems


def check(root: Path = ROOT) -> int:
    """Read every self-test body against the three things that make it a bar."""
    problems = audit(root)
    for problem in problems:
        print(problem)
    print(f"{len(bodies(root))} self-test bod(y/ies)")
    if problems:
        print(f"\n{len(problems)} problem(s). A bar nobody can fail is not a bar.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from selftest_honest_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
