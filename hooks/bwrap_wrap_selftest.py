"""The `--self-test` of `hooks/bwrap-wrap.py`: its assertions and the tree, fake
`bwrap` binaries and answer helpers that only they use.

Nothing imports this at hook time; `python3 hooks/bwrap-wrap.py --self-test` is
the entry point and pulls it in from inside that branch.
"""

import importlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hook_payload  # noqa: E402
import bwrap_probe  # noqa: E402
import hook_shape  # noqa: E402
import lane_config  # noqa: E402

#: the hook under test, already imported by the time this module is: the
#: `--self-test` branch registers it under this name before importing here, so
#: this is the same module object and not a second copy of it.
_bw = importlib.import_module("bwrap-wrap")

pair_passthrough = _bw.pair_passthrough
PASSTHROUGH_AGENTS = _bw.PASSTHROUGH_AGENTS
PROTECTED_IN_CHECKOUT = _bw.PROTECTED_IN_CHECKOUT
REVIEWS_DIR = _bw.REVIEWS_DIR
WORKTREES = _bw.WORKTREES
_NO_BWRAP = bwrap_probe._NO_BWRAP
_answer = _bw._answer
_heredoc = _bw._heredoc
bwrap_fault = bwrap_probe.bwrap_fault
worktrees = _bw.worktrees
wrap = _bw.wrap

#: the hook's own path, not this module's: the hostile-payload check runs the
#: file it is given.
_HOOK = _bw.__file__


def run() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        return _self_test_in(tmp)


def _make_tree(root: str, worktree_git_is_a_file: bool) -> None:
    """A checkout shaped like this kit's: lanes, scripts, and a `.git`.

    `worktree_git_is_a_file` spells the difference between a main checkout and
    a git worktree. In a worktree `.git` is a pointer file, so `.git/hooks`
    resolves `ENOTDIR` rather than simply missing -- the shape that took every
    `Bash` call in a session down.
    """
    for relative in PROTECTED_IN_CHECKOUT + (WORKTREES,):
        if relative.startswith(".git/") and worktree_git_is_a_file:
            continue
        (Path(root) / relative).mkdir(parents=True, exist_ok=True)
    dot_git = Path(root) / ".git"
    if worktree_git_is_a_file:
        dot_git.write_text("gitdir: /elsewhere/.git/worktrees/tree\n", encoding="utf-8")


def _runs(wrapped: str) -> tuple[bool, str]:
    """Whether the shell command a profile produced actually runs. Decisive.

    No inspection of an argument list can answer this: `bwrap` is the authority
    on which of its own sources it will accept, so the test asks it. The
    command inside the sandbox is `true`, so the cost is one process.
    """
    done = subprocess.run(
        ["bash", "-c", wrapped], capture_output=True, text=True, timeout=60, check=False
    )
    return done.returncode == 0, (done.stderr or "").strip().split("\n")[0]


def _answer_with_path(where: str, root: str) -> dict[str, Any] | None:
    """`_answer` for one Bash call, with `where` as the whole of `PATH`.

    The probe is cached for the life of the process, so the cache is cleared on
    both sides: a stale answer here would test the previous case twice.
    """
    was = os.environ.get("PATH", "")
    os.environ["PATH"] = where
    bwrap_fault.cache_clear()
    try:
        return _answer(
            {
                "tool_name": "Bash",
                "cwd": root,
                "agent_type": "prosecutor",
                "tool_input": {"command": "echo hi"},
            }
        )
    finally:
        os.environ["PATH"] = was
        bwrap_fault.cache_clear()


def _fake_bwrap(where: str, body: str) -> str:
    """A real executable named `bwrap` in `where`, running `body`. Returns `where`."""
    Path(where).mkdir(parents=True, exist_ok=True)
    path = Path(where) / "bwrap"
    path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
    path.chmod(0o755)
    return where


def _reason(answer: dict[str, Any] | None) -> str:
    """The denial text of an answer, or "" if it is not a denial."""
    out = (answer or {}).get("hookSpecificOutput") or {}
    if out.get("permissionDecision") != "deny":
        return ""
    return str(out.get("permissionDecisionReason") or "")


def _self_test_in(tmp: str) -> int:
    root = str(Path(tmp) / "checkout")
    _make_tree(root, worktree_git_is_a_file=False)
    tree = str(Path(root) / WORKTREES / "demo-spec")
    _make_tree(tree, worktree_git_is_a_file=True)

    semicolon = "echo hi; cat /etc/hostname"
    heredoc = "echo $(cat /etc/hostname) <<'X'"

    def command_of_answer(answer: dict[str, Any] | None) -> str | None:
        """The command an answer carries, or None where it carries none."""
        out = (answer or {}).get("hookSpecificOutput") or {}
        return (out.get("updatedInput") or {}).get("command")

    def answer_for(agent: str) -> dict[str, Any] | None:
        """`_answer` for one ordinary command, run as `agent`."""
        return _answer(
            {
                "tool_name": "Bash",
                "cwd": root,
                "agent_type": agent,
                "tool_input": {"command": semicolon},
            }
        )

    default = wrap(semicolon, root, "prosecutor")
    reviewer = wrap(semicolon, root, "arbiter")
    awkward = wrap(heredoc, root, "prosecutor")

    #: not `shutil.which`: a binary that will not run is the case below
    have_bwrap = bwrap_fault() is None
    gone = str(Path(tmp) / "cut-since-the-call-began")

    #: an installed `bwrap` that dies at exec -- user namespaces off, a seccomp
    #: policy refusing the setup. A real executable, so the probe is a real run.
    broken = _fake_bwrap(
        str(Path(tmp) / "broken-bin"),
        'echo "bwrap: No permissions to creating new namespace" >&2\nexit 1',
    )
    empty = str(Path(tmp) / "empty-bin")
    Path(empty).mkdir(parents=True, exist_ok=True)

    #: the declared extra binds, against real paths outside the checkout
    outside = str(Path(tmp) / "outside")
    inside = str(Path(root) / "inside")
    in_tree = str(Path(tree) / "inside")
    linked = str(Path(tmp) / "linked")
    for made in (outside, inside, in_tree):
        Path(made).mkdir(parents=True, exist_ok=True)
    if not Path(linked).exists():
        Path(linked).symlink_to(root)
    home = os.environ.get("HOME") or str(Path(tmp) / "home")

    def extras(entries: list[Any], agent: str = "prosecutor") -> str:
        """The wrapped command under one `extra_binds` declaration.

        The declaration is resolved through the reader, so a malformed list
        reaches the mount table exactly as a project's mistyped one would.
        """
        declared = lane_config.extra_binds_from({"extra_binds": entries})
        was = lane_config.extra_binds
        lane_config.extra_binds = lambda: declared
        try:
            return wrap(semicolon, root, agent)
        finally:
            lane_config.extra_binds = was

    def bound(entries: list[Any], path: str, agent: str = "prosecutor") -> bool:
        """Is `path` writable under that declaration?"""
        return f"--bind-try {path} {path}" in extras(entries, agent)

    def named_without_home(entry: str) -> bool:
        """Is `entry` named at all with no `HOME` to expand it against?

        The name is distinctive on purpose: an entry that survives unexpanded
        is spelled `~/...`, and half of that spelling is a word the profile
        carries anyway.
        """
        was = os.environ.pop("HOME", None)
        try:
            return "gauntlet-extra-probe" in extras([entry])
        finally:
            if was is not None:
                os.environ["HOME"] = was

    lines = {
        "a declared path outside every checkout is bound writable": bound([outside], outside),
        "a declared path whose source is not live is not bound": not bound([gone], gone),
        "a relative entry is not bound": "relative/cache" not in extras(["relative/cache"]),
        "a `~` entry with no HOME to expand it is not bound": not named_without_home(
            "~/gauntlet-extra-probe"
        ),
        "an entry standing over a path the profile guards is dropped": not any(
            bound([one], one) for one in ("/dev", "/proc", "/run/user", home)
        ),
        "the /tmp mountpoint is dropped and a path under it is not": (
            not bound(["/tmp"], "/tmp") and bound([outside], outside)
        ),
        "an entry equal to the checkout, inside it, or over it is dropped": not any(
            bound([one], one) for one in (root, inside, str(Path(tmp)))
        ),
        "an entry inside a worktree is dropped": not bound([in_tree], in_tree),
        "an entry resolving into a checkout is dropped whatever it is spelled": not bound(
            [linked], linked
        ),
        "the reviewer profile takes no declared extra": not bound([outside], outside, "arbiter"),
        "one malformed entry voids the whole key": not bound([outside, 5], outside),
        "one path named twice is bound once": (
            extras([outside, outside]).count(f"--bind-try {outside} {outside}") == 1
        ),
        "the extras stand after the read-only lanes they must not walk back": (
            extras([outside]).index(f"--bind-try {outside} {outside}")
            > max(
                extras([outside]).index(f"--ro-bind-try {root}/{lane} {root}/{lane}")
                for lane in lane_config.LANE_DIRS
            )
        ),
        "the caller's text survives the wrap byte for byte, whatever it is": (
            semicolon in default and heredoc in awkward
        ),
        "a command carrying the delimiter cannot close the here-document early": (
            "<<'GAUNTLET_COMMAND_EOF_'" in wrap("a\nGAUNTLET_COMMAND_EOF\nb", root, "")
        ),
        "the default profile makes the repository writable": (f"--bind {root} {root}" in default),
        "the lane directories are bound back read-only under it": all(
            f"--ro-bind-try {root}/{lane} {root}/{lane}" in default for lane in lane_config.LANE_DIRS
        ),
        "the reviewer profile binds no writable repository": (
            f"--bind {root} {root}" not in reviewer and f"--tmpfs {root}/{REVIEWS_DIR}" in reviewer
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
        #: the escape is the whole call, and a bare head leaves here spelled at
        #: the kit's own copy: the spelling an agent types names a path a
        #: project that dropped its local copy does not hold. What does not
        #: match is wrapped exactly as before, `bwrap` in front of it.
        "a whole pair.sh subcommand call escapes the wrap, resolved, and nothing else does": (
            command_of_answer(
                _answer(
                    {
                        "tool_name": "Bash",
                        "cwd": root,
                        "agent_type": "prosecutor",
                        "tool_input": {"command": "scripts/pair.sh red demo"},
                    }
                )
            )
            == f"{pair_passthrough.kit_entry()} red demo"
            and (
                command_of_answer(
                    _answer(
                        {
                            "tool_name": "Bash",
                            "cwd": root,
                            "agent_type": "prosecutor",
                            "tool_input": {
                                "command": "scripts/pair.sh red demo; rm -rf state"
                            },
                        }
                    )
                )
                or ""
            ).startswith("bwrap")
        ),
        #: a head that already names a script is what it will run, so it
        #: escapes with nothing rewritten and the hook answers nothing at all
        "an absolute pair.sh head escapes untouched": (
            _answer(
                {
                    "tool_name": "Bash",
                    "cwd": root,
                    "agent_type": "prosecutor",
                    "tool_input": {"command": f"{pair_passthrough.kit_entry()} red demo"},
                }
            )
            is None
        ),
        #: installed as a plugin the harness spells the name with its plugin in
        #: front of it, and that is the same agent, profile for profile
        "a namespaced agent_type is the agent its bare spelling names": (
            answer_for("prosecutor") is not None
            and answer_for("gauntlet:prosecutor") == answer_for("prosecutor")
            and answer_for("gauntlet:arbiter") == answer_for("arbiter")
            #: a namespaced passthrough agent keeps its passthrough
            and answer_for("gauntlet:scrivener") is None
        ),
        #: the exemption this closes: the main agent is the caller with the
        #: widest reach, so a roster that let it past left the sandbox with a
        #: hole the size of the session
        "the main agent, carrying no agent_type, is wrapped like anyone else": (
            answer_for("prosecutor") is not None
            and _answer(
                {
                    "tool_name": "Bash",
                    "cwd": root,
                    "tool_input": {"command": semicolon},
                }
            )
            == answer_for("prosecutor")
        ),
        #: an agent_type this kit never named is not a caller to exempt either
        "a foreign agent_type takes the default profile rather than a pass": (
            answer_for("some-other-plugin:whatever") == answer_for("prosecutor")
        ),
        "a tool that is not Bash is not this hook's business": (
            _answer({"tool_name": "Write", "tool_input": {"command": "x"}}) is None
        ),
        "the worktree list is read from disk rather than carried": (
            worktrees("/nonexistent-by-construction") == [] and worktrees(root) == [tree]
        ),
        #: the bug: `.git` is a pointer file in a worktree, so `.git/hooks`
        #: resolves ENOTDIR, and `--ro-bind-try` forgives absence only
        "a worktree's `.git` pointer file is never named as a bind source": (
            f"{tree}/.git/hooks" not in default and f"{tree}/.git/config" not in default
        ),
        #: the gap the probe closes: on `PATH` and unable to run is a host where
        #: every rewritten `Bash` call dies at exec with no statement of why
        "a bwrap that is installed but will not run is denied, by its own words": (
            "No permissions to creating new namespace" in _reason(_answer_with_path(broken, root))
        ),
        "a host with no bwrap at all is denied for that, and not for the other": (
            _reason(_answer_with_path(empty, root)) == _NO_BWRAP
        ),
        "the worktree binds survive the tree going away under them": (
            f"--bind-try {tree} {tree}" in default and f"--bind {tree} {tree}" not in default
        ),
        "a bind source cut between the profile and the exec is not named": (
            gone not in wrap("true", gone, "prosecutor")
            or not Path(gone).exists()
            and f"--chdir {gone}" not in wrap("true", gone, "prosecutor")
        ),
        #: a hook decides a tool call, so its own crash is a denial -- and a
        #: payload it cannot read is a call it cannot decide, which is a refusal
        "every payload shape is answered, and an unreadable one is refused": (
            hook_payload.survives_hostile_payloads(_HOOK, guards=("Bash",))
        ),
    }

    if have_bwrap:
        for label, profile in (
            ("the default profile runs, against this very tree", default),
            ("the reviewer profile runs, against this very tree", reviewer),
            (
                "the profile for the real checkout this gate runs in runs",
                wrap("true", str(Path(_HOOK).resolve().parents[2]), "prosecutor"),
            ),
        ):
            #: `true` inside the sandbox, so a failure is the mount setup and
            #: nothing else
            ran, first = _runs(profile.replace(_heredoc(semicolon), _heredoc("true")))
            lines[label] = ran
            if not ran:
                lines[label + f"  [bwrap said: {first}]"] = False

        #: the race the listing cannot close: the profile names a tree that is
        #: gone by the time `bwrap` reads it. Under `--bind` this killed the
        #: whole command; the test removes the tree for real and runs it.
        vanishing = wrap("true", root, "prosecutor")
        shutil.rmtree(tree)
        ran, first = _runs(vanishing)
        label = "a worktree cut after the profile was built does not kill the command"
        lines[label] = ran
        if not ran:
            lines[label + f"  [bwrap said: {first}]"] = False
        _make_tree(tree, worktree_git_is_a_file=True)
    else:
        lines["bwrap is absent, so the profiles could not be run"] = True

    return hook_shape.report(lines)
