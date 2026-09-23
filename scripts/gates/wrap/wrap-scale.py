#!/usr/bin/env python3
"""Gate: the wrapped command stays small, whatever the checkout holds.

    scripts/gates/wrap/wrap-scale.py [--check]
    scripts/gates/wrap/wrap-scale.py --self-test

`bwrap-wrap.py` rewrites every `Bash` call into one `bwrap` invocation, and that
invocation is delivered as a single argument. The kernel caps one argument at
`MAX_ARG_STRLEN`, 128KB, and refuses the whole exec past it:

    Could not start /usr/bin/zsh: the command line plus environment exceed the
    OS exec argument limit (E2BIG).

Nothing in the hook's own self-test measures the string it builds, so the cap is
reached in a consumer's checkout rather than here. It has been: a checkout with
387 collected test files produced 54,944 characters at the parent tree and
222.8KB inside a worktree agent, and every `Bash` call in that session died.

So this gate builds real checkouts of different sizes, asks the live hook for
the wrap it would emit, and reads three numbers off it.

  * **Size.** The wrap stays under `MAX_COMMAND`. The ceiling is a quarter of
    the kernel's, because the caller's own command text and the environment
    share the same limit and the hook controls neither.
  * **Flatness.** The wrap is the same length at `SMALL` files and at `LARGE`.
    A mount table that grows per file is the shape that reaches the cap, and a
    ceiling alone does not catch it: it passes at 500 files and fails at the
    consumer's 5,000. The size rule bounds today; this one bounds tomorrow.
  * **Mounts.** The table stays under `MAX_BINDS` binds, for the same reason
    read a second way -- `bwrap` walks every bind at setup, and a table that is
    per-file is slow long before it is fatal.

The checkouts are empty files in a throwaway directory: 500 of them, created
and removed inside one run.
"""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from types import ModuleType

HOOKS = Path(__file__).resolve().parents[3] / "hooks"
LIB = HOOKS / "lib"

#: a quarter of `MAX_ARG_STRLEN`: the caller's command and the environment
#: share the kernel's limit with the wrap, and the hook controls neither
MAX_COMMAND = 32 * 1024

#: `bwrap` walks every bind at setup, so the table is bounded as a table
MAX_BINDS = 64

#: the two checkout sizes the flatness rule is read across
SMALL = 50
LARGE = 500

#: what a runner collects, spelled the way the mount table's own module does
TEST_NAME = "test_{n}.py"


def _load(name: str, directory: Path = HOOKS) -> ModuleType:
    """Import one hook module by path, since the hook names are hyphenated."""
    path = directory / f"{name}.py"
    if str(HOOKS) not in sys.path:
        sys.path.insert(0, str(HOOKS))
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def checkout(root: Path, count: int, lane: str) -> None:
    """Write one checkout: a tests lane holding `count` collected files."""
    (root / lane).mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)
    for index in range(count):
        (root / lane / TEST_NAME.format(n=index)).write_text("", encoding="utf-8")


def measure(count: int) -> tuple[int, int]:
    """The wrap the live hook emits for a checkout of `count` tests: chars, binds."""
    wrap = _load("bwrap-wrap")
    lane_config = _load("lane_config", LIB)
    with tempfile.TemporaryDirectory() as name:
        root = Path(name)
        checkout(root, count, lane_config.tests_dir())
        command = wrap.wrap("pwd", str(root), "")
    return len(command), command.count("-bind")


def judge(small: int, large: int, binds: int) -> list[str]:
    """Why the measured wrap cannot stand, if it cannot. Every rule, every run."""
    problems = []
    if large > MAX_COMMAND:
        problems.append(
            f"the wrap is {large} characters at {LARGE} tests, over the ceiling of "
            f"{MAX_COMMAND}; the kernel refuses one argument past 128KB with E2BIG"
        )
    if large != small:
        problems.append(
            f"the wrap grows with the checkout: {small} characters at {SMALL} tests, "
            f"{large} at {LARGE}. A mount table bound per file reaches the cap in a "
            "tree bigger than any this gate builds"
        )
    if binds > MAX_BINDS:
        problems.append(
            f"the mount table binds {binds} paths at {LARGE} tests, over the ceiling "
            f"of {MAX_BINDS}; bwrap walks every one of them at setup"
        )
    return problems


def check() -> int:
    """Measure the live hook against real checkouts, and refuse a wrap that scales."""
    small, _ = measure(SMALL)
    large, binds = measure(LARGE)
    problems = judge(small, large, binds)

    for problem in problems:
        print(problem)
    print(f"{small} chars at {SMALL} tests, {large} chars and {binds} binds at {LARGE}")
    if problems:
        print(f"\n{len(problems)} problem(s). The wrap is one argument, and the kernel caps it.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from wrap_scale_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
