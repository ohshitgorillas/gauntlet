#!/usr/bin/env python3
"""PreToolUse hook: every `Bash` command runs inside `bwrap`, unread.

This is the mechanism that stands in place of reading command text. Deciding a
`Bash` call by parsing the string -- does this command write, and where -- is
undecidable on a string: an env prefix, a here-document, a command
substitution, a shell function, a `find -exec`, an `xargs`. A list of spellings
leaves the next spelling open.

So nothing here parses. The command text is carried into the replacement byte
for byte and what changes is not the command but the filesystem it sees. A
write the sandbox refuses comes back as an ordinary errno rather than as a hook
denial with a paragraph of prose, which is a real loss of explanation and the
price of the mechanism. The `Write` and `Edit` paths keep their prose, and those
are the tools an agent should be using for a write.

The command is delivered on stdin through a here-document rather than as a
quoted argument. Quoting is the thing this hook exists not to do: a quoter has
to know the shape of what it is quoting, and `echo $(cat /etc/hostname) <<'X'`
survives `shlex.quote` only by being rewritten. A here-document carries any byte
sequence unaltered, so the caller's text appears in the replacement exactly as
typed, whatever it is.

Two profiles, chosen by `agent_type`, the same payload field the lane hooks
read. No caller is exempt and no command is: every `Bash` call is wrapped,
because exempting one would mean reading its text. An absent `agent_type` is
the main agent and takes the default profile like anyone else, so `sudo` stops
working in a shell and no sudoers file changes: `bwrap` sets NO_NEW_PRIVS, so
`sudo` inside the wrap fails with "The \"no new privileges\" flag is set", and
so does every script that calls `sudo` internally.

  * **reviewer** for the blind reviewers: the whole filesystem read-only, plus a
    tmpfs over the reviewers' own lane. A reviewer's shell cannot change the
    checkout it was spawned to judge.
  * **default** for every other caller, the main agent included. Everything
    readable.
    Writable: the repository, the checkout's shared scratch at `/tmp`, `~/.cache`, and every
    live path the project declares under `extra_binds` that stands over nothing
    the profile protects.
    Read-only again inside the repository: every lane directory in every checkout, `<gauntlet
    dir>/red`, `<gauntlet dir>/merge`, `.claude/`, `.git/hooks` and `.git/config`.
    `~/.gitconfig` is read-only. `/run/user` is masked with an empty tmpfs,
    which closes the D-Bus route to `systemd --user` -- a socket rather than a spelling, so no
    string classifier could ever have caught it.

`--unshare-pid` is taken, and what it buys is narrower than it looks. The route
out through an outer process's `/proc/<pid>/cwd` is closed either way, because
that process is outside the sandbox's user-namespace mapping; the flag removes
the entry rather than denying it, which is defense in depth against a future
kernel or mapping that would make the denial a permission rather than an
absence.

The worktree list is rebuilt on every call and never cached. `.claude/worktrees`
is itself read-only and each tree that exists is bound back writable, so a tree
cut since the last call is writable and a tree removed since the last call is
simply absent. A cached list would name a path that is gone, and `bwrap` fails
the whole invocation on a missing bind source -- every `Bash` call in the
session would error until the session restarted.

That failure mode is the hazard this hook has to answer, and `--ro-bind-try` is
not the answer: the `-try` suffix forgives a source that is *absent* and
nothing else. A source whose parent is a file, not a directory, comes back
`ENOTDIR` and kills the whole invocation -- which is exactly `.git/hooks` in a
git worktree, where `.git` is a pointer file rather than a directory. So every
bind source is resolved against the tree before it is emitted, by `_source`,
and a path that does not resolve is not named at all. `-try` stays on the
optional binds for the race between the check and the exec; it is a second
line, never the first.

Nothing about a checkout is assumed. A worktree's `.git/hooks` and `.git/config`
simply drop out of its profile, and the protection still holds, because a
worktree shares both with the main checkout whose copies are bound read-only.

`bwrap` being on `PATH` is not the same as `bwrap` working. A host with user
namespaces disabled, or a seccomp policy that refuses the setup, has the binary
and fails at exec -- and since every `Bash` call is rewritten into that
invocation, every `Bash` call in the session dies with `bwrap`'s own one-line
complaint and no statement of what refused it. So the binary is run once, on a
trivial profile, before anything is rewritten, and a host where it does not run
gets a named denial instead of a session of broken commands.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hook_payload  # noqa: E402
import hook_shape  # noqa: E402
import lane_config  # noqa: E402
import lane_declaration  # noqa: E402
import shell_binds  # noqa: E402
import wrap_extras  # noqa: E402
import wrap_scratch  # noqa: E402
from bwrap_probe import bwrap_fault  # noqa: E402

#: the blind reviewers: read-only everywhere, with a tmpfs over their own lane
REVIEWER_AGENTS = ("arbiter", "juror")

#: read-only again inside every checkout, on top of a writable repository.
#: `shell_binds.py` projects the lane table onto the mount table, one bind per
#: lane, so the table is the same size in any checkout.
PROTECTED_IN_CHECKOUT = shell_binds.PROTECTED_DIRS

#: the reviewers' own lane, which their profile answers with a tmpfs
REVIEWS_DIR = lane_config.reviews_lane()

WORKTREES = ".claude/worktrees"


def _answer(payload: dict[str, Any]) -> dict[str, Any] | None:
    """The hook's answer for this payload, or None to say nothing at all."""
    if payload.get("tool_name") != "Bash":
        return None
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str):
        return None

    # `agent_type` picks a profile; it never admits a caller. An absent one is
    # the main agent and takes the default profile, so `sudo` in a shell dies
    # at NO_NEW_PRIVS for the main agent exactly as for anyone else.
    agent = hook_payload.agent_of(payload)
    cwd = str(Path(hook_payload.cwd_of(payload)).resolve())

    # the checkout is the root, never the directory the caller stands in: a
    # shell standing in a lane that took itself for the root would bind that
    # lane writable, and one standing above the checkout would bind every lane
    found = lane_declaration.checkout_of(Path(cwd))
    if found is None:
        return _deny(hook_payload.undecidable(f"the cwd {cwd} sits in no git checkout"))
    root = str(found[0])

    fault = bwrap_fault()
    if fault is not None:
        return _deny(fault)

    wrapped = wrap(command, root, agent, cwd)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {"command": wrapped},
        }
    }


def _deny(reason: str) -> dict[str, Any]:
    """The answer refusing this call, for `reason`."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def worktrees(root: str) -> list[str]:
    """The worktrees that exist under `root` right now, absolute, sorted.

    Rebuilt per call on purpose. A cached list outlives the tree it names, and
    `bwrap` fails the whole invocation on a bind source that is not there.
    """
    parent = Path(root) / WORKTREES
    try:
        trees = sorted(parent.iterdir())
    except OSError:
        return []
    return [str(tree) for tree in trees if tree.is_dir()]


def _base(root: str, cwd: str | None) -> list[str]:
    """The mounts every profile takes: readable world, live /dev, shared scratch.

    The shell starts where the caller stands, `cwd`, and in `root` where the
    caller names nowhere or stands somewhere that is gone.
    """
    start = cwd if cwd is not None and _source(cwd) else root
    return (
        [
            "bwrap",
            "--ro-bind",
            "/",
            "/",
            "--dev",
            "/dev",
            "--proc",
            "/proc",
            # the D-Bus route to `systemd --user`, which starts a unit outside
            # anything the calling process was confined by
            "--tmpfs",
            "/run/user",
            "--unshare-pid",
            "--die-with-parent",
            # one scratch directory per checkout, bound rather than masked, so a
            # nested wrap resolves what the wrap around it wrote
        ]
        + wrap_scratch.mounts(root)
        + (
            # a `--chdir` onto a directory that is not there fails the invocation,
            # and a caller's `cwd` can name a tree that has since been cut
            ["--chdir", start]
            if _source(start)
            else []
        )
    )


def _source(path: str) -> bool:
    """Whether `path` is a bind source `bwrap` will accept, right now.

    `Path.exists` answers False for every reason a bind would fail on the
    source -- absent, a component that is a file (`ENOTDIR`), a dangling
    symlink, a directory that cannot be traversed -- which is the whole of what
    this needs to know. `--ro-bind-try` forgives only the first of those.
    """
    return Path(path).exists()


def _bind(flag: str, path: str) -> list[str]:
    """One bind of `path` onto itself, or nothing if the source is not there."""
    return [flag, path, path] if _source(path) else []


def _checkout_readonly(checkout: str) -> list[str]:
    """Bind back read-only the directories no shell writes, in one checkout.

    A path that does not resolve is not named. In a worktree that drops
    `.git/hooks` and `.git/config`, which the worktree shares with the main
    checkout and which the main checkout's own profile has already bound.
    """
    args: list[str] = []
    for path in shell_binds.readonly_paths(checkout):
        args += _bind("--ro-bind-try", path)
    return args


def _extra_binds(root: str) -> list[str]:
    """The paths the project declares writable on top of the checkout.

    `wrap_extras` decides which declarations survive the profile's guards; what
    is left is bound here, at the spelling the project used.
    """
    args: list[str] = []
    for entry in wrap_extras.paths(root, worktrees(root)):
        args += _bind("--bind-try", entry)
    return args


def wrap(command: str, root: str, agent: str, cwd: str | None = None) -> str:
    """The `bwrap` invocation that runs `command`, as one shell command string.

    `root` is the main checkout, and everything the profile binds keys on it;
    `cwd` is only where the shell starts. A tree that is neither `root` nor
    under its worktrees is bound by nothing here, so it stays read-only
    through the root mount.

    The caller's text is carried on stdin through a here-document, so it appears
    in the result byte for byte however it is spelled.
    """
    args = _profile(root, agent, cwd)
    return " ".join(_quote(a) for a in args) + " " + _heredoc(command)


def _profile(root: str, agent: str, cwd: str | None) -> list[str]:
    """The full `bwrap` argument list for one agent in one checkout."""
    home = os.environ.get("HOME") or root
    args = _base(root, cwd)

    if agent in REVIEWER_AGENTS:
        # nothing writable but the reviewer's own lane, and that only as a
        # tmpfs: a reviewer's shell cannot change the checkout it judges
        # a tmpfs needs its mountpoint to exist: everything else is bound
        # read-only, so `bwrap` cannot create one. A checkout without the
        # reviews lane gives the reviewer a wholly read-only filesystem, which
        # errs in the safe direction.
        reviews = str(Path(root) / REVIEWS_DIR)
        if _source(reviews):
            args += ["--tmpfs", reviews]
    else:
        args += _bind("--bind", root)
        args += _bind("--bind-try", str(Path(home) / ".cache"))
        args += _bind("--ro-bind-try", str(Path(home) / ".gitconfig"))

        # the repository is writable, so the lanes inside it are bound back
        # read-only, in the main checkout and in every worktree
        args += _checkout_readonly(root)
        args += _bind("--ro-bind-try", str(Path(root) / WORKTREES))
        for tree in worktrees(root):
            # `--bind`, not `--bind-try`, would stake the whole invocation on a
            # tree surviving the microseconds between the listing above and the
            # exec. A tree cut in that window costs its own writability and
            # nothing else; under `--bind` it killed the command outright.
            args += _bind("--bind-try", tree)
            args += _checkout_readonly(tree)

        # the project's own writable paths: after the lanes, so a declaration
        # cannot walk one back
        args += _extra_binds(root)

    return args + ["--", "bash", "-s"]


def _quote(argument: str) -> str:
    """Quote one `bwrap` argument. Never the caller's command -- see `_heredoc`."""
    if argument and all(c.isalnum() or c in "-_/.:=" for c in argument):
        return argument
    return "'" + argument.replace("'", "'\\''") + "'"


def _heredoc(command: str) -> str:
    """`command` as a quoted here-document, so every byte of it survives.

    The delimiter is extended until it appears on no line of the command, so a
    command that happens to contain the delimiter cannot terminate it early.
    """
    delimiter = "GAUNTLET_COMMAND_EOF"
    lines = command.split("\n")
    while any(line.strip() == delimiter for line in lines):
        delimiter += "_"
    return f"<<'{delimiter}'\n{command}\n{delimiter}"


def main() -> None:
    #: a command is the only thing this hook wraps, so a `Bash` call is the only
    #: one it refuses for being unreadable. A wrap that cannot be built is a
    #: denial and not a shrug: the shrug runs the command outside the sandbox.
    hook_shape.answer_main(_answer, guards=("Bash",))


def self_test() -> int:
    """Pin what the wrap carries, what it binds, and every way it can go wrong.

    Every profile is built against a real directory tree, not an invented path.
    The bug this pins was a path that resolved to something other than the
    profile assumed, and no assertion over a `/repo` that has never existed can
    see that class at all.
    """
    #: lazily, so the hook path never pays for the self-test's imports
    sys.modules.setdefault("bwrap-wrap", sys.modules[__name__])
    return int(importlib.import_module("bwrap_wrap_selftest").run())


if __name__ == "__main__":
    hook_shape.entry(self_test, main)
