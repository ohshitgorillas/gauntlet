"""Git half of the fence's `commit` tool (runtime-model-design.md, "Commit model").

Takes everything it needs as arguments, so it imports nothing from files.py."""

import fcntl
import os
import subprocess
from collections.abc import Callable

LOCK = "gauntlet-commit.lock"
HOOKS = ("pre-commit", "prepare-commit-msg", "commit-msg")


def _git(root: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", root, *args],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=check,
    )


def _specs(paths: list[str]) -> list[str]:
    return [f":(literal){p}" for p in paths]


def _covers(listed: list[str], path: str) -> bool:
    return any(p == "." or path == p or path.startswith(p + "/") for p in listed)


def _status(root: str, prefix: str, paths: list[str]) -> list[str]:
    """Paths `git status --porcelain -z -uall` names as changed, relative to root."""
    out = _git(
        root, "status", "--porcelain", "-z", "-uall", "--", *_specs(paths)
    ).stdout
    records = iter(out.split("\0"))
    names = []
    for rec in records:
        if len(rec) < 4:
            continue
        names.append(rec[3:])
        if "R" in rec[:2] or "C" in rec[:2]:
            names.append(next(records, ""))
    return [n.removeprefix(prefix) for n in names if n]


def _snapshot(root: str, paths: list[str]) -> tuple[str, str]:
    status = _git(root, "status", "--porcelain", "-z", "-uall", "--", *_specs(paths))
    diff = _git(root, "diff", "--binary", "HEAD", "--", *_specs(paths), check=False)
    return status.stdout, diff.stdout


def _hooks(root: str) -> list[str]:
    folder = os.path.join(
        root, _git(root, "rev-parse", "--git-path", "hooks").stdout.strip()
    )
    return [
        h
        for h in HOOKS
        if os.path.isfile(os.path.join(folder, h))
        and os.access(os.path.join(folder, h), os.X_OK)
    ]


def _commit_changed(root: str, message: str, changed: list[str]) -> str:
    for attempt in (1, 2):
        _git(root, "add", "-A", "--", *_specs(changed))
        before = _snapshot(root, changed)
        done = _git(
            root, "commit", "--only", "-m", message, "--", *_specs(changed), check=False
        )
        if done.returncode == 0:
            head = _git(root, "rev-parse", "HEAD").stdout.strip()
            return f"exit=0 commit={head}"
        if attempt == 2 or _snapshot(root, changed) == before:
            break
    return " ".join([f"exit={done.returncode}", *_hooks(root)])


def commit(
    root: str,
    message: str,
    paths: list[str],
    recorded: set[str],
    check: Callable[[str], object],
) -> str:
    """Commit the changed ones of `paths` (relative to root, already fence-checked).
    Raises ValueError when a path in `recorded` is changed and not covered by
    `paths`; `check` raises PermissionError for a changed path the fence refuses. A git
    command other than `commit` that fails raises CalledProcessError."""
    specs = sorted(set(paths) | recorded)
    if not specs:
        return "exit=0 nothing"
    gitdir = _git(root, "rev-parse", "--git-dir").stdout.strip()
    prefix = _git(root, "rev-parse", "--show-prefix").stdout.strip()
    with open(os.path.join(root, gitdir, LOCK), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        seen = _status(root, prefix, specs)
        left_out = [p for p in seen if p in recorded and not _covers(paths, p)]
        if left_out:
            raise ValueError(f"changed but not in paths: {', '.join(left_out)}")
        changed = [p for p in seen if _covers(paths, p)]
        if not changed:
            return "exit=0 nothing"
        for p in changed:
            check(p)
        return _commit_changed(root, message, changed)
