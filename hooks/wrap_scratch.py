"""The scratch directory a checkout's wrapped shells share, as mount arguments.

`/tmp` inside a wrap is a bind of one directory, not a mask. A tmpfs is the
right answer for one command and the wrong one for two: a suite builds a tree
in one wrapped command and runs a second wrapped command against it, and a
fresh tmpfs per wrap means the inner wrap mounts its own empty directory over
the first one's work. The tree is not merely unwritable there, it is absent.

That absence is what pushes such a tree inside the checkout, and a lane holding
one cannot be bound read-only whole, so it is bound file by file instead. A
consumer with 387 collected files then takes 387 binds and 54,944 characters in
one `bwrap` argument, and the kernel refuses a single argument past
`MAX_ARG_STRLEN`:

    Could not start /usr/bin/zsh: the command line plus environment exceed the
    OS exec argument limit (E2BIG).

So the mask is a bind. One directory per checkout, keyed by where the checkout
resolves, so every wrap of one tree agrees on it without passing anything
between processes. Two checkouts share nothing, and the host's own `/tmp` is
not written through: a wrapped shell sees this directory as `/tmp` and sees
nothing else of the host's.

It binds over itself at `/tmp/<its own name>` as well, and that second bind is
the mountpoint the *next* wrap down needs. Inside the sandbox the host spelling
of the directory is gone, so a nested wrap resolving its own source finds
nothing and drops the bind. With the self-bind the same directory answers at
the same path at any depth.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path, PurePosixPath
from tempfile import gettempdir

#: how one checkout's scratch directory is named on the host
PREFIX = "gauntlet-scratch-"

#: where a wrapped shell sees it
MOUNT = "/tmp"

#: the mode it is created with: one checkout's scratch is not another user's
MODE = 0o700


def directory(root: str) -> str:
    """The scratch directory this checkout's wraps share, created if it is absent.

    The nested mountpoint inside it is created at the same time, since a wrap
    that cannot resolve it silently loses the sharing this exists to give.
    """
    key = sha256(str(Path(root).resolve()).encode("utf-8")).hexdigest()[:12]
    scratch = Path(gettempdir()) / f"{PREFIX}{key}"
    (scratch / scratch.name).mkdir(parents=True, exist_ok=True)
    scratch.chmod(MODE)
    return str(scratch)


def mounts(root: str) -> list[str]:
    """The `bwrap` arguments that put one checkout's scratch at `/tmp`, nestably."""
    scratch = directory(root)
    return [
        "--bind",
        scratch,
        MOUNT,
        "--bind",
        scratch,
        str(PurePosixPath(MOUNT) / Path(scratch).name),
    ]
