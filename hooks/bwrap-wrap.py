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

Three profiles, chosen by `agent_type`, the same payload field the lane hooks
read. No caller is exempt. An absent `agent_type` is the main agent and takes
the default profile like anyone else, so `sudo` stops working in a shell and no
sudoers file changes: `bwrap` sets NO_NEW_PRIVS, so `sudo` inside the wrap fails
with "The \"no new privileges\" flag is set", and so does every script that
calls `sudo` internally. A project that needs one such command declares that
command by its exact text under `unwrapped_commands`; a project that declares
nothing has no privileged shell at all. A carve-out is a command, never a
caller.

  * **passthrough** for the two blind agents that keep a shell. `blind.sh` runs
    its own `bwrap`, and wrapping a wrapper gains nothing while costing a nested
    mount setup on the one command those agents have.
  * **reviewer** for the blind reviewers: the whole filesystem read-only, plus a
    tmpfs over the reviewers' own lane. A reviewer's shell cannot change the
    checkout it was spawned to judge.
  * **default** for every other caller, the main agent included. Everything
    readable.
    Writable: the repository, the session's own `/tmp`, and `~/.cache`.
    Read-only again inside the repository: every lane directory in every
    checkout, `<gauntlet dir>/red`, `<gauntlet dir>/merge`, `.claude/`, `hooks/`, `agents/`, `scripts/`,
    `.git/hooks` and `.git/config`. `~/.gitconfig` is read-only. `/run/user` is masked with an
    empty tmpfs, which closes the D-Bus route to `systemd --user` -- a socket
    rather than a spelling, so no string classifier could ever have caught it.

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

One shape escapes the wrap: `scripts/pair.sh`, which writes lane files by
design. `pair_passthrough.is_pair_command` holds that decision, in its own file,
because a wrapper that decided for itself which commands to skip would be a
classifier again.
"""

from __future__ import annotations

import functools
import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hook_payload  # noqa: E402
import hook_shape  # noqa: E402
import lane_config  # noqa: E402

pair_passthrough = importlib.import_module("pair-passthrough")

#: the two blind agents that keep a shell. `scripts/blind.sh` is their one
#: command and it runs its own `bwrap`, so this hook leaves them alone.
PASSTHROUGH_AGENTS = ("scrivener", "bailiff")

#: the blind reviewers: read-only everywhere, with a tmpfs over their own lane
REVIEWER_AGENTS = ("arbiter", "juror")

#: read-only again inside every checkout, on top of a writable repository. The
#: lane directories come from the one place they are defined.
PROTECTED_IN_CHECKOUT = lane_config.LANE_DIRS + (
    lane_config.gauntlet_dir() + "/red",
    lane_config.gauntlet_dir() + "/merge",
    ".claude",
    "hooks",
    "agents",
    "scripts",
    ".git/hooks",
    ".git/config",
)

#: the reviewers' own lane, which their profile answers with a tmpfs
REVIEWS_DIR = lane_config.reviews_lane()

WORKTREES = ".claude/worktrees"

_NO_BWRAP = (
    "This kit runs every Bash command inside `bwrap`, and `bwrap` is not on this host. "
    "Install `bubblewrap` (Fedora/RHEL: `sudo dnf install bubblewrap`; Debian/Ubuntu: "
    "`sudo apt install bubblewrap`). The hook fails closed rather than running the "
    "command unconfined. (hooks/bwrap-wrap.py)"
)


_BWRAP_BROKEN = (
    "This kit runs every Bash command inside `bwrap`. `bwrap` is installed on this host "
    "but will not run here, so every wrapped command would die at exec. `bwrap` said: "
    "{said}. Usual causes: unprivileged user namespaces off "
    "(`sysctl kernel.unprivileged_userns_clone`, `user.max_user_namespaces`), or a "
    "seccomp/LSM policy refusing the setup. The hook fails closed rather than running "
    "the command unconfined. (hooks/bwrap-wrap.py)"
)

#: the smallest profile that still does what every real profile does: make a
#: user namespace, bind a root, mount `/dev` and `/proc`, unshare the pid
#: namespace. A host that refuses any of those refuses every profile here.
_PROBE = (
    "--ro-bind",
    "/",
    "/",
    "--dev",
    "/dev",
    "--proc",
    "/proc",
    "--unshare-pid",
    "--die-with-parent",
    "--",
    "true",
)


def _first_line(text: str) -> str:
    return (text or "").strip().split("\n")[0].strip()


@functools.lru_cache(maxsize=1)
def bwrap_fault() -> str | None:
    """Why `bwrap` cannot be used on this host right now, or None if it can.

    Installed is not the same as working: user namespaces can be off and a
    seccomp policy can refuse the setup, and both leave a binary on `PATH` that
    dies at exec. Nothing but running it answers that, so it is run -- once per
    process, on `true`, which costs one process for the first `Bash` call of a
    session and nothing for the rest.
    """
    if shutil.which("bwrap") is None:
        return _NO_BWRAP
    try:
        done = subprocess.run(
            ["bwrap", *_PROBE], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError) as error:
        return _BWRAP_BROKEN.format(said=_first_line(str(error)) or type(error).__name__)
    if done.returncode == 0:
        return None
    said = _first_line(done.stderr) or f"exit status {done.returncode}"
    return _BWRAP_BROKEN.format(said=said)


def _answer(payload: dict[str, Any]) -> dict[str, Any] | None:
    """The hook's answer for this payload, or None to say nothing at all."""
    if payload.get("tool_name") != "Bash":
        return None
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str):
        return None

    # `agent_type` picks a profile; it never admits a caller. An absent one is
    # the main agent and takes the default profile, so `sudo` in a shell dies
    # at NO_NEW_PRIVS for the main agent exactly as for anyone else. The only
    # way out is a command the project declared, never a name.
    agent = hook_payload.agent_of(payload)
    if agent in PASSTHROUGH_AGENTS:
        return None
    # `pair.sh` runs unwrapped. A bare head is resolved to the kit's own copy on
    # the way out, because the spelling an agent types names a path a project
    # that dropped its local copy does not hold: admitting that spelling and
    # then running it as typed would answer the sandbox question and leave the
    # command with nothing to execute.
    if pair_passthrough.is_pair_command(command):
        resolved = pair_passthrough.resolved_pair_command(command)
        if resolved is None:
            return None
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "updatedInput": {"command": resolved},
            }
        }

    root = hook_payload.cwd_of(payload)
    # the project's own word, not this hook's: a command it declared under
    # `unwrapped_commands` runs outside the sandbox, and the paths that command
    # reads are bound read-only inside every wrapped profile. A declaration
    # naming a path this checkout does not hold is not live here and the
    # command is wrapped like any other.
    if pair_passthrough.is_declared_command(command, root):
        return None

    fault = bwrap_fault()
    if fault is not None:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": fault,
            }
        }

    wrapped = wrap(command, root, agent)
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "updatedInput": {"command": wrapped},
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


def _base(root: str) -> list[str]:
    """The mounts every profile takes: readable world, live /dev, masked /run/user."""
    return [
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
        "--tmpfs",
        "/tmp",
        "--unshare-pid",
        "--die-with-parent",
        # a `--chdir` onto a directory that is not there fails the invocation,
        # and a caller's `cwd` can name a tree that has since been cut
    ] + (["--chdir", root] if _source(root) else [])


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
    for relative in PROTECTED_IN_CHECKOUT:
        args += _bind("--ro-bind-try", str(Path(checkout) / relative))
    return args


def wrap(command: str, root: str, agent: str) -> str:
    """The `bwrap` invocation that runs `command`, as one shell command string.

    The caller's text is carried on stdin through a here-document, so it appears
    in the result byte for byte however it is spelled.
    """
    args = _profile(root, agent)
    return " ".join(_quote(a) for a in args) + " " + _heredoc(command)


def _profile(root: str, agent: str) -> list[str]:
    """The full `bwrap` argument list for one agent in one checkout."""
    home = os.environ.get("HOME") or root
    args = _base(root)

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

        # last, so they stand over the writable binds above: a path a declared
        # command reads is read-only to every wrapped shell. The one command
        # that runs outside the sandbox would otherwise run whatever a shell
        # inside it wrote into that file.
        for path in pair_passthrough.read_only_paths(root):
            args += _bind("--ro-bind", path)

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
    return importlib.import_module("bwrap_wrap_selftest").run()


if __name__ == "__main__":
    hook_shape.entry(self_test, main)
