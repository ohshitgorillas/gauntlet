#!/usr/bin/env python3
"""PreToolUse hook: `docs/gauntlet/plans/` is the gauntlet-prosecutor's lane.

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
    `docs/gauntlet/plans/` directory, unless the caller's `agent_type` is
    `gauntlet-prosecutor`
  * a `Bash` command that names a `docs/gauntlet/plans/` path and is not
    read-only, except a restore from a named git object
    (`git restore --source <rev>` or `git checkout <rev> --` onto the path),
    which copies a commit and types nothing

Allowed: every read of `docs/gauntlet/plans/`, by any agent and by the shell;
every write anywhere else, including a draft plan under
`docs/gauntlet/drafts/plans/`.

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
LANE = "docs/gauntlet/plans"
BASH_PLANS = sh.lane_pattern(LANE)

_LANE = (
    "docs/gauntlet/plans/ is the gauntlet-prosecutor's lane. An approved plan is "
    "written there by the reviewer that approved it, and by nothing else: it is "
    "the only evidence a later stage has that the plan it works from passed the "
    "plan gate. Draft under docs/gauntlet/drafts/plans/ and send the draft to the "
    "gauntlet-prosecutor. (hooks/plans-lane.py)"
)
_BASH = (
    "A shell write naming a docs/gauntlet/plans/ path is denied: " + _LANE + " Restoring "
    "an approved plan from a git object is the one shell shape that passes: "
    "`git restore --source <rev> -- docs/gauntlet/plans/<file>`."
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
        "1 docs/gauntlet/plans/ closed to every agent but the gauntlet-prosecutor": all(
            (
                denied(write(f"{root}/docs/gauntlet/plans/slug.txt")),
                denied(write("docs/gauntlet/plans/slug.txt")),
                denied(write(f"{root}/docs/gauntlet/plans/slug.txt", "gauntlet-arbiter")),
                denied(write(f"{root}/docs/gauntlet/plans/slug.txt", "gauntlet-scrivener")),
                #: an unprefixed same-named agent in the host project is not this one
                denied(write(f"{root}/docs/gauntlet/plans/slug.txt", "prosecutor")),
                allowed(write(f"{root}/docs/gauntlet/plans/slug.txt", REVIEWER)),
            )
        ),
        "2 every other path stays open, drafts included": all(
            (
                allowed(write(f"{root}/docs/gauntlet/drafts/plans/slug.txt")),
                allowed(write(f"{root}/docs/gauntlet/specs/slug.txt", "gauntlet-arbiter")),
                allowed(write(f"{root}/docs/plans.md")),
                allowed(write(f"{root}/tests/plans/t.py")),
            )
        ),
        "3 shell writes naming the lane denied, reads and object restores pass": all(
            (
                denied(bash("sed -i 's/a/b/' docs/gauntlet/plans/slug.txt")),
                denied(bash("echo x > docs/gauntlet/plans/slug.txt")),
                denied(bash("cp draft.txt docs/gauntlet/plans/slug.txt")),
                denied(bash("rm docs/gauntlet/plans/slug.txt")),
                denied(bash("cat > docs/gauntlet/plans/slug.txt <<'EOF'\nslug: x\nEOF")),
                allowed(bash("cat docs/gauntlet/plans/slug.txt")),
                allowed(bash("grep -n 'kind:' docs/gauntlet/plans/slug.txt")),
                allowed(bash("git status --porcelain docs/gauntlet/plans/")),
                allowed(bash("git restore --source abc1234 -- docs/gauntlet/plans/slug.txt")),
                allowed(bash("git checkout abc1234 -- docs/gauntlet/plans/slug.txt")),
                allowed(bash("git commit -m 'plan: docs/gauntlet/plans/slug.txt'")),
            )
        ),
        "4 the lane directory itself is in the lane, checkout or not": all(
            (
                #: outside any checkout the path is read off its own segments, and
                #: the last segment is one of them: the write that creates the
                #: directory is the lane's first write, not its exception
                denied(write("/nogit/docs/gauntlet/plans")),
                denied(write("/nogit/docs/gauntlet/plans/slug.txt")),
                allowed(write("/nogit/docs/gauntlet/drafts/plans/slug.txt")),
                allowed(write(f"{root}/docs/gauntlet/plans", REVIEWER)),
            )
        ),
        "5 read-only git naming the lane passes, its write forms do not": all(
            (
                allowed(bash("git grep -n foo -- docs/gauntlet/plans/")),
                allowed(bash("git grep -n 'docs/gauntlet/plans/' -- .claude/hooks")),
                allowed(bash("git ls-tree HEAD docs/gauntlet/plans/")),
                denied(bash("git grep -Ovim foo -- docs/gauntlet/plans/")),
                denied(bash("git diff --output=docs/gauntlet/plans/x.txt")),
            )
        ),
        "6 a declared runner invocation naming this lane is still denied": all(
            (
                #: the declaration names the test directory, so its one argument
                #: reaches no other lane however the argument is spelled
                denied(bash("scripts/blind.sh test docs/gauntlet/plans/slug.txt")),
                denied(bash("scripts/blind.sh test tests/a/../../docs/gauntlet/plans/slug.txt")),
            )
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test()) if "--self-test" in sys.argv else main()
