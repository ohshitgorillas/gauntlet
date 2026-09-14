#!/usr/bin/env python3
"""Report the test files a set of symbols reaches.

    printf '%s\n' <symbol>... | scripts/gates/symbol-closure.py --symbols-stdin <anchor>

The symbols arrive on stdin, one per line. The one argument is an anchor path,
and the directory it sits in is the scan root; every `*.py` file under that root
is read. Output is one path per line on stdout, sorted, each path written
relative to the parent of the scan root, and the exit code is 0 whether the set
is empty or not.

This is a fact reporter, not a gate. It answers "which files would a reviewer
have to read to see this symbol exercised", and it answers at file granularity
by name: a file that merely spells the name is reported, whether it imported the
name, was handed it as a fixture argument, or defined something else by the same
name. No arity analysis, no binding resolution, no import resolution.

The closure is direct hits plus one hop. A file naming a symbol is a direct hit;
a file naming something a direct hit defines is the hop, and the walk stops
there. A fixpoint would pull in a file whose only tie is a name taken from
another test file, which is a file the change under review does not reach.

A file that does not parse costs only itself: it is skipped, and every other
file under the root is still read.
"""

import ast
import sys
from pathlib import Path

USAGE = "usage: symbol-closure.py --symbols-stdin <anchor>"


def names_and_defines(text):
    """The identifiers a file spells, and the names it defines itself."""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return set(), set()

    names, defines = set(), set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
            defines.add(node.name)
        elif isinstance(node, ast.alias):
            names.update(node.name.split("."))
            if node.asname:
                names.add(node.asname)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.update(node.module.split("."))

    for node in tree.body:
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            targets = [node.target]
        for target in targets:
            for inner in ast.walk(target):
                if isinstance(inner, ast.Name):
                    defines.add(inner.id)

    return names, defines


def closure(root, symbols):
    """The paths under `root` the symbols reach, relative to the root's parent."""
    read = {}
    for path in root.rglob("*.py"):
        if path.is_file():
            read[path] = names_and_defines(path.read_text(errors="replace"))

    direct = {path for path, (names, _) in read.items() if names & symbols}

    exported = set()
    for path in direct:
        exported |= read[path][1]

    hop = {path for path, (names, _) in read.items() if path not in direct and names & exported}

    base = root.parent
    return sorted(str(path.relative_to(base)) for path in direct | hop)


def self_test():
    """One PASS or FAIL per rule this script exists to hold."""
    import tempfile

    failed = 0

    def tree(root, files):
        anchor = root / "tests" / "__init__.py"
        anchor.parent.mkdir(parents=True, exist_ok=True)
        anchor.write_text("")
        for name, text in files.items():
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)
        return anchor

    def check(rule, got, want):
        nonlocal failed
        if got == want:
            print(f"PASS {rule}")
        else:
            failed += 1
            print(f"FAIL {rule}: {got} != {want}")

    uses_alpha = "from pkg import alpha\n\n\ndef test_it():\n    alpha()\n"
    one = "tests/test_one.py"
    two = "tests/test_two.py"
    helper = "tests/support/helper.py"
    near = "tests/test_uses_helper.py"
    far = "tests/test_far.py"
    collide = "tests/test_collide.py"
    good = "tests/test_good.py"
    broken = "tests/test_broken.py"

    with tempfile.TemporaryDirectory() as tmp:
        anchor = tree(
            Path(tmp),
            {one: uses_alpha, two: "def test_two():\n    alpha()\n"},
        )
        check(
            "a bare reference with no import of its own reaches the closure",
            closure(anchor.parent, {"alpha"}),
            sorted([one, two]),
        )

    with tempfile.TemporaryDirectory() as tmp:
        anchor = tree(
            Path(tmp),
            {
                helper: ("from pkg import alpha\n\n\ndef build_thing():\n    return alpha()\n"),
                near: (
                    "from support.helper import build_thing\n"
                    "\n"
                    "\n"
                    "def test_uses_helper():\n"
                    "    build_thing()\n"
                ),
                far: (
                    "from test_uses_helper import other_thing\n"
                    "\n"
                    "\n"
                    "def test_far():\n"
                    "    other_thing()\n"
                ),
            },
        )
        check(
            "the closure takes one hop and stops",
            closure(anchor.parent, {"alpha"}),
            sorted([helper, near]),
        )

    with tempfile.TemporaryDirectory() as tmp:
        anchor = tree(
            Path(tmp),
            {
                one: uses_alpha,
                collide: (
                    "def alpha(x, y):\n"
                    "    return x + y\n"
                    "\n"
                    "\n"
                    "def test_collide():\n"
                    "    alpha(1, 2, 3)\n"
                ),
            },
        )
        check(
            "a file binding the name itself is still reported",
            closure(anchor.parent, {"alpha"}),
            sorted([collide, one]),
        )

    with tempfile.TemporaryDirectory() as tmp:
        anchor = tree(Path(tmp), {good: uses_alpha, broken: "def f(:\n"})
        check(
            "an unparseable file costs only itself",
            closure(anchor.parent, {"alpha"}),
            [good],
        )

    with tempfile.TemporaryDirectory() as tmp:
        anchor = tree(Path(tmp), {one: uses_alpha})
        check(
            "an empty closure prints nothing and is not an error",
            closure(anchor.parent, {"nothing_spells_this"}),
            [],
        )

    return 1 if failed else 0


def main(argv):
    if argv[1:] == ["--self-test"]:
        return self_test()
    if len(argv) != 3 or argv[1] != "--symbols-stdin":
        print(USAGE, file=sys.stderr)
        return 2
    symbols = {line.strip() for line in sys.stdin if line.strip()}
    for line in closure(Path(argv[2]).resolve().parent, symbols):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
