#!/usr/bin/env python3
"""PreToolUse hook: every `Bash` command runs inside `bwrap`, unread.

This is the mechanism that replaces reading command text. A lane hook used to
decide a `Bash` call by parsing the string -- does this command write, and
where -- and that question is undecidable on a string: an env prefix, a
here-document, a command substitution, a shell function, a `find -exec`, an
`xargs`. Each round of patching added a member to a list and left the next
spelling open.

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
read:

  * **passthrough** for the two blind agents that keep a shell. `blind.sh` runs
    its own `bwrap`, and wrapping a wrapper gains nothing while costing a nested
    mount setup on the one command those agents have.
  * **reviewer** for the blind reviewers: the whole filesystem read-only, plus a
    tmpfs over the reviewers' own lane. A reviewer's shell cannot change the
    checkout it was spawned to judge.
  * **default** for everyone else, the main agent included. Everything readable.
    Writable: the repository, the session's own `/tmp`, and `~/.cache`.
    Read-only again inside the repository: every lane directory in every
    checkout, `state/red`, `state/merge`, `.claude/`, `scripts/`, `.git/hooks`
    and `.git/config`. `~/.gitconfig` is read-only. `/run/user` is masked with an
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

One shape escapes the wrap: `scripts/pair.sh`, which writes lane files by
design. `pair_passthrough.is_pair_command` holds that decision, in its own file,
because a wrapper that decided for itself which commands to skip would be a
classifier again.
"""

from __future__ import annotations

import importlib
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shell_shapes as sh  # noqa: E402

pair_passthrough = importlib.import_module("pair-passthrough")

#: the two blind agents that keep a shell. `scripts/blind.sh` is their one
#: command and it runs its own `bwrap`, so this hook leaves them alone.
PASSTHROUGH_AGENTS = ("gauntlet-scrivener", "gauntlet-bailiff")

#: the blind reviewers: read-only everywhere, with a tmpfs over their own lane
REVIEWER_AGENTS = ("gauntlet-arbiter", "gauntlet-juror")

#: read-only again inside every checkout, on top of a writable repository. The
#: lane directories come from the one place they are defined.
PROTECTED_IN_CHECKOUT = sh.LANE_DIRS + (
    "state/red",
    "state/merge",
    ".claude",
    "scripts",
    ".git/hooks",
    ".git/config",
)

#: the reviewers' own lane, which their profile answers with a tmpfs
REVIEWS_DIR = "gauntlet/reviews"

WORKTREES = ".claude/worktrees"

_NO_BWRAP = (
    "This kit runs every Bash command inside `bwrap`, and `bwrap` is not on this host. "
    "Install `bubblewrap` (Fedora/RHEL: `sudo dnf install bubblewrap`; Debian/Ubuntu: "
    "`sudo apt install bubblewrap`). The hook fails closed rather than running the "
    "command unconfined. (hooks/bwrap-wrap.py)"
)


def _answer(payload: dict) -> dict | None:
    """The hook's answer for this payload, or None to say nothing at all."""
    if payload.get("tool_name") != "Bash":
        return None
    command = (payload.get("tool_input") or {}).get("command")
    if not isinstance(command, str):
        return None

    agent = payload.get("agent_type") or ""
    if agent in PASSTHROUGH_AGENTS:
        return None
    if pair_passthrough.is_pair_command(command):
        return None

    if shutil.which("bwrap") is None:
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": _NO_BWRAP,
            }
        }

    root = payload.get("cwd") or os.getcwd()
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
    parent = os.path.join(root, WORKTREES)
    try:
        names = sorted(os.listdir(parent))
    except OSError:
        return []
    trees = [os.path.join(parent, name) for name in names]
    return [tree for tree in trees if os.path.isdir(tree)]


def _base(root: str) -> list[str]:
    """The mounts every profile takes: readable world, live /dev, masked /run/user."""
    return [
        "bwrap",
        "--ro-bind", "/", "/",
        "--dev", "/dev",
        "--proc", "/proc",
        # the D-Bus route to `systemd --user`, which starts a unit outside
        # anything the calling process was confined by
        "--tmpfs", "/run/user",
        "--tmpfs", "/tmp",
        "--unshare-pid",
        "--die-with-parent",
        "--chdir", root,
    ]


def _checkout_readonly(checkout: str) -> list[str]:
    """Bind back read-only the directories no shell writes, in one checkout."""
    args: list[str] = []
    for relative in PROTECTED_IN_CHECKOUT:
        path = os.path.join(checkout, relative)
        args += ["--ro-bind-try", path, path]
    return args


def wrap(command: str, root: str, agent: str) -> str:
    """The `bwrap` invocation that runs `command`, as one shell command string.

    The caller's text is carried on stdin through a here-document, so it appears
    in the result byte for byte however it is spelled.
    """
    home = os.environ.get("HOME") or root
    args = _base(root)

    if agent in REVIEWER_AGENTS:
        # nothing writable but the reviewer's own lane, and that only as a
        # tmpfs: a reviewer's shell cannot change the checkout it judges
        reviews = os.path.join(root, REVIEWS_DIR)
        args += ["--tmpfs", reviews]
    else:
        args += ["--bind", root, root]
        args += ["--bind-try", os.path.join(home, ".cache"), os.path.join(home, ".cache")]
        gitconfig = os.path.join(home, ".gitconfig")
        args += ["--ro-bind-try", gitconfig, gitconfig]

        # the repository is writable, so the lanes inside it are bound back
        # read-only, in the main checkout and in every worktree
        args += _checkout_readonly(root)
        trees = worktrees(root)
        parent = os.path.join(root, WORKTREES)
        args += ["--ro-bind-try", parent, parent]
        for tree in trees:
            args += ["--bind", tree, tree]
            args += _checkout_readonly(tree)

    args += ["--", "bash", "-s"]
    return " ".join(_quote(a) for a in args) + " " + _heredoc(command)


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
    if sh.bypassed():
        return  # GAUNTLET=off: the owner's switch, read at the entry point only
    try:
        payload = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        return  # never block on our own failure
    answer = _answer(payload)
    if answer is not None:
        print(json.dumps(answer))


def self_test() -> int:
    """Pin what the wrap carries, what it binds, and what escapes it."""
    root = "/repo"
    semicolon = "echo hi; cat /etc/hostname"
    heredoc = "echo $(cat /etc/hostname) <<'X'"

    default = wrap(semicolon, root, "gauntlet-prosecutor")
    reviewer = wrap(semicolon, root, "gauntlet-arbiter")
    awkward = wrap(heredoc, root, "gauntlet-prosecutor")

    lines = {
        "the caller's text survives the wrap byte for byte, whatever it is": (
            semicolon in default and heredoc in awkward
        ),
        "a command carrying the delimiter cannot close the here-document early": (
            "<<'GAUNTLET_COMMAND_EOF_'" in wrap("a\nGAUNTLET_COMMAND_EOF\nb", root, "")
        ),
        "the default profile makes the repository writable": (
            f"--bind {root} {root}" in default
        ),
        "the lane directories are bound back read-only under it": all(
            f"--ro-bind-try {root}/{lane} {root}/{lane}" in default for lane in sh.LANE_DIRS
        ),
        "the reviewer profile binds no writable repository": (
            f"--bind {root} {root}" not in reviewer
            and f"--tmpfs {root}/{REVIEWS_DIR}" in reviewer
        ),
        "/run/user is masked and the pid namespace is unshared": (
            "--tmpfs /run/user" in default and "--unshare-pid" in default
        ),
        "a blind agent with its own bwrap is left alone": all(
            _answer(
                {
                    "tool_name": "Bash",
                    "cwd": root,
                    "agent_type": agent,
                    "tool_input": {"command": "scripts/blind.sh status demo"},
                }
            )
            is None
            for agent in PASSTHROUGH_AGENTS
        ),
        "a whole pair.sh subcommand call escapes the wrap, and nothing else does": (
            _answer(
                {
                    "tool_name": "Bash",
                    "cwd": root,
                    "agent_type": "gauntlet-prosecutor",
                    "tool_input": {"command": "scripts/pair.sh red demo"},
                }
            )
            is None
            and _answer(
                {
                    "tool_name": "Bash",
                    "cwd": root,
                    "agent_type": "gauntlet-prosecutor",
                    "tool_input": {"command": "scripts/pair.sh red demo; rm -rf state"},
                }
            )
            is not None
        ),
        "a tool that is not Bash is not this hook's business": (
            _answer({"tool_name": "Write", "tool_input": {"command": "x"}}) is None
        ),
        "the worktree list is read from disk rather than carried": (
            worktrees("/nonexistent-by-construction") == []
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test()) if "--self-test" in sys.argv else main()
