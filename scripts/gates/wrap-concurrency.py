#!/usr/bin/env python3
"""Gate: two wrapped sessions in two worktrees share nothing and race nothing.

    scripts/gates/wrap-concurrency.py [--check]
    scripts/gates/wrap-concurrency.py --self-test

The scratch directory a wrapped shell sees at `/tmp` is one directory per
checkout, keyed by where that checkout resolves. That key is what makes a
fixture survive a nested wrap, and it is also the whole of the isolation
between two sessions: nothing is passed between the processes, so a key that
collides puts one session's scratch under the other's feet, and a key that is
recomputed per wrap puts each wrapped command in a directory of its own.

Two sessions in two worktrees is the shape a paired run takes, and the chain
cuts those worktrees side by side under one main checkout. So the gate builds
two of them and executes four probes:

  * **No bleed.** A file one tree's wrap writes to scratch is absent from the
    other tree's wrap. Two sessions reading one another's scratch is two agents
    sharing a working directory they each believe is private.
  * **Sharing holds inside one tree.** A second wrapped command at the *same*
    tree, a separate process and no descendant of the first, reads that file
    back. Isolation that also separates a tree from itself has taken the
    nesting guarantee away to get here.
  * **No cross-tree write.** A wrap in one tree cannot write into the other's
    checkout. Each session's writable set is its own tree.
  * **No race.** `RACERS` wraps at one tree, started together, all exit 0. The
    scratch directory is created by whichever arrives first, and a creation
    that is not idempotent fails the rest.

The racing wraps run `pwd` and nothing else, so the load is `RACERS` short-lived
processes at `WORKERS` at a time.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType

HOOKS = Path(__file__).resolve().parents[2] / "hooks"

#: no probe here does work; a wrap that has not answered in this long is stuck
TIMEOUT = 60

#: how many wraps start at one tree at once, and how many run at a time
RACERS = 8
WORKERS = max(1, min(4, (os.cpu_count() or 2) // 2))

#: written to scratch by the first tree, and looked for from both
TOKEN = "gauntlet-concurrency-probe"

#: what one tree writes into it, so a stale file cannot pass for a fresh one
WORD = "first-tree"

#: what a write to a read-only mount says on the way out
EROFS = "Read-only file system"

#: where the two trees are built, and why it is here rather than under the
#: host's `/tmp`: a wrapped shell sees one bound scratch directory at `/tmp` and
#: nothing else of the host's, so a checkout built there is absent inside the
#: sandbox and every probe answers `ENOENT` instead of the question it was
#: asked. `state/` is this repository's own scratch, visible through the
#: read-only world bind and writable to neither probe session.
BASE = Path(__file__).resolve().parents[2] / "state"


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


def trees(base: Path) -> tuple[str, str]:
    """Two worktrees cut side by side under one main checkout, absolute."""
    main = base / "project"
    cut = main / ".claude" / "worktrees"
    made = []
    for name in ("probe-spec", "probe-impl"):
        tree = cut / name
        (tree / "tests").mkdir(parents=True, exist_ok=True)
        (tree / ".git").write_text(f"gitdir: {main}/.git\n", encoding="utf-8")
        made.append(str(tree))
    (main / ".git").mkdir(parents=True, exist_ok=True)
    return made[0], made[1]


def race(wrap: ModuleType, tree: str) -> list[subprocess.CompletedProcess[str]]:
    """`RACERS` wraps at one tree, started together, in the order they finished."""
    commands = [wrap.wrap("pwd", tree, "") for _ in range(RACERS)]
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        return list(pool.map(run, commands))


def probes(wrap: ModuleType, one: str, other: str) -> dict[str, subprocess.CompletedProcess[str]]:
    """Run every probe against two trees, name to the process that answered."""
    run(wrap.wrap(f"echo {WORD} > /tmp/{TOKEN}", one, ""))
    return {
        "shared": run(wrap.wrap(f"cat /tmp/{TOKEN}", one, "")),
        "bleed": run(wrap.wrap(f"cat /tmp/{TOKEN}", other, "")),
        "cross": run(wrap.wrap(f"echo x > {one}/tests/crossed.py", other, "")),
    }


def _tail(done: subprocess.CompletedProcess[str]) -> str:
    """The shortest decisive line of one answer."""
    text = done.stderr.strip() or done.stdout.strip()
    return text.splitlines()[-1] if text else "no output"


def judge(
    answered: dict[str, subprocess.CompletedProcess[str]],
    raced: list[subprocess.CompletedProcess[str]],
) -> list[str]:
    """Why two wrapped sessions cannot stand beside each other, if they cannot."""
    shared = answered["shared"]
    bleed = answered["bleed"]
    cross = answered["cross"]
    problems = []
    if shared.returncode != 0 or WORD not in shared.stdout:
        problems.append(
            f"a second wrap at one tree cannot read that tree's scratch: {_tail(shared)!r}. "
            "Every wrapped command gets a scratch directory of its own"
        )
    if bleed.returncode == 0 or WORD in bleed.stdout:
        problems.append(
            "one tree's wrap reads the other tree's scratch. Two sessions share a "
            "directory each believes is private"
        )
    if cross.returncode == 0 or EROFS not in cross.stderr:
        problems.append(
            f"a wrap in one tree wrote into the other tree: exit {cross.returncode}, "
            f"{_tail(cross)!r}. A session's writable set is not its own"
        )
    lost = [done for done in raced if done.returncode != 0]
    if lost:
        problems.append(
            f"{len(lost)} of {len(raced)} wraps started together failed: {_tail(lost[0])!r}. "
            "The scratch directory is made by whoever arrives first, and once"
        )
    return problems


def check() -> int:
    """Execute the live hook's wrap from two trees at once, and read the processes."""
    wrap = _load("bwrap-wrap")
    fault = _load("bwrap_probe").bwrap_fault()
    if fault is not None:
        print(fault)
        print("\n1 problem(s). bwrap does not run here, so every wrapped Bash call dies.")
        return 1

    BASE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=BASE, prefix="races-") as name:
        one, other = trees(Path(name).resolve())
        problems = judge(probes(wrap, one, other), race(wrap, one))

    for problem in problems:
        print(problem)
    print(f"2 tree(s), {RACERS} wrap(s) raced at {WORKERS} at a time")
    if problems:
        print(f"\n{len(problems)} problem(s). Two sessions share their host and nothing else.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from wrap_concurrency_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
