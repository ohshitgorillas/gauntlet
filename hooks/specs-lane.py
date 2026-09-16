#!/usr/bin/env python3
"""PreToolUse hook: `<gauntlet dir>/specs/approved/` is the arbiter's lane.

Wire it session-wide from `.claude/settings.json`, so it binds the main agent
and every subagent, and again from the `hooks:` frontmatter of
`agents/arbiter.md` and `agents/scrivener.md`.

An approved spec is the only thing the blind `scrivener` works from. If the
agent that wants a test can also write the file the test is generated from,
approval is a formality: the main agent states the behavior, hands it to the
writer, and the adversarial review it was supposed to survive never happened.
So the file is written by exactly one hand, the one that holds the gate.

Denied:

  * `Write`/`Edit`/`NotebookEdit` whose target is under a `<gauntlet dir>/specs/approved/`
    directory, unless the caller's `agent_type` is `arbiter`
  * a `Bash` command that names a `<gauntlet dir>/specs/approved/` path and is not
    read-only, except a restore from a named git object
    (`git restore --source <rev>` or `git checkout <rev> --` onto the path),
    which copies a commit and types nothing

Allowed: every read of `<gauntlet dir>/specs/approved/`, by any agent and by the shell;
every write anywhere else, including a draft spec under
`<gauntlet dir>/specs/drafts/`.

`agent_type` is present in the payload only for subagent calls; an absent key
is the main agent, which is denied. If a build omits the key for subagents
too, the arbiter is over-denied, which is the safe direction: no
unreviewed spec reaches the writer, and the denial names this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import shell_shapes as sh  # noqa: E402

REVIEWER = "arbiter"
LANE = sh.specs_lane()
#: where an unreviewed block is drafted: beside the lane, never in it
DRAFTS = sh.gauntlet_dir() + "/specs/drafts"

_LANE = (
    f"{LANE}/ is the arbiter's lane. An approved spec is "
    "written there by the reviewer that approved it, and by nothing else: it is "
    "the only evidence the blind scrivener has that the behavior it is about "
    f"to pin was reviewed. Draft under {DRAFTS}/ and send the draft "
    "to the arbiter. (hooks/specs-lane.py)"
)
#: the lane's whole policy: the one writer passes, every other hand is
#: refused with the reason. A shell that writes into the lane is stopped by
#: the mount table instead, so no lane hook is wired on `Bash` any more.
_verdict = sh.sole_writer_lane(LANE, REVIEWER, _LANE)


def main() -> None:
    sh.hook_main(_verdict, guards=sh.WRITE_TOOLS)


def self_test() -> int:
    """Pin the three spec lines of the approved-spec lane."""
    root = "/repo"

    write, bash = sh.probes(_verdict, root)
    denied, allowed = sh.denied, sh.allowed
    lines = {
        "1 gauntlet/specs/approved/ closed to every agent but the arbiter": all(
            (
                denied(write(f"{root}/gauntlet/specs/approved/slug.txt")),
                denied(write("gauntlet/specs/approved/slug.txt")),
                denied(write(f"{root}/gauntlet/specs/approved/slug.txt", "scrivener")),
                denied(write(f"{root}/gauntlet/specs/approved/slug.txt", "cavecrew-builder")),
                allowed(write(f"{root}/gauntlet/specs/approved/slug.txt", REVIEWER)),
                #: installed as a plugin the harness spells the name with its
                #: plugin in front of it, and that is the same agent
                allowed(write(f"{root}/gauntlet/specs/approved/slug.txt", f"gauntlet:{REVIEWER}")),
            )
        ),
        "2 every other path stays open, drafts included": all(
            (
                allowed(write(f"{root}/gauntlet/specs/drafts/slug.txt")),
                allowed(write(f"{root}/gauntlet/plans/approved/slug.txt")),
                allowed(write(f"{root}/tests/specs/t.py")),
                allowed(write(f"{root}/docs/lane.txt", "scrivener")),
            )
        ),
        "4 the lane directory itself is in the lane, checkout or not": all(
            (
                #: outside any checkout the path is read off its own segments, and
                #: the last segment is one of them: the write that creates the
                #: directory is the lane's first write, not its exception
                denied(write("/nogit/gauntlet/specs/approved")),
                denied(write("/nogit/gauntlet/specs/approved/slug.txt")),
                allowed(write("/nogit/gauntlet/specs/drafts/slug.txt")),
                allowed(write(f"{root}/gauntlet/specs/approved", REVIEWER)),
            )
        ),
        #: the classifier is gone: the lane's shell half is the mount table,
        #: which binds this directory read-only inside every wrapped profile
        "8 a Bash call is not this lane's business, whatever it names": all(
            (
                allowed(bash("sed -i 's/a/b/' gauntlet/specs/approved/slug.txt")),
                allowed(bash("cat > gauntlet/specs/approved/slug.txt <<'EOF'\nkind: new\nEOF")),
                allowed(bash("cat gauntlet/specs/approved/slug.txt")),
            )
        ),
        #: a hook decides a tool call, so its own crash is a denial -- and a
        #: payload it cannot read is a call it cannot decide, which is a refusal
        "every payload shape is answered, and an unreadable one is refused": (
            sh.survives_hostile_payloads(__file__, guards=sh.WRITE_TOOLS)
        ),
    }
    return sh.report(lines)


if __name__ == "__main__":
    sh.entry(self_test, main)
