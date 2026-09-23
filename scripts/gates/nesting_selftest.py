#!/usr/bin/env python3
"""The `--self-test` body of `nesting.py`: one line per rule the gate holds.

It lives beside the gate rather than inside it so the gate stays readable as a
walk plus a table, and `python3 scripts/gates/nesting.py --self-test` runs it.

Each case writes real source into a throwaway tree, changes into it so the
paths reaching the gate are repo-relative the way a real run passes them, and
hands the gate its own exemption mapping. What is checked is the pair the gate
offers a caller: the exit code, and what lands on stdout.
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from types import ModuleType

GATE_PATH = Path(__file__).resolve().parent / "nesting.py"


def _load_gate() -> ModuleType:
    """Import the gate by path, since it also needs to be runnable as a script."""
    spec = importlib.util.spec_from_file_location("nesting_under_test", GATE_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {GATE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = _load_gate()

#: Each block-opening construct as (opening lines, how far its body is indented
#: past the opener, lines that close it off). ``match`` opens with a ``case``
#: arm, which puts its body two indents in; ``try`` needs a handler after it.
BLOCKS: dict[str, tuple[list[str], int, list[str]]] = {
    "if": (["if cond:"], 1, []),
    "for": (["for _item in items:"], 1, []),
    "while": (["while cond:"], 1, []),
    "with": (["with ctx:"], 1, []),
    "try": (["try:"], 1, ["except Exception:", "    pass"]),
    "match": (["match value:", "    case _:"], 2, []),
}


def _nest(kind: str, depth: int, indent: int = 1) -> list[str]:
    """Lines for ``depth`` copies of ``kind`` nested one inside the next."""
    opener, step, trailer = BLOCKS[kind]
    pad = "    " * indent
    lines = [pad + line for line in opener]
    if depth > 1:
        lines += _nest(kind, depth - 1, indent + step)
    else:
        lines.append("    " * (indent + step) + "pass")
    return lines + [pad + line for line in trailer]


def _function(kind: str, depth: int, name: str = "f") -> str:
    """A module whose one function nests ``depth`` copies of ``kind``, ``def`` on line 1."""
    return "\n".join([f"def {name}():", *_nest(kind, depth)]) + "\n"


#: An if/elif chain three levels in. Every arm sits at the same level as the
#: ``if`` it belongs to, so the chain is one level however many arms it has.
_ELIF_CHAIN = """
def f():
    if cond:
        for _item in items:
            if a:
                pass
            elif b:
                pass
            else:
                pass
"""

#: A nested function five deep inside an outer one that is only two deep, so
#: only the inner one is the violation and it is reported under its dotted name.
_NESTED_DEF_OVER_LIMIT = """
def outer():
    if cond:

        def inner():
            if cond:
                for _item in items:
                    while cond:
                        with ctx:
                            if cond:
                                pass
"""


def _write(root: Path, relpath: str, source: str) -> str:
    """Write ``source`` at ``relpath`` under ``root``; return its relative path."""
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source)
    return relpath


def _run(files: dict[str, str], names: list[str] | None, exempt: dict[str, str]) -> tuple[int, str]:
    """Build a tree of `files`, run the gate over `names`, and return its status and stdout.

    With `names` None the tree is a git checkout the files sit in untracked, and
    the gate picks its own file set.
    """
    cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        for relpath, source in files.items():
            _write(root, relpath, source)
        if names is None:
            subprocess.run(["git", "init", "-q", tmp], check=True, capture_output=True, timeout=60)
        os.chdir(root)
        out = io.StringIO()
        try:
            with redirect_stdout(out):
                status = GATE.check(GATE.tracked_files() if names is None else names, exempt)
        finally:
            os.chdir(cwd)
    return status, out.getvalue()


def self_test() -> int:  # noqa: PLR0915
    """One PASS or FAIL per rule this gate exists to hold."""
    failed = 0

    def check(rule: str, got: object, want: object) -> None:
        nonlocal failed
        if got == want:
            print(f"PASS {rule}")
        else:
            failed += 1
            print(f"FAIL {rule}: {got!r} != {want!r}")

    deep = "hooks/deep.py"

    status, out = _run({deep: _function("if", 4)}, [deep], {})
    check("a function at the limit passes", (status, out), (0, ""))

    status, out = _run({deep: _function("if", 5)}, [deep], {})
    check("a function one past the limit fails", status, 1)
    check("the offending file is named on stdout", deep in out, True)
    check("the reported depth is on stdout", "5 deep (max 4)" in out, True)

    status, _ = _run({deep: _ELIF_CHAIN}, [deep], {})
    check("an elif chain shares its if's level and passes", status, 0)

    status, out = _run({deep: _NESTED_DEF_OVER_LIMIT}, [deep], {})
    check("a nested def over the limit fails", status, 1)
    check("it is reported under its dotted name", "outer.inner()" in out, True)

    status, out = _run({deep: _function("if", 5)}, [deep], {f"{deep}::f": "measured on purpose"})
    check("an exempt function passes", (status, out), (0, ""))

    status, out = _run({deep: _function("if", 4)}, [deep], {f"{deep}::f": "no longer needed"})
    check("an exemption for a function back within the limit fails as stale", status, 1)
    check("the stale entry is named on stdout", f"{deep}::f" in out, True)

    status, out = _run({deep: _function("if", 4)}, [deep], {"hooks/missing.py::f": "long gone"})
    check("an exemption naming no file fails as stale", status, 1)
    check("the missing-file entry is named on stdout", "hooks/missing.py::f" in out, True)

    files = {"hooks/one.py": _function("if", 5, "f"), "hooks/two.py": _function("if", 4, "f")}
    status, out = _run(files, list(files), {})
    check("one offender among compliant files fails the gate", status, 1)
    check("the compliant file is not named", "hooks/two.py" in out, False)

    status, out = _run({deep: _function("if", 5)}, None, {})
    check("with no paths an untracked Python file is read", (status, deep in out), (1, True))

    check("the shipped tree passes its own gate", GATE.main(["nesting.py"]), 0)

    if failed:
        print(f"\n{failed} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test())
