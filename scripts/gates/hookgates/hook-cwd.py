#!/usr/bin/env python3
"""Gate: a lane holds from whatever working directory the call arrives in.

    scripts/gates/hookgates/hook-cwd.py [--check]
    scripts/gates/hookgates/hook-cwd.py --self-test

A lane verdict is a question about a path, and the path is half a spelling and
half a `cwd`. The host sends the working directory of the moment: a subdirectory
the agent walked into, a worktree the chain cut, a route through a symlink, a
checkout sitting at a detached head, or a directory that is no checkout at all.
Each of those resolves to a different string, and a lane that holds for one
spelling and not for the next guards nothing.

So the gate builds those five shapes as real directories and drives the real
`lanes.py` against each one twice: a write into the tests lane, which every
shape must refuse, and a write beside it, which every shape must let through.
An answer that is a traceback is a third failure, counted as its own.

The lane and the file the control write names are read from `lane_config`, so a
project that declares another directory is measured against the one it declared.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(ROOT / "hooks" / "lib"))

import lane_config  # noqa: E402

HOOK = ROOT / "hooks" / "lanes.py"

#: a hook that has not decided one write by now is not slow, it is stuck
TIMEOUT = 30

#: what a crash looks like on the way out
CRASH = "Traceback (most recent call last)"

#: a directory no lane claims, for the write every shape has to let through
OPEN_DIR = "src"

#: the file each shape tries to write inside the lane, and beside it
LEAF = "shape_probe.py"


def _git(root: Path, *args: str) -> None:
    """One git command in `root`, quiet, raising if git refuses it."""
    subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


def checkout(base: Path) -> Path:
    """A throwaway checkout carrying a lane, an open directory and one commit."""
    root = base / "project"
    for relative in (lane_config.tests_dir(), OPEN_DIR, "docs"):
        (root / relative).mkdir(parents=True, exist_ok=True)
        (root / relative / "kept.txt").write_text("kept\n", encoding="utf-8")
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "gate@example.invalid")
    _git(root, "config", "user.name", "gate")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    return root


def shapes(base: Path) -> dict[str, tuple[str, str]]:
    """The five shapes this gate asks about: name to `(cwd, prefix)`.

    The prefix is how that working directory spells the checkout it sits in,
    so the subdirectory shape reaches its lane by walking up rather than by a
    name that would land in a second directory of the same leaf.

    Each one is built rather than spelled, so what the hook resolves is what the
    filesystem holds: a real worktree, a real symlink, a real detached head.
    """
    root = checkout(base)
    lane = lane_config.tests_dir()

    tree = root / ".claude" / "worktrees" / "probe-impl"
    tree.parent.mkdir(parents=True, exist_ok=True)
    _git(root, "worktree", "add", "-q", "-b", "probe", str(tree))
    (tree / lane).mkdir(parents=True, exist_ok=True)

    link = base / "by-symlink"
    link.symlink_to(root, target_is_directory=True)

    detached = base / "detached"
    _git(root, "worktree", "add", "-q", "--detach", str(detached), "HEAD")
    (detached / lane).mkdir(parents=True, exist_ok=True)

    loose = base / "loose" / lane
    loose.mkdir(parents=True, exist_ok=True)

    return {
        "a subdirectory of the checkout": (str(root / "docs"), "../"),
        "a worktree the chain cut": (str(tree), ""),
        "a route through a symlink": (str(link), ""),
        "a checkout at a detached head": (str(detached), ""),
        "a directory that is no checkout": (str(loose.parent), ""),
    }


def answer(cwd: str, target: str, hook: Path = HOOK) -> tuple[str, str]:
    """What `lanes.py` says about one write from one working directory."""
    payload = {
        "tool_name": "Write",
        "tool_input": {"file_path": target, "content": ""},
        "cwd": cwd,
        "session_id": "hook-cwd",
    }
    environment = dict(os.environ)
    environment.pop("GAUNTLET", None)
    environment["CLAUDE_PLUGIN_ROOT"] = str(hook.parent.parent)
    try:
        done = subprocess.run(
            [sys.executable, str(hook)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        return "", f"did not answer in {TIMEOUT}s"
    return done.stdout, done.stderr


def denied(said: tuple[str, str]) -> bool:
    """Did the hook refuse this write?"""
    out, _ = said
    try:
        data = json.loads(out)
    except ValueError:
        return False
    specific = data.get("hookSpecificOutput") if isinstance(data, dict) else None
    if not isinstance(specific, dict):
        return False
    return specific.get("permissionDecision") == "deny"


def crashed(said: tuple[str, str]) -> bool:
    """Did the hook answer with a traceback, or not answer at all?"""
    out, err = said
    return CRASH in out or CRASH in err or err.startswith("did not answer")


def judge(name: str, inside: tuple[str, str], beside: tuple[str, str]) -> list[str]:
    """Why one working directory cannot stand, if it cannot."""
    problems = []
    for where, said in (("inside the lane", inside), ("beside the lane", beside)):
        if crashed(said):
            lines = (said[1] or said[0]).strip().splitlines()
            last = lines[-1] if lines else "no output at all"
            problems.append(f"{name}: a write {where} answered with a crash, {last!r}")
    if not crashed(inside) and not denied(inside):
        problems.append(f"{name}: a write into the lane was allowed. The lane does not hold here")
    if not crashed(beside) and denied(beside):
        problems.append(f"{name}: a write beside the lane was refused. The lane reaches too far")
    return problems


def readings(base: Path) -> dict[str, list[str]]:
    """Every shape driven twice, name to what cannot stand about it."""
    lane = lane_config.tests_dir()
    out = {}
    for name, (cwd, prefix) in shapes(base).items():
        inside = answer(cwd, f"{prefix}{lane}/{LEAF}")
        beside = answer(cwd, f"{prefix}{OPEN_DIR}/{LEAF}")
        out[name] = judge(name, inside, beside)
    return out


def check() -> int:
    """Drive the lane hook from every working-directory shape, and refuse a hole."""
    with tempfile.TemporaryDirectory(prefix="hook-cwd-") as base:
        scored = readings(Path(base))

    problems = [problem for found in scored.values() for problem in found]
    for problem in problems:
        print(problem)
    for name in scored:
        print(f"{'FAIL' if scored[name] else 'ok  '}  {name}")
    if problems:
        print(f"\n{len(problems)} problem(s). A lane is a question about a path, from anywhere.")
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Check the tree the gate is run in."""
    del argv
    return check()


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from hook_cwd_selftest import self_test

        sys.exit(self_test())
    sys.exit(main(sys.argv))
