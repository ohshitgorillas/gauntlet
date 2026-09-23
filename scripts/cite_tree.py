#!/usr/bin/env python3
"""The file listing behind `cite.py`: what git shows in a checkout, and every
path in it carrying a basename, so a bare basename resolves to one file or is
`AMBIGUOUS`."""

import subprocess
from pathlib import Path

SKIP = {".git", ".venv", ".pytest_cache", "node_modules", "__pycache__"}


def _ls(at: Path | str, *args: str) -> subprocess.CompletedProcess[str]:
    """`git ls-files -z` run at `at`; a failure is its return code, never a raise."""
    cmd = ["git", "-C", str(at), "ls-files", "-z", *args]
    return subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)


def candidates(name: str, root: Path) -> list[Path]:
    """Every path carrying that basename: what git shows, ignored files out, or a walk."""
    git = _ls(root, "--cached", "--others", "--exclude-standard")
    shown = (root / n for n in git.stdout.split("\0") if n and Path(n).name == name)
    hits = []
    for path in root.rglob(name) if git.returncode else shown:
        #: relative to root: a root that is itself a worktree searches its own tree
        parts = path.relative_to(root).parts
        if any(part in SKIP for part in parts):
            continue
        if "worktrees" in parts:
            continue  # a worktree carries a second copy of every path in the tree
        if path.is_file():
            hits.append(path)
    return sorted(hits)
