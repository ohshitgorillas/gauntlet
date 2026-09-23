"""The paths a project declares writable on top of the checkout, filtered.

Every path outside the checkout is already readable through `--ro-bind / /`, so
`extra_binds` adds one thing: a writable path in no lane, held until now by the
sandbox alone. What this module decides is which declared entries survive the
guards the profile is built on -- the answer is a list of paths, and the hook
that asked emits the binds.

Drops are silent and per entry, because an entry that voids the mount table
costs the session every `Bash` call rather than one path. A path that is not
absolute names nothing here -- `~` with no `HOME` arrives that way. A path
standing over one the profile guards is dropped from either side, since an
ancestor reaches a lane or remounts a mask exactly as a descendant does. Two
entries naming one path bind once.

`/tmp` is guarded from one side only: it is the checkout's own scratch
directory rather than a route out, so a declared path under it is the hole this
key exists to make. The mountpoint itself still drops.

Comparison runs on resolved paths, so a symlinked entry is judged by where it
lands; the path comes back at the entry's own spelling, which is the name a
shell inside the wrap will use.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import lane_config  # noqa: E402
import lane_paths  # noqa: E402

#: masked or bound by the profile itself, and reachable from either side
GUARDED = ("/dev", "/proc", "/run/user")

#: guarded from one side only: a declared path under it is the point of the key
SCRATCH = ("/tmp",)


def stands_over(one: str, other: str) -> bool:
    """Is `one` `other`, or an ancestor or a descendant of it? Resolved paths."""
    return one == other or one.startswith(other + "/") or other.startswith(one + "/")


def paths(root: str, trees: list[str]) -> list[str]:
    """Every declared path that survives the guards, in declaration order, once each."""
    home = os.environ.get("HOME") or root
    protected = [*GUARDED, str(Path(home) / ".gitconfig"), root, *trees]
    guarded = [lane_paths.real_path(one, root) for one in protected]
    scratch = [lane_paths.real_path(one, root) for one in SCRATCH]
    kept: list[str] = []
    bound: set[str] = set()
    for entry in lane_config.extra_binds():
        if not Path(entry).is_absolute():
            continue
        target = lane_paths.real_path(entry, root)
        if any(stands_over(target, one) for one in guarded):
            continue
        if any(target == one or one.startswith(target + "/") for one in scratch):
            continue
        if target in bound:
            continue
        bound.add(target)
        kept.append(entry)
    return kept
