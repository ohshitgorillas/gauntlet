#!/usr/bin/env python3
"""Gate: every test function holds exactly one assertion, of a shape a test may take.

    scripts/gates/test-assertions.py [<path>...]
    scripts/gates/test-assertions.py --self-test

With no paths the gate reads `git ls-files 'tests/*.py'`, which is the whole of
what this repository tests itself with. Paths on argv override that set.

`docs/testing.md` rules 2, 3, 10 and 14 and the Markers section. One finding is
a `(category, location, count)` tuple; `count` is the assertion count for the
`count` category and 0 otherwise.

  count      a test function holds `count` assertions, wanting one. An assertion
             is an `assert` statement, a `pytest.raises(...)` context, or a
             framework assertion — `self.assertEqual(...)`, `self.fail(...)`,
             `self.assertRaises(...)` and their siblings; a boolean conjunction
             at an `assert`'s root counts one per operand.
  loop       an assertion inside a loop, or `all()`/`any()` over a generator at
             an `assert`'s root: an unparametrized case sweep either way.
  outside    an assertion in a function that is not a test and is not nested
             inside one — a helper method or a fixture as much as a module-level
             function. Helpers return evidence; a fixture that must refuse raises.
  existence  an `assert` whose whole condition is `x is not None`,
             `len(x) > 0` or `len(x)`: presence pinned where a value was owed.
  skip       a `skip`, `skipif` or `xfail` decorator.
  private    a single-underscore attribute reached on anything but `self` or
             `cls`. Dunders are protocol and pass; `tests/support/` fakes may
             reach into their own state and are not scanned.

Shape checks read the root of the one condition, looking through a leading
`not` for the conjunction and sweep shapes and nothing deeper, so a conjunction
that is an operand of a comparison passes. Functions nested inside a test are
not scanned: a gate defeated by wrapping the assert in a closure is not a gate,
and the fix is to keep the assert at the call site.

Sites allowed to stand say why in `EXEMPT`, keyed `<path>::<test name>`, each
owner-approved and each carrying its entry in `docs/exemptions.md`; the table
covers the `skip` and `existence` categories only, since rule 10 keeps one legal
existence case and the Markers section one legal skip class.
"""

from __future__ import annotations

import ast
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

Finding = tuple[str, str, int]

#: The pathspec this gate reads when it picks the file set itself.
TRACKED = ("tests/*.py",)

#: `<path>::<test name>` to the owner-approved reason a skip or xfail decorator,
#: or an existence-only assertion under rule 10's escape, stands. Every key here
#: has an entry in docs/exemptions.md; this table is not where one is granted.
EXEMPT: dict[str, str] = {}

_FUNCS = (ast.FunctionDef, ast.AsyncFunctionDef)
_LOOPS = (ast.For, ast.AsyncFor, ast.While)
_SKIP_MARKS = frozenset({"skip", "skipif", "xfail"})
_SWEEPS = frozenset({"all", "any"})
_SELVES = frozenset({"self", "cls"})


def _is_raises(node: ast.With | ast.AsyncWith) -> bool:
    for item in node.items:
        call = item.context_expr
        if (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Attribute)
            and call.func.attr == "raises"
        ):
            return True
    return False


def _root(expr: ast.expr) -> ast.expr:
    """Return the condition under any leading `not`."""
    while isinstance(expr, ast.UnaryOp) and isinstance(expr.op, ast.Not):
        expr = expr.operand
    return expr


def _is_sweep(expr: ast.expr) -> bool:
    return (
        isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id in _SWEEPS
    )


def _weight(node: ast.Assert) -> tuple[int, bool]:
    """(how many assertions this `assert` counts as, whether it is a sweep)."""
    root = _root(node.test)
    if isinstance(root, ast.BoolOp):
        return len(root.values), False
    return 1, _is_sweep(root)


def _is_framework_assert(node: ast.Call) -> bool:
    """Return whether a call is a `unittest` assertion made on `self` or `cls`."""
    func = node.func
    if not isinstance(func, ast.Attribute) or not isinstance(func.value, ast.Name):
        return False
    return func.value.id in _SELVES and (func.attr.startswith("assert") or func.attr == "fail")


def _count_assertions(node: ast.AST, *, in_loop: bool = False) -> tuple[int, bool]:
    """Return (assertion count, any-inside-loop-or-sweep) for everything under a node.

    Does not descend into nested function definitions.
    """
    count, looped = 0, False
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _FUNCS):
            continue
        if isinstance(child, ast.Assert):
            weight, sweep = _weight(child)
            count += weight
            looped = looped or in_loop or sweep
        elif (isinstance(child, ast.Call) and _is_framework_assert(child)) or (
            isinstance(child, (ast.With, ast.AsyncWith)) and _is_raises(child)
        ):
            count += 1
            looped = looped or in_loop
        sub_count, sub_looped = _count_assertions(
            child, in_loop=in_loop or isinstance(child, _LOOPS)
        )
        count += sub_count
        looped = looped or sub_looped
    return count, looped


def _is_none(expr: ast.expr) -> bool:
    return isinstance(expr, ast.Constant) and expr.value is None


def _is_len(expr: ast.expr) -> bool:
    return isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == "len"


def _is_existence(test: ast.expr) -> bool:
    """`x is not None`, `len(x) > 0` or `len(x)` as the whole condition."""
    if isinstance(test, ast.Compare) and len(test.ops) == 1:
        op, right = test.ops[0], test.comparators[0]
        if isinstance(op, ast.IsNot) and _is_none(right):
            return True
        return (
            isinstance(op, ast.Gt)
            and _is_len(test.left)
            and isinstance(right, ast.Constant)
            and right.value == 0
        )
    return _is_len(test)


def _is_skip_mark(decorator: ast.expr) -> bool:
    target = decorator.func if isinstance(decorator, ast.Call) else decorator
    if not isinstance(target, ast.Attribute) or target.attr not in _SKIP_MARKS:
        return False
    owner = target.value
    if isinstance(owner, ast.Attribute):
        return owner.attr == "mark"
    return isinstance(owner, ast.Name) and owner.id == "mark"


def _own_nodes(node: ast.AST) -> Iterator[ast.AST]:
    """Every node under `node` except those inside a nested function."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _FUNCS):
            continue
        yield child
        yield from _own_nodes(child)


def _test_findings(
    path: Path, fn: ast.FunctionDef | ast.AsyncFunctionDef, exempt: dict[str, str]
) -> list[Finding]:
    where = f"{path}:{fn.lineno} {fn.name}"
    findings: list[Finding] = []
    count, looped = _count_assertions(fn)
    if count != 1:
        findings.append(("count", where, count))
    elif looped:
        findings.append(("loop", where, 0))
    if f"{path}::{fn.name}" in exempt:
        return findings
    if any(isinstance(node, ast.Assert) and _is_existence(node.test) for node in _own_nodes(fn)):
        findings.append(("existence", where, 0))
    if any(_is_skip_mark(decorator) for decorator in fn.decorator_list):
        findings.append(("skip", where, 0))
    return findings


def _asserts_in(fn: ast.AST) -> list[ast.Assert | ast.Call]:
    """Every assertion a function makes itself, bare `assert` and framework alike."""
    return [
        node
        for node in _own_nodes(fn)
        if isinstance(node, ast.Assert)
        or (isinstance(node, ast.Call) and _is_framework_assert(node))
    ]


def _helpers(
    node: ast.AST, *, in_test: bool = False
) -> Iterator[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Every function that is not a test and is not nested inside one, methods included."""
    for child in ast.iter_child_nodes(node):
        if isinstance(child, _FUNCS):
            inside = in_test or child.name.startswith("test_")
            if not inside:
                yield child
            yield from _helpers(child, in_test=inside)
        else:
            yield from _helpers(child, in_test=in_test)


def _outside_findings(path: Path, fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[Finding]:
    return [("outside", f"{path}:{node.lineno} {fn.name}", 0) for node in _asserts_in(fn)]


def _is_private_reach(node: ast.Attribute) -> bool:
    if not node.attr.startswith("_") or node.attr.startswith("__"):
        return False
    return not (isinstance(node.value, ast.Name) and node.value.id in _SELVES)


def _private_reaches(path: Path, scope: ast.AST, name: str) -> list[Finding]:
    reaches = (
        node
        for node in _own_nodes(scope)
        if isinstance(node, ast.Attribute) and _is_private_reach(node)
    )
    return [("private", f"{path}:{node.lineno} {name}", 0) for node in reaches]


def _private_findings(path: Path, tree: ast.Module) -> list[Finding]:
    """Private reaches per enclosing function, module-level code under `<module>`."""
    if "support" in path.parts:
        return []
    findings = _private_reaches(path, tree, "<module>")
    for node in ast.walk(tree):
        if isinstance(node, _FUNCS):
            findings.extend(_private_reaches(path, node, node.name))
    return findings


def _line_of(finding: Finding) -> int:
    return int(finding[1].rsplit(":", 1)[1].split(" ", 1)[0])


def check_file(path: Path, exempt: dict[str, str] | None = None) -> list[Finding]:
    """Return one finding per shape defect in `path`, in line order.

    `exempt` defaults to `EXEMPT`; a `skip` or `existence` finding whose
    `<path>::<name>` is a key is not returned.
    """
    if exempt is None:
        exempt = EXEMPT
    tree = ast.parse(path.read_text(), filename=str(path))
    findings: list[Finding] = []
    for node in ast.walk(tree):
        if isinstance(node, _FUNCS) and node.name.startswith("test_"):
            findings.extend(_test_findings(path, node, exempt))
    for node in _helpers(tree):
        findings.extend(_outside_findings(path, node))
    findings.extend(_private_findings(path, tree))
    return sorted(findings, key=_line_of)


def describe(finding: Finding) -> str:
    """Return the one line a finding prints as."""
    category, where, count = finding
    if category == "count":
        return f"{where}: {count} assertions (want 1)"
    return f"{where}: {category}"


def tracked_tests() -> list[str]:
    """Return the tracked test modules of the tree the gate is run in."""
    listed = subprocess.run(
        ["git", "ls-files", "-z", *TRACKED],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return [name for name in listed.stdout.split("\0") if name and Path(name).is_file()]


def check(names: list[str], exempt: dict[str, str] | None = None) -> int:
    """Refuse a suite where a named file holds a test of a shape a test may not take."""
    findings = [finding for name in names for finding in check_file(Path(name), exempt)]
    for finding in findings:
        print(describe(finding))
    if findings:
        print(
            f"\n{len(findings)} problem(s). "
            "One assertion per test, and a test reaches only the public surface."
        )
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the paths on argv, or the tracked test modules when argv names none."""
    names = argv[1:]
    return check(names or tracked_tests())


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from test_assertions_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
