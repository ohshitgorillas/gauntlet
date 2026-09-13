#!/usr/bin/env python3
"""PreToolUse hook: `docs/gauntlet/reviews/` is the reviewers' lane, and nearly their only one.

Wired session-wide from `.claude/settings.json`, so it binds the main agent
and every subagent, and again from the `hooks:` frontmatter of
`.claude/agents/gauntlet-arbiter.md` and `.claude/agents/gauntlet-prosecutor.md`, where
the same script confines those two agents to what they are allowed to write.

The rule it enforces: a reviewer's verdict reaches the rest of the chain from a
file the reviewer wrote itself, `docs/gauntlet/reviews/<slug>.<N>.txt`, never
from a transcription the main agent typed. A verdict that passes through
another agent's hands on the way is a verdict that agent can soften.

Each reviewer has a second write, and exactly one: the `gauntlet-arbiter` the
approved block at `docs/gauntlet/specs/<slug>.txt`, and the `gauntlet-prosecutor`
the approved plan at `docs/gauntlet/plans/<slug>.txt`, each written on `READY`
and on nothing else. That is the same rule in the other direction — the file a
later stage works from is written by the gate itself — so this hook must allow
both or each reviewer is locked out of the lane `specs-lane.py` and
`plans-lane.py` reserve for it. Neither write is the other's: the
`gauntlet-prosecutor` approves no spec, and the `gauntlet-arbiter` approves no plan.

Denied:

  * `Write`/`Edit`/`NotebookEdit` whose target is under `docs/gauntlet/reviews/`
    of any checkout, unless the caller's `agent_type` is `gauntlet-arbiter` or
    `gauntlet-prosecutor`
  * for those two agents, any `Write`/`Edit`/`NotebookEdit` outside
    `docs/gauntlet/reviews/`, except the `gauntlet-arbiter` writing under
    `docs/gauntlet/specs/` and the `gauntlet-prosecutor` under
    `docs/gauntlet/plans/`
  * for those two agents, any `Bash` command that writes anything at all
  * for those two agents, a `Read` or a `Grep` aimed under
    `docs/gauntlet/reviews/`, and a read-only `Bash` command naming such a path
  * for everyone else, a `Bash` command that writes and that names a
    `docs/gauntlet/reviews/` path

A reviewer is denied the lane's contents as well as its writes, because a
steering rejection burns the agent that printed it and its replacement
continues the numbering in the same directory: the `Glob` that finds the next
`<N>` is allowed and returns filenames, and a prior round reaches a reviewer
only as the carried verdicts in the main agent's own return. An evasion
rejection burns nobody — the same reviewer stays open and takes the next `<N>`
itself — so the denial holds for the same reason either way.

Allowed: every read-only command naming `docs/gauntlet/reviews/` for everyone but
those two agents, git commands that never write the working tree, `Glob` for
anyone, and every write elsewhere by every non-reviewer. A reviewer's suite
run counts as read-only in every form `shell_shapes.is_runner` recognizes —
`pytest`, `python -m pytest`, `node --test`, `npm test`, `npx vitest`, and the
invocations this repo declares in `blind-reads.json` — and an
interpreter handed an inline script (`-e`, `-c`, `--eval`) counts as a write
in all of them, which is the distinction a head word cannot make.
`docs/gauntlet/reviews/` is meant to be gitignored, so there is no git object to
restore from and no restore carve-out.

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
PLAN_REVIEWER = "gauntlet-prosecutor"
REVIEWERS = frozenset({SPEC_REVIEWER, PLAN_REVIEWER})
WRITE_TOOLS = ("Write", "Edit", "NotebookEdit")
#: tools that hand back a file's contents; `Glob` returns names only and is not one
READ_TOOLS = ("Read", "Grep")
LANE = "docs/gauntlet/reviews"
APPROVED = "docs/gauntlet/specs"
PLANS = "docs/gauntlet/plans"
#: the one approved-artifact lane each reviewer writes, and no other's
SECOND_WRITE = {SPEC_REVIEWER: APPROVED, PLAN_REVIEWER: PLANS}
BASH_REVIEWS = sh.lane_pattern(LANE)

_LANE = (
    "docs/gauntlet/reviews/ is the reviewers' lane: a verdict file is written by "
    "the gauntlet-arbiter or gauntlet-prosecutor that produced it, and the chain reads "
    "the verdict from that file. Nothing else writes there. "
    "(hooks/reviews-lane.py)"
)
_REVIEWER_LANE = (
    "Reviewer: your verdict goes to docs/gauntlet/reviews/<slug>.<N>.txt of the "
    "main checkout, the gauntlet-arbiter's approved block to "
    "docs/gauntlet/specs/<slug>.txt, and the gauntlet-prosecutor's approved plan to "
    "docs/gauntlet/plans/<slug>.txt. Nowhere else: not the source tree, not tests/, "
    "not the rest of docs/, and not the other reviewer's lane. "
    "(hooks/reviews-lane.py)"
)
_REVIEWER_BASH = (
    "Reviewer: a shell command that changes anything is denied; your writes are "
    "the Write tool onto docs/gauntlet/reviews/ and, on READY, docs/gauntlet/specs/ "
    "for the gauntlet-arbiter or docs/gauntlet/plans/ for the gauntlet-prosecutor. "
    "Read-only shell passes: cat, grep, sed -n, and a suite run "
    "in any of its recognized forms (pytest, python -m pytest, node --test, "
    "npm test, npx vitest, and the invocations this repo declares in "
    "blind-reads.json). An interpreter given an inline script (-e, -c, "
    "--eval) is a write, whatever it does. (hooks/reviews-lane.py)"
)
_REVIEWER_READ = (
    "Reviewer: docs/gauntlet/reviews/ is not yours to read. A prior round reaches "
    "you as the carried verdicts in the main agent's return, never as a file: the round "
    "that rejected a brief printed the steering back verbatim, and it is written "
    "nowhere for you to find. Glob for the next <N> is allowed and returns "
    "filenames. (hooks/reviews-lane.py)"
)
_BASH = "A shell write naming a docs/gauntlet/reviews/ path is denied: " + _LANE


def _write_verdict(target: str, cwd: str, agent: str) -> str | None:
    in_reviews = sh.path_in_lane(target, cwd, LANE)
    if agent not in REVIEWERS:
        return _LANE if in_reviews else None
    if in_reviews:
        return None
    #: each reviewer's one other lane, and never the other reviewer's
    second = SECOND_WRITE[agent]
    if sh.path_in_lane(target, cwd, second):
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
    """Pin the five spec lines of the reviewers' lane."""
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
        "1 docs/gauntlet/reviews/ closed to everyone but the two reviewers": all(
            (
                denied(write(f"{root}/docs/gauntlet/reviews/slug.1.txt")),
                denied(write(f"{root}/docs/gauntlet/reviews/slug.1.txt", "gauntlet-scrivener")),
                #: an unprefixed same-named agent in the host project is not this one
                denied(write(f"{root}/docs/gauntlet/reviews/slug.1.txt", "arbiter")),
                denied(write(f"{root}/docs/gauntlet/reviews/slug.1.txt", "prosecutor")),
                allowed(write(f"{root}/docs/gauntlet/reviews/slug.1.txt", SPEC_REVIEWER)),
                allowed(write(f"{root}/docs/gauntlet/reviews/slug.1.txt", PLAN_REVIEWER)),
                denied(bash("echo x > docs/gauntlet/reviews/slug.1.txt")),
                allowed(bash("cat docs/gauntlet/reviews/slug.1.txt")),
            )
        ),
        "2 a reviewer writes its verdict and nothing else": all(
            (
                denied(write(f"{root}/src/m.py", SPEC_REVIEWER)),
                denied(write(f"{root}/tests/t.py", SPEC_REVIEWER)),
                denied(write(f"{root}/docs/testing.md", PLAN_REVIEWER)),
                denied(write(f"{root}/docs/gauntlet/drafts/plans/slug.txt", PLAN_REVIEWER)),
                denied(bash("sed -i 's/a/b/' src/m.py", SPEC_REVIEWER)),
                allowed(bash("git show HEAD:docs/gauntlet/specs/slug.txt", SPEC_REVIEWER)),
                allowed(bash("grep -rn 'def test_' tests/", SPEC_REVIEWER)),
                #: the suite run this file promises a reviewer, in the spellings
                #: a head-word reader list cannot tell apart from a write
                allowed(bash("pytest tests/ -q", SPEC_REVIEWER)),
                allowed(bash("python -m pytest tests/ -q", SPEC_REVIEWER)),
                denied(bash("python -c \"open('x','w')\"", SPEC_REVIEWER)),
                denied(bash("node -e \"require('fs').writeFileSync('x','')\"", SPEC_REVIEWER)),
                denied(bash("make clean", SPEC_REVIEWER)),
            )
        ),
        "3 the gauntlet-arbiter alone also writes docs/gauntlet/specs/": all(
            (
                allowed(write(f"{root}/docs/gauntlet/specs/slug.txt", SPEC_REVIEWER)),
                denied(write(f"{root}/docs/gauntlet/specs/slug.txt", PLAN_REVIEWER)),
                denied(write(f"{root}/docs/gauntlet/drafts/specs/slug.txt", SPEC_REVIEWER)),
            )
        ),
        "4 the gauntlet-prosecutor alone also writes docs/gauntlet/plans/": all(
            (
                allowed(write(f"{root}/docs/gauntlet/plans/slug.txt", PLAN_REVIEWER)),
                denied(write(f"{root}/docs/gauntlet/plans/slug.txt", SPEC_REVIEWER)),
                denied(write(f"{root}/docs/plans.md", PLAN_REVIEWER)),
            )
        ),
        "5 a reviewer never reads the round files": all(
            (
                denied(read(f"{root}/docs/gauntlet/reviews/slug.1.txt", SPEC_REVIEWER)),
                denied(read(f"{root}/docs/gauntlet/reviews/slug.1.txt", PLAN_REVIEWER)),
                denied(bash("cat docs/gauntlet/reviews/slug.1.txt", SPEC_REVIEWER)),
                allowed(read(f"{root}/docs/gauntlet/reviews/slug.1.txt")),
                allowed(read(f"{root}/tests/t.py", SPEC_REVIEWER)),
            )
        ),
        "6 read-only git naming the lane passes, its write forms do not": all(
            (
                allowed(bash("git grep -n foo -- docs/gauntlet/reviews/")),
                allowed(bash("git grep -n 'docs/gauntlet/reviews/' -- .claude/hooks")),
                allowed(bash("git ls-tree HEAD docs/gauntlet/reviews/")),
                denied(bash("git grep -Ovim foo -- docs/gauntlet/reviews/")),
                denied(bash("git diff --output=docs/gauntlet/reviews/x.txt")),
            )
        ),
        "7 a reviewer's read-only git passes, its write forms do not": all(
            (
                allowed(bash("git grep foo", SPEC_REVIEWER)),
                denied(bash("git grep foo -- docs/gauntlet/reviews/", SPEC_REVIEWER)),
                denied(bash("git reflog expire --all", SPEC_REVIEWER)),
                denied(bash("git diff --output=out.txt", SPEC_REVIEWER)),
            )
        ),
    }
    for label, ok in lines.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    return 0 if all(lines.values()) else 1


if __name__ == "__main__":
    sys.exit(self_test()) if "--self-test" in sys.argv else main()
