#!/usr/bin/env python3
"""PreToolUse hook: `gauntlet/plans/approved/` is the gauntlet-prosecutor's lane.

Wire it session-wide from `.claude/settings.json`, so it binds the main agent
and every subagent, and again from the `hooks:` frontmatter of
`.claude/agents/gauntlet-prosecutor.md`.

This is the rule `specs-lane.py` holds for the spec gate, one stage earlier.
A plan that reached `READY` is the thing the implementation is measured
against, and a fresh agent picking the chain up at any later stage reads it
from disk rather than inheriting it. If the agent that wants a plan through
can also write the file, approval is a formality: the main agent states the
plan, drops it in the folder, and the adversarial review it was supposed to
survive never happened. So the file is written by exactly one hand, the one
that holds the gate.

Denied:

  * `Write`/`Edit`/`NotebookEdit` whose target is under a
    `gauntlet/plans/approved/` directory, unless the caller's `agent_type` is
    `gauntlet-prosecutor`
  * a `Bash` command that names a `gauntlet/plans/approved/` path and is not
    read-only, except a restore from a named git object
    (`git restore --source <rev>` or `git checkout <rev> --` onto the path),
    which copies a commit and types nothing

Allowed: every read of `gauntlet/plans/approved/`, by any agent and by the shell;
every write anywhere else, including a draft plan under
`gauntlet/plans/drafts/`.

`agent_type` is present in the payload only for subagent calls; an absent key
is the main agent, which is denied. If a build omits the key for subagents
too, the gauntlet-prosecutor is over-denied, which is the safe direction: no
unreviewed plan reaches the tree, and the denial names this file.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import shell_shapes as sh  # noqa: E402

REVIEWER = "gauntlet-prosecutor"
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")
LANE = "gauntlet/plans/approved"
BASH_PLANS = sh.lane_pattern(LANE)

_LANE = (
    "gauntlet/plans/approved/ is the gauntlet-prosecutor's lane. An approved plan is "
    "written there by the reviewer that approved it, and by nothing else: it is "
    "the only evidence a later stage has that the plan it works from passed the "
    "plan gate. Draft under gauntlet/plans/drafts/ and send the draft to the "
    "gauntlet-prosecutor. (hooks/plans-lane.py)"
)
_BASH = (
    "A shell write naming a gauntlet/plans/approved/ path is denied: " + _LANE + " Restoring "
    "an approved plan from a git object is the one shell shape that passes: "
    "`git restore --source <rev> -- gauntlet/plans/approved/<file>`."
)


def _write_verdict(target: str, cwd: str, agent: str) -> str | None:
    if not sh.path_in_lane(target, cwd, LANE):
        return None
    return None if agent == REVIEWER else _LANE


def _bash_verdict(command: str) -> str | None:
    return _BASH if sh.lane_write_in(command, BASH_PLANS) else None


def _verdict(name: str, tool_input: dict, payload: dict) -> str | None:
    """Why this call is refused, or None to let it through."""
    cwd = payload.get("cwd") or os.getcwd()
    agent = payload.get("agent_type") or ""
    if name in WRITE_TOOLS:
        target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
        return _write_verdict(target, cwd, agent) if target else None
    if name == "Bash":
        return _bash_verdict(tool_input.get("command", ""))
    return None


def main() -> None:
    if sh.bypassed():
        return  # GAUNTLET=off: the owner's switch, read at the entry point only
    try:
        data = json.loads(sys.stdin.read())
    except (ValueError, OSError):
        return  # never block on our own failure
    reason = _verdict(data.get("tool_name", ""), data.get("tool_input") or {}, data)
    if reason is not None:
        print(sh.deny(reason))


def self_test() -> int:
    """Pin the four spec lines of the approved-plan lane."""
    root = "/repo"

    def write(path: str, agent: str | None = None) -> str | None:
        payload = {"cwd": root}
        if agent:
            payload["agent_type"] = agent
        return _verdict("Edit", {"file_path": path}, payload)

    def bash(cmd: str) -> str | None:
        return _verdict("Bash", {"command": cmd}, {"cwd": root})

    denied, allowed = (lambda v: isinstance(v, str)), (lambda v: v is None)
    lines = {
        "1 gauntlet/plans/approved/ closed to every agent but the gauntlet-prosecutor": all(
            (
                denied(write(f"{root}/gauntlet/plans/approved/slug.txt")),
                denied(write("gauntlet/plans/approved/slug.txt")),
                denied(write(f"{root}/gauntlet/plans/approved/slug.txt", "gauntlet-arbiter")),
                denied(write(f"{root}/gauntlet/plans/approved/slug.txt", "gauntlet-scrivener")),
                #: an unprefixed same-named agent in the host project is not this one
                denied(write(f"{root}/gauntlet/plans/approved/slug.txt", "prosecutor")),
                allowed(write(f"{root}/gauntlet/plans/approved/slug.txt", REVIEWER)),
            )
        ),
        "2 every other path stays open, drafts included": all(
            (
                allowed(write(f"{root}/gauntlet/plans/drafts/slug.txt")),
                allowed(write(f"{root}/gauntlet/specs/approved/slug.txt", "gauntlet-arbiter")),
                allowed(write(f"{root}/docs/plans.md")),
                allowed(write(f"{root}/tests/plans/t.py")),
            )
        ),
        "3 shell writes naming the lane denied, reads and object restores pass": all(
            (
                denied(bash("sed -i 's/a/b/' gauntlet/plans/approved/slug.txt")),
                denied(bash("echo x > gauntlet/plans/approved/slug.txt")),
                denied(bash("cp draft.txt gauntlet/plans/approved/slug.txt")),
                denied(bash("rm gauntlet/plans/approved/slug.txt")),
                denied(bash("cat > gauntlet/plans/approved/slug.txt <<'EOF'\nslug: x\nEOF")),
                allowed(bash("cat gauntlet/plans/approved/slug.txt")),
                allowed(bash("grep -n 'kind:' gauntlet/plans/approved/slug.txt")),
                allowed(bash("git status --porcelain gauntlet/plans/approved/")),
                allowed(bash("git restore --source abc1234 -- gauntlet/plans/approved/slug.txt")),
                allowed(bash("git checkout abc1234 -- gauntlet/plans/approved/slug.txt")),
                allowed(bash("git commit -m 'plan: gauntlet/plans/approved/slug.txt'")),
            )
        ),
        "4 the lane directory itself is in the lane, checkout or not": all(
            (
                #: outside any checkout the path is read off its own segments, and
                #: the last segment is one of them: the write that creates the
                #: directory is the lane's first write, not its exception
                denied(write("/nogit/gauntlet/plans/approved")),
                denied(write("/nogit/gauntlet/plans/approved/slug.txt")),
                allowed(write("/nogit/gauntlet/plans/drafts/slug.txt")),
                allowed(write(f"{root}/gauntlet/plans/approved", REVIEWER)),
            )
        ),
        "5 read-only git naming the lane passes, its write forms do not": all(
            (
                allowed(bash("git grep -n foo -- gauntlet/plans/approved/")),
                allowed(bash("git grep -n 'gauntlet/plans/approved/' -- .claude/hooks")),
                allowed(bash("git ls-tree HEAD gauntlet/plans/approved/")),
                denied(bash("git grep -Ovim foo -- gauntlet/plans/approved/")),
                denied(bash("git diff --output=gauntlet/plans/approved/x.txt")),
            )
        ),
        "6 a declared runner invocation naming this lane is still denied": all(
            (
                #: the declaration names the test directory, so its one argument
                #: reaches no other lane however the argument is spelled
                denied(bash("scripts/blind.sh test gauntlet/plans/approved/slug.txt")),
                denied(bash("scripts/blind.sh test tests/a/../../gauntlet/plans/approved/slug.txt")),
            )
        ),
        "7 the lane is what a write targets, not what its text mentions": all(
            (
                allowed(
                    bash(
                        "cat > gauntlet/plans/drafts/slug.txt <<EOF\n"
                        "cites gauntlet/plans/approved/other.txt\nEOF"
                    )
                ),
                allowed(bash("echo 'gauntlet/plans/approved/slug.txt' >> notes.txt")),
                allowed(bash("find gauntlet/plans/approved -name '*.txt'")),
                allowed(bash("cmp gauntlet/plans/drafts/slug.txt gauntlet/plans/approved/slug.txt")),
                denied(bash("cat draft.txt > gauntlet/plans/approved/slug.txt")),
                denied(bash("find gauntlet/plans/approved -name '*.txt' -delete")),
            )
        ),
        #: a hook decides a tool call, so its own crash is a denial
        "no payload shape makes this hook block the call it is deciding": (
            sh.survives_hostile_payloads(__file__)
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test()) if "--self-test" in sys.argv else sh.never_block(main)
