#!/usr/bin/env python3
"""PreToolUse hook: `state/reviews/` is the reviewers' lane, and nearly their only one.

Wired session-wide from `.claude/settings.json`, so it binds the main agent
and every subagent, and again from the `hooks:` frontmatter of
`.claude/agents/gauntlet-arbiter.md` and `.claude/agents/gauntlet-prosecutor.md`, where
the same script confines those two agents to what they are allowed to write.

The rule it enforces: a reviewer's verdict reaches the rest of the chain from a
file the reviewer wrote itself, `state/reviews/<slug>.<N>.txt`, never from a
transcription the main agent typed. A verdict that passes through another
agent's hands on the way is a verdict that agent can soften.

The `gauntlet-arbiter` has a second write, and exactly one: the approved block at
`specs/approved/<slug>.txt`, which it writes on `READY` and on nothing else.
That is the same rule in the other direction — the file the blind gauntlet-testsmith
works from is written by the gate itself — so this hook must allow it or the
reviewer is locked out of the lane `specs-lane.py` reserves for it. The
`gauntlet-prosecutor` approves no spec and does not get that write.

Denied:

  * `Write`/`Edit`/`NotebookEdit` whose target is under `state/reviews/` of
    any checkout, unless the caller's `agent_type` is `gauntlet-arbiter` or
    `gauntlet-prosecutor`
  * for those two agents, any `Write`/`Edit`/`NotebookEdit` outside
    `state/reviews/`, except the `gauntlet-arbiter` writing under
    `specs/approved/`
  * for those two agents, any `Bash` command that writes anything at all
  * for those two agents, a `Read` or a `Grep` aimed under `state/reviews/`,
    and a read-only `Bash` command naming such a path
  * for everyone else, a `Bash` command that writes and that names a
    `state/reviews/` path

A reviewer is denied the lane's contents as well as its writes, because a
rejection burns the agent that printed it and its replacement continues the
numbering in the same directory: the `Glob` that finds the next `<N>` is
allowed and returns filenames, and a prior round reaches a reviewer only as
the carried verdicts in the main agent's own return.

Allowed: every read-only command naming `state/reviews/` for everyone but
those two agents, git commands that never write the working tree, `Glob` for
anyone, and every write elsewhere by every non-reviewer. `state/` is meant to
be gitignored, so there is no git object to restore from and no restore
carve-out.

`agent_type` is present in the payload only for subagent calls; an absent key
is the main agent. If a build omits the key for subagents too, a reviewer is
over-denied, which is the safe direction: nothing leaks, and the denial names
this file.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shell_shapes as sh  # noqa: E402

SPEC_REVIEWER = "gauntlet-arbiter"
REVIEWERS = frozenset({SPEC_REVIEWER, "gauntlet-prosecutor"})
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")
#: tools that hand back a file's contents; `Glob` returns names only and is not one
READ_TOOLS = ("Read", "Grep")
LANE = "state/reviews"
APPROVED = "specs/approved"
BASH_REVIEWS = sh.lane_pattern(LANE)

_LANE = (
    "state/reviews/ is the reviewers' lane: a verdict file is written by the "
    "gauntlet-arbiter or gauntlet-prosecutor that produced it, and the chain reads the "
    "verdict from that file. Nothing else writes there. "
    "(hooks/reviews-lane.py)"
)
_REVIEWER_LANE = (
    "Reviewer: your verdict goes to state/reviews/<slug>.<N>.txt of the main "
    "checkout, and the gauntlet-arbiter's approved block to specs/approved/<slug>.txt. "
    "Nowhere else: not the source tree, not tests/, not docs/. "
    "(hooks/reviews-lane.py)"
)
_REVIEWER_BASH = (
    "Reviewer: a shell command that changes anything is denied; your writes are "
    "the Write tool onto state/reviews/ and, for the gauntlet-arbiter on READY, "
    "specs/approved/. Read-only shell (cat, grep, sed -n, pytest) passes. "
    "(hooks/reviews-lane.py)"
)
_REVIEWER_READ = (
    "Reviewer: state/reviews/ is not yours to read. A prior round reaches you "
    "as the carried verdicts in the main agent's return, never as a file: the round "
    "that rejected a brief printed the steering back verbatim, and it is written "
    "nowhere for you to find. Glob for the next <N> is allowed and returns "
    "filenames. (hooks/reviews-lane.py)"
)
_BASH = "A shell write naming a state/reviews/ path is denied: " + _LANE


def _write_verdict(target: str, cwd: str, agent: str) -> str | None:
    in_reviews = sh.path_in_lane(target, cwd, LANE)
    if agent not in REVIEWERS:
        return _LANE if in_reviews else None
    if in_reviews:
        return None
    if agent == SPEC_REVIEWER and sh.path_in_lane(target, cwd, APPROVED):
        return None
    return _REVIEWER_LANE


def _read_verdict(tool_input: dict, cwd: str, agent: str) -> str | None:
    """A reviewer reads no round file; `Read` names one, `Grep` names a set."""
    if agent not in REVIEWERS:
        return None
    targets = (tool_input.get("file_path"), tool_input.get("path"), tool_input.get("glob"))
    aimed = any(t and sh.path_in_lane(t, cwd, LANE) for t in targets)
    return _REVIEWER_READ if aimed else None


def _bash_verdict(command: str, agent: str) -> str | None:
    if agent in REVIEWERS:
        if sh.command_writes(command, restore_ok=False):
            return _REVIEWER_BASH
        return _REVIEWER_READ if BASH_REVIEWS.search(command) else None
    return _BASH if sh.lane_write_in(command, BASH_REVIEWS, restore_ok=False) else None


def _verdict(name: str, tool_input: dict, payload: dict) -> str | None:
    """Why this call is refused, or None to let it through."""
    cwd = payload.get("cwd") or os.getcwd()
    agent = payload.get("agent_type") or ""
    if name in WRITE_TOOLS:
        target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        return _write_verdict(target, cwd, agent) if target else None
    if name in READ_TOOLS:
        return _read_verdict(tool_input, cwd, agent)
    if name == "Bash":
        return _bash_verdict(tool_input.get("command", ""), agent)
    return None


def main() -> None:
    try:
        data = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        return  # never block on our own failure
    reason = _verdict(data.get("tool_name", ""), data.get("tool_input") or {}, data)
    if reason is not None:
        print(sh.deny(reason))


def self_test() -> int:
    """Pin the four spec lines of the reviewers' lane."""
    root = "/repo"

    def call(tool: str, tool_input: dict, agent: str | None = None) -> str | None:
        payload = {"cwd": root}
        if agent:
            payload["agent_type"] = agent
        return _verdict(tool, tool_input, payload)

    def write(path: str, agent: str | None = None) -> str | None:
        return call("Write", {"file_path": path}, agent)

    def read(path: str, agent: str | None = None) -> str | None:
        return call("Read", {"file_path": path}, agent)

    def bash(cmd: str, agent: str | None = None) -> str | None:
        return call("Bash", {"command": cmd}, agent)

    denied, allowed = (lambda v: isinstance(v, str)), (lambda v: v is None)
    lines = {
        "1 state/reviews/ closed to everyone but the two reviewers": all(
            (
                denied(write(f"{root}/state/reviews/slug.1.txt")),
                denied(write(f"{root}/state/reviews/slug.1.txt", "gauntlet-testsmith")),
                #: an unprefixed same-named agent in the host project is not this one
                denied(write(f"{root}/state/reviews/slug.1.txt", "arbiter")),
                denied(write(f"{root}/state/reviews/slug.1.txt", "prosecutor")),
                allowed(write(f"{root}/state/reviews/slug.1.txt", SPEC_REVIEWER)),
                allowed(write(f"{root}/state/reviews/slug.1.txt", "gauntlet-prosecutor")),
                denied(bash("echo x > state/reviews/slug.1.txt")),
                allowed(bash("cat state/reviews/slug.1.txt")),
            )
        ),
        "2 a reviewer writes its verdict and nothing else": all(
            (
                denied(write(f"{root}/src/m.py", SPEC_REVIEWER)),
                denied(write(f"{root}/tests/t.py", SPEC_REVIEWER)),
                denied(write(f"{root}/docs/testing.md", "gauntlet-prosecutor")),
                denied(bash("sed -i 's/a/b/' src/m.py", SPEC_REVIEWER)),
                allowed(bash("git show HEAD:specs/approved/slug.txt", SPEC_REVIEWER)),
                allowed(bash("grep -rn 'def test_' tests/", SPEC_REVIEWER)),
            )
        ),
        "3 the gauntlet-arbiter alone also writes specs/approved/": all(
            (
                allowed(write(f"{root}/specs/approved/slug.txt", SPEC_REVIEWER)),
                denied(write(f"{root}/specs/approved/slug.txt", "gauntlet-prosecutor")),
                denied(write(f"{root}/specs/draft/slug.txt", SPEC_REVIEWER)),
            )
        ),
        "4 a reviewer never reads the round files": all(
            (
                denied(read(f"{root}/state/reviews/slug.1.txt", SPEC_REVIEWER)),
                denied(read(f"{root}/state/reviews/slug.1.txt", "gauntlet-prosecutor")),
                denied(bash("cat state/reviews/slug.1.txt", SPEC_REVIEWER)),
                allowed(read(f"{root}/state/reviews/slug.1.txt")),
                allowed(read(f"{root}/tests/t.py", SPEC_REVIEWER)),
            )
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test()) if "--self-test" in sys.argv else main()
