#!/usr/bin/env python3
"""Gate: the wrap the hook emits actually runs, and holds what it claims to.

    scripts/gates/wrap-runtime.py [--check]
    scripts/gates/wrap-runtime.py --self-test

`bwrap-wrap.py` is checked today by reading the argument list it builds. That
catches a missing flag and nothing else. Every consumer outage of this hook has
been the other kind: an argument list that is correct on paper and impossible at
exec -- a table too long for the kernel, a mask that hides the file the command
was about to read, a bind that lands read-only over something the suite writes.

So this gate executes. It builds a checkout, asks the hook for the wrap, runs it
through `bash`, and reads the result off the process rather than off the string.

  * **It runs.** A wrapped `pwd` exits 0 and prints the checkout. A wrap that
    cannot exec takes every `Bash` call in the session with it.
  * **Scratch survives nesting.** A wrapped command writes a file under the
    session scratch directory and a *second* wrap, nested inside the first,
    reads it back. A suite that builds a fixture and then runs a wrapped child
    against it needs exactly this, and a fresh `--tmpfs /tmp` per wrap breaks
    it: the inner command sees an empty directory and the fixture is gone.
  * **A pinned test is read-only.** A shell inside the wrap cannot rewrite a
    collected test file; the write comes back `EROFS`, which is the mount table
    doing the lane's work.
  * **The checkout is still writable.** A file at the root of the checkout is
    written without complaint. A sandbox that refuses everything holds the lane
    by holding nothing, and passes the rule above for the wrong reason.

Each command runs under `timeout` and dies with its parent, so a wrap that
hangs costs this gate its wall time and nothing else.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

HOOKS = Path(__file__).resolve().parents[2] / "hooks"

#: no probe here does work; a wrap that has not answered in this long is stuck
TIMEOUT = 60

#: what a runner collects, and what a shell therefore may not rewrite
PINNED = "test_pinned.py"

#: written by the outer wrap and read by the inner one
FIXTURE = "gauntlet-scale-probe"


def _load(name: str) -> ModuleType:
    """Import one hook module by path, since the hook names are hyphenated."""
    path = HOOKS / f"{name}.py"
    if str(HOOKS) not in sys.path:
        sys.path.insert(0, str(HOOKS))
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"no importable module at {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run(command: str) -> subprocess.CompletedProcess[str]:
    """Run one already-wrapped command through `bash`, bounded."""
    return subprocess.run(
        ["bash", "-c", command],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
        check=False,
    )


def checkout(root: Path, lane: str) -> None:
    """Write one checkout: a tests lane holding a collected file, and a git dir."""
    (root / lane).mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)
    (root / lane / PINNED).write_text("# pinned\n", encoding="utf-8")


def probes(wrap: ModuleType, root: str, lane: str) -> dict[str, subprocess.CompletedProcess[str]]:
    """Run every probe against one checkout, name to the process that answered."""
    inner = wrap.wrap(f"cat /tmp/{FIXTURE}", root, "")
    return {
        "runs": run(wrap.wrap("pwd", root, "")),
        "nested": run(wrap.wrap(f"echo fixture > /tmp/{FIXTURE}\n{inner}", root, "")),
        "pinned": run(wrap.wrap(f"echo x >> {lane}/{PINNED}", root, "")),
        "writable": run(wrap.wrap("echo x > scratch.txt", root, "")),
    }


def judge(root: str, answered: dict[str, subprocess.CompletedProcess[str]]) -> list[str]:
    """Why the wrap cannot stand, if it cannot. Every rule, every run."""
    runs = answered["runs"]
    nested = answered["nested"]
    pinned = answered["pinned"]
    writable = answered["writable"]
    problems = []
    if runs.returncode != 0 or runs.stdout.strip() != str(Path(root).resolve()):
        problems.append(
            f"a wrapped `pwd` answered {runs.returncode} with {runs.stdout.strip()!r}: "
            f"{runs.stderr.strip().splitlines()[-1] if runs.stderr.strip() else 'no output'}"
        )
    if nested.returncode != 0 or "fixture" not in nested.stdout:
        problems.append(
            "a nested wrap cannot read what the outer wrap wrote to scratch: "
            f"{nested.stderr.strip().splitlines()[-1] if nested.stderr.strip() else 'no output'}. "
            "A fixture built by one wrapped command is invisible to the next"
        )
    if pinned.returncode == 0 or "Read-only file system" not in pinned.stderr:
        problems.append(
            f"a shell rewrote a collected test file: exit {pinned.returncode}, "
            f"{pinned.stderr.strip()!r}. The lane is held by the mount table or by nothing"
        )
    if writable.returncode != 0:
        problems.append(
            f"a shell cannot write beside the lane: exit {writable.returncode}, "
            f"{writable.stderr.strip()!r}. A suite cannot run in this sandbox at all"
        )
    return problems


def check() -> int:
    """Execute the live hook's wrap against a real checkout, and read the processes."""
    wrap = _load("bwrap-wrap")
    lane_config = _load("lane_config")
    fault = _load("bwrap_probe").bwrap_fault()
    if fault is not None:
        print(fault)
        print("\n1 problem(s). bwrap does not run here, so every wrapped Bash call dies.")
        return 1

    with tempfile.TemporaryDirectory() as name:
        root = Path(name).resolve()
        lane = lane_config.tests_dir()
        checkout(root, lane)
        problems = judge(str(root), probes(wrap, str(root), lane))

    for problem in problems:
        print(problem)
    if problems:
        print(f"\n{len(problems)} problem(s). The wrap is judged by what it does, not by its text.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from wrap_runtime_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
