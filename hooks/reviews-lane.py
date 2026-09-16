#!/usr/bin/env python3
"""PreToolUse hook: `<gauntlet dir>/reviews/` is the reviewers' lane, and nearly their only one.

Wired session-wide from `.claude/settings.json`, so it binds the main agent
and every subagent, and again from the `hooks:` frontmatter of
`agents/arbiter.md` and `agents/prosecutor.md`, where
the same script confines those two agents to what they are allowed to write.

The rule it enforces: a reviewer's verdict reaches the rest of the chain from a
file the reviewer wrote itself, `<gauntlet dir>/reviews/<slug>.<N>.txt`, never
from a transcription the main agent typed. A verdict that passes through
another agent's hands on the way is a verdict that agent can soften.

Each reviewer has a second write, and exactly one: the `arbiter` the
approved block at `<gauntlet dir>/specs/approved/<slug>.txt`, and the `prosecutor`
the approved plan at `<gauntlet dir>/plans/approved/<slug>.txt`, each written on `READY`
and on nothing else. That is the same rule in the other direction — the file a
later stage works from is written by the gate itself — so this hook must allow
both or each reviewer is locked out of the lane `specs-lane.py` and
`plans-lane.py` reserve for it. Neither write is the other's: the
`prosecutor` approves no spec, and the `arbiter` approves no plan.

Denied:

  * `Write`/`Edit`/`NotebookEdit` whose target is under `<gauntlet dir>/reviews/`
    of any checkout, unless the caller's `agent_type` is `arbiter` or
    `prosecutor`
  * for those two agents, any `Write`/`Edit`/`NotebookEdit` outside
    `<gauntlet dir>/reviews/`, except the `arbiter` writing under
    `<gauntlet dir>/specs/approved/` and the `prosecutor` under
    `<gauntlet dir>/plans/approved/`
  * for those two agents, a `Read` or a `Grep` aimed under
    `<gauntlet dir>/reviews/`

A reviewer is denied the lane's contents as well as its writes, and a prior
round reaches a reviewer only as the carried verdicts in the main agent's own
return. A shell is no way round that: the reviewer profile mounts a tmpfs over
this lane, so a reviewer's `ls` of it lists an empty directory rather than the
rounds. That denial puts the numbering out of the reviewer's reach, so it
belongs to `scripts/pair.sh review <slug>`: it counts the directory from
outside and prints the one path the reviewer writes, which the brief carries
verbatim. A
reviewer that picks its own `<N>` under this denial is guessing, and a guess
that lands on a number already taken overwrites a round held in no git object.

Allowed: `Glob` for anyone, and every write elsewhere by every non-reviewer.

`Bash` is not this hook's business. A reviewer's shell is held by the mount
table instead: `bwrap-wrap.py` gives the two blind reviewers a profile with the
whole filesystem read-only and a tmpfs over this lane, so a reviewer's command
changes nothing and reads no round file, whatever it says. A non-reviewer's
shell write into the lane is stopped by the same table, which binds every lane
directory read-only in every wrapped profile.

`agent_type` is present in the payload only for subagent calls; an absent key
is the main agent. If a build omits the key for subagents too, a reviewer is
over-denied, which is the safe direction: nothing leaks, and the denial names
this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shell_shapes as sh  # noqa: E402

SPEC_REVIEWER = "arbiter"
PLAN_REVIEWER = "prosecutor"
REVIEWERS = frozenset({SPEC_REVIEWER, PLAN_REVIEWER})
#: tools that hand back a file's contents; `Glob` returns names only and is not one
READ_TOOLS = ("Read", "Grep")
LANE = sh.reviews_lane()
APPROVED = sh.specs_lane()
PLANS = sh.plans_lane()
#: the one approved-artifact lane each reviewer writes, and no other's
SECOND_WRITE = {SPEC_REVIEWER: APPROVED, PLAN_REVIEWER: PLANS}

_LANE = (
    f"{LANE}/ is the reviewers' lane: a verdict file is written by "
    "the arbiter or prosecutor that produced it, and the chain reads "
    "the verdict from that file. Nothing else writes there. "
    "(hooks/reviews-lane.py)"
)
_REVIEWER_LANE = (
    f"Reviewer: your verdict goes to {LANE}/<slug>.<N>.txt of the "
    "main checkout, the arbiter's approved block to "
    f"{APPROVED}/<slug>.txt, and the prosecutor's approved plan to "
    f"{PLANS}/<slug>.txt. Nowhere else: not the source tree, not {sh.tests_dir()}/, "
    f"not the rest of {sh.docs_dir()}/, and not the other reviewer's lane. "
    "(hooks/reviews-lane.py)"
)
_REVIEWER_READ = (
    f"Reviewer: {LANE}/ is not yours to read. A prior round reaches "
    "you as the carried verdicts in the main agent's return, never as a file: the round "
    "that rejected a brief printed the steering back verbatim, and it is written "
    "nowhere for you to find. The path you write is not yours to count either: "
    "your brief carries it, from `scripts/pair.sh review <slug>`. "
    "(hooks/reviews-lane.py)"
)


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


def _read_verdict(tool_input: sh.ToolInput, cwd: str, agent: str) -> str | None:
    """A reviewer reads no round file; `Read` names one, `Grep` names a set."""
    if agent not in REVIEWERS:
        return None
    targets = (tool_input.get("file_path"), tool_input.get("path"), tool_input.get("glob"))
    aimed = any(t and sh.path_in_lane(t, cwd, LANE) for t in targets)
    return _REVIEWER_READ if aimed else None


def _verdict(name: str, tool_input: sh.ToolInput, payload: sh.Payload) -> str | None:
    """Why this call is refused, or None to let it through."""
    return sh.dispatch(
        name,
        tool_input,
        payload,
        on_write=_write_verdict,
        on_read=_read_verdict,
        read_tools=READ_TOOLS,
    )


def main() -> None:
    sh.hook_main(_verdict, guards=sh.WRITE_TOOLS + READ_TOOLS)


def self_test() -> int:
    """Pin the five spec lines of the reviewers' lane."""
    root = "/repo"

    #: the lines below spell the kit's defaults; under a project that moved one
    #: of the three directories, the same lines run at that project's own
    write = sh.rebased(sh.probe(_verdict, root, "Write"))
    read = sh.rebased(sh.probe(_verdict, root, "Read"))
    bash = sh.rebased(sh.probe(_verdict, root, "Bash", "command"))
    denied, allowed = sh.denied, sh.allowed
    lines = {
        "1 gauntlet/reviews/ closed to everyone but the two reviewers": all(
            (
                denied(write(f"{root}/gauntlet/reviews/slug.1.txt")),
                denied(write(f"{root}/gauntlet/reviews/slug.1.txt", "scrivener")),
                allowed(write(f"{root}/gauntlet/reviews/slug.1.txt", SPEC_REVIEWER)),
                allowed(write(f"{root}/gauntlet/reviews/slug.1.txt", PLAN_REVIEWER)),
                #: installed as a plugin the harness spells the name with its
                #: plugin in front of it, and that is the same agent
                allowed(write(f"{root}/gauntlet/reviews/slug.1.txt", f"gauntlet:{SPEC_REVIEWER}")),
                allowed(write(f"{root}/gauntlet/reviews/slug.1.txt", f"gauntlet:{PLAN_REVIEWER}")),
            )
        ),
        "2 a reviewer writes its verdict and nothing else": all(
            (
                denied(write(f"{root}/src/m.py", SPEC_REVIEWER)),
                denied(write(f"{root}/tests/t.py", SPEC_REVIEWER)),
                denied(write(f"{root}/docs/testing.md", PLAN_REVIEWER)),
                denied(write(f"{root}/gauntlet/plans/drafts/slug.txt", PLAN_REVIEWER)),
            )
        ),
        "3 the arbiter alone also writes gauntlet/specs/approved/": all(
            (
                allowed(write(f"{root}/gauntlet/specs/approved/slug.txt", SPEC_REVIEWER)),
                denied(write(f"{root}/gauntlet/specs/approved/slug.txt", PLAN_REVIEWER)),
                denied(write(f"{root}/gauntlet/specs/drafts/slug.txt", SPEC_REVIEWER)),
            )
        ),
        "4 the prosecutor alone also writes gauntlet/plans/approved/": all(
            (
                allowed(write(f"{root}/gauntlet/plans/approved/slug.txt", PLAN_REVIEWER)),
                denied(write(f"{root}/gauntlet/plans/approved/slug.txt", SPEC_REVIEWER)),
                denied(write(f"{root}/docs/plans.md", PLAN_REVIEWER)),
            )
        ),
        "5 a reviewer never reads the round files": all(
            (
                denied(read(f"{root}/gauntlet/reviews/slug.1.txt", SPEC_REVIEWER)),
                denied(read(f"{root}/gauntlet/reviews/slug.1.txt", PLAN_REVIEWER)),
                denied(read(f"{root}/gauntlet/reviews/slug.1.txt", f"gauntlet:{SPEC_REVIEWER}")),
                allowed(read(f"{root}/gauntlet/reviews/slug.1.txt")),
                allowed(read(f"{root}/tests/t.py", SPEC_REVIEWER)),
            )
        ),
        #: the classifier is gone: a reviewer's shell is held by its own bwrap
        #: profile, read-only everywhere with a tmpfs over this lane, and every
        #: other hand's by the read-only lane binds of the default profile
        "6 a Bash call is not this lane's business, whoever runs it": all(
            (
                allowed(bash("echo x > gauntlet/reviews/slug.1.txt")),
                allowed(bash("sed -i 's/a/b/' src/m.py", SPEC_REVIEWER)),
                allowed(bash("cat gauntlet/reviews/slug.1.txt", SPEC_REVIEWER)),
                allowed(bash("make clean", PLAN_REVIEWER)),
            )
        ),
        #: a hook decides a tool call, so its own crash is a denial -- and a
        #: payload it cannot read is a call it cannot decide, which is a refusal
        "every payload shape is answered, and an unreadable one is refused": (
            sh.survives_hostile_payloads(__file__, guards=sh.WRITE_TOOLS + READ_TOOLS)
        ),
    }
    return sh.report(lines)


if __name__ == "__main__":
    sh.entry(self_test, main)
