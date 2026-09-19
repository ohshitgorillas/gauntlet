"""The path shapes the lane hooks share, and the owner's off switch.

The lane hooks all ask the same question: does this path fall inside a
directory that belongs to one agent. This module answers it, so that a hook is
a policy over the answer rather than a second parser.

No shell command is read here. This module carried a classifier once -- a
reader allowlist, a runner table, a redirection scanner, a git form test --
and every lane hook decided a `Bash` call through it. That half is gone with
the hooks' `Bash` matchers: what holds a shell out of a lane is the mount
table `bwrap-wrap.py` builds, which binds every lane directory read-only
inside every wrapped profile. A command that names a lane is not parsed for
the name any more; it fails in the kernel or it does not touch the lane.

What is left of the shell side is `TESTPATH`, the shape of the one argument
`blind-bash.py` admits after `scripts/blind.sh test`. It is a path shape, not
a command shape: the test directory as configured, optionally under one spec
worktree, matched whole and matched again after `os.path.normpath`, so an
argument that opens under the lane and walks out of it is not that shape.

The owner's off switch lives here too, as `bypassed()`. It reads `os.environ`
and never a hook payload: the payload is the one input an agent controls, and a
switch honouring a payload key would be a bypass any subagent could forge in a
tool call.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from lane_config import tests_dir

#: a slug names one path segment and carries no traversal
SLUG = r"[A-Za-z0-9][A-Za-z0-9._-]*"
#: a spec worktree is the other place a blind agent's tests live, so the blind
#: runner's argument may carry that one prefix and no other: the writer runs
#: the suite in the tree it wrote in
TREE = rf"\.claude/worktrees/{SLUG}-spec/"


def path_shape(prefix: str) -> str:
    """The regex source a path prefix expands into.

    Repo-relative, under `prefix`, optionally inside a spec worktree. The
    trailing class admits `.` and `/`, so it admits `..` as well: the shape is
    not the whole key, and `is_blind_run` normalizes what it matches.
    """
    return rf"(?:{TREE})?{re.escape(prefix)}/[A-Za-z0-9_][A-Za-z0-9._/-]*"


#: the shape the blind runner's one argument takes, exported so that
#: `blind-bash.py` reads the same regular expression the classifier does
TESTPATH = path_shape(tests_dir())


_TESTPATH_WHOLE = re.compile(TESTPATH + r"\Z")


#: a write stage whose targets this parser cannot name. `STAGE` is an
#: interpreter handed a script: the paths are computed inside the script, so
#: there is no target to test and the stage is denied. `STDIN` is `xargs`: the
#: paths were produced upstream, so the evidence is the whole command and not
#: this stage.
STAGE, STDIN = "stage", "stdin"


def checkout_root(path: str) -> str | None:
    """The checkout (main or worktree) containing `path`, by walking up to a `.git`."""
    while True:
        if Path(path, ".git").exists():
            return path
        parent = str(Path(path).parent)
        if parent == path:
            return None
        path = parent


def root_by_name(path: str) -> str | None:
    """A checkout root read off the path alone, for trees that need not exist.

    `.claude/worktrees/<slug>-spec` and `-impl` are roots by construction; the
    directory holding `.claude/worktrees` is the main checkout.
    """
    parts = Path(path).parts
    for i in range(len(parts) - 1, 1, -1):
        if parts[i - 2] == ".claude" and parts[i - 1] == "worktrees":
            return str(Path(*parts[: i + 1]))
    return None


def real_path(target: str, cwd: str) -> str:
    """One absolute path for `target`, with every symlink on it followed.

    Both sides of every lane comparison come through here, so a symlinked
    file, a symlinked parent directory, a relative spelling and a `..` walk all
    collapse onto the one name the kernel will open. A lexical answer is a
    different answer for each of those spellings, and a lane that admits one
    spelling of a file and refuses another guards nothing.

    `os.path.realpath` resolves the longest prefix that exists and rejoins the
    tail lexically, which is what a write to a file whose parent does not exist
    yet needs: the nearest existing ancestor is resolved and the rest is
    carried.

    LIMIT, left open on purpose: `realpath` does not resolve a hardlink, and
    cannot -- a hardlink is a second name of equal standing, not a pointer. A
    second name for a lane file, made under another directory, resolves to
    itself and is admitted. Closing it means comparing `st_dev`/`st_ino`
    against the lane's contents, which costs a `stat` per call and per lane
    file; the owner decides whether the lane is worth that, and until then the
    hole is here rather than hidden.
    """
    return os.path.realpath(os.path.join(cwd, target))  # noqa: PTH118


def split_root(target: str, cwd: str) -> tuple[str | None, str | None]:
    """(checkout root, path relative to it) for a write target, or (None, None).

    The target is resolved first, so the root is the checkout the write really
    lands in rather than the one its spelling suggests. Every ancestor of a
    resolved path is itself resolved, so the root needs no second pass.
    """
    real = real_path(target, cwd)
    root = root_by_name(real) or checkout_root(str(Path(real).parent))
    if root is None:
        return None, None
    return root, os.path.relpath(real, root)


def under(rel: str, lane: str) -> bool:
    """Is this path the lane directory or inside it? Both sides spelled alike.

    Two repo-relative paths, or two resolved absolute ones. Never one of each.
    """
    prefix = lane.replace("/", os.sep)
    return rel == prefix or rel.startswith(prefix + os.sep)


def path_in_lane(target: str, cwd: str, lane: str) -> bool:
    """Does the resolved target land inside a `<lane>` directory of any checkout?

    Both sides are resolved. Resolving the target alone answers a symlink that
    points into the lane; resolving the lane root as well answers the other
    direction, a lane directory that is itself a symlink and whose contents
    therefore sit somewhere the repo-relative path never shows.

    Falls back to a segment match when the path is in no checkout at all, so
    the lane holds before `git init` and outside a repo.
    """
    real = real_path(target, cwd)
    root, rel = split_root(target, cwd)
    if root is not None and under(real, real_path(lane, root)):
        return True
    if rel is not None and not rel.startswith(".."):
        return under(rel, lane)
    parts = list(Path(real).parts)
    lane_parts = lane.split("/")
    return any(
        parts[i : i + len(lane_parts)] == lane_parts
        for i in range(len(parts) - len(lane_parts) + 1)
    )


def bypassed() -> bool:
    """Whether the owner started this session with the gauntlet off.

    `GAUNTLET=off claude`, and nothing else. The comparison is against the
    exact value `off` after strip and lowercase, so an unset, empty or
    misspelled variable leaves the gauntlet on, which is the safe direction.

    Read only at the top of a hook's `main()`, never inside a `_verdict()`: a
    self-test calls `_verdict()` directly, and a switch reachable from there
    would make the self-tests pass vacuously in a bypassed environment.
    """
    return os.environ.get("GAUNTLET", "").strip().lower() == "off"
