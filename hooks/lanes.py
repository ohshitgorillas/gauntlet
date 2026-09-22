#!/usr/bin/env python3
"""PreToolUse hook: every lane in the chain, one row each.
`Stop` hook, behind `--stop`: a red run with no verdict does not end a turn.

Wired session-wide from the plugin manifest, so it binds the main agent and
every subagent. No agent definition wires it: a plugin-shipped agent definition
runs no `hooks:` frontmatter of its own.

The rule the whole table holds is one rule at five addresses: the file a later
stage works from is written by the hand that holds the gate, and by nothing
else. An approved spec is the only evidence the blind `scrivener` has that the
behavior it pins was reviewed; an approved plan is the only evidence a later
stage has that the plan passed the plan gate; a round file is the only verdict
a reviewer cannot have softened on the way; a verdict file is the only evidence
that a blind hand certified the red run; and a test is the thing the agent
implementing a change must not be able to edit until it passes. If the agent
that wants an artifact through can also write it, approval is a formality.

So each lane is a row, and the rows differ only in their fields:

  * `lane` -- the directory, resolved through `blind-reads.json` like every
    other path the kit names
  * `writers` -- the agents whose write into it passes. Every other hand is
    refused with `lane_msg`, the main agent included
  * `confined` -- whether those writers may write *only* into this lane, which
    is the rule for the two reviewers and the blind writer and is not the rule
    for the `juror` or for the lanes' readers
  * `second` -- the one other lane a confined writer may write, per writer:
    the `arbiter`'s approved block and the `prosecutor`'s approved plan. This
    field is why the two reviewers are not locked out of the lanes the spec and
    plan rows reserve for them
  * `spec_tree` -- whether a writer's write must land inside a
    `.claude/worktrees/*-spec` tree, which is the blind writer's rule and
    nobody else's
  * `read_msg` -- whether this lane's own writers are denied its contents.
    Only the reviewers are: a prior round reaches a reviewer as the carried
    verdicts in the main agent's return, never as a file

`Bash` is not this hook's business, at any row. A shell that writes into a lane
is stopped by the mount table -- `bwrap-wrap.py` binds every lane directory
read-only inside every wrapped profile, and gives the two reviewers a profile
with a tmpfs over their own lane -- rather than by reading the command, which
is the question no string answers. The cost is the prose: a shell write comes
back as an errno, and the explanation below survives only for the write tools,
which is what an agent should be using.

One lane is a script's rather than the writer's. A strike motion block names
tests to remove; a single test is an `Edit` and the writer's, but a whole file
cannot be, because this hook denies every hand the shell it would take. So
`scripts/pair.sh red` removes the whole-file targets itself, from the committed
block, and `scripts/strike-diff.py` checks the result at merge against that
same block.

`agent_type` is present in the payload only for subagent calls; an absent key
is the main agent, which is denied every lane. If a build omits the key for
subagents too, every gate holder is over-denied, which is the safe direction:
nothing unreviewed reaches the tree, and the denial names this file.

The `--stop` half reads `<gauntlet dir>/red/`, where `scripts/pair.sh red`
saves the run output. Every red file there wants a verdict file of the same
slug, newer than it: `pair.sh` writes the run with `>`, so a second run
overwrites the evidence in place, and a verdict older than the file it answers
ruled on output no longer on disk. The comparison is the hook's rather than the
juror's, which holds no `Bash` and could neither stat nor hash the run it ruled
on, and which writes one verdict per line and nothing else into its file.

`stop_hook_active` on the payload says this turn was itself started by this
gate. The complaints print again, so the state still reaches the user, and the
exit is 0: a gate that answers 2 to the turn it already held open is a loop
with no way out, and a second 2 says nothing the first did not.

A zero-byte red file is not a run to rule on -- `pair.sh` redirects before the
suite runs and appends `|| true`, so a crashed or killed run leaves one -- and
it fails with its own message rather than demanding a verdict on nothing.

The root is resolved from this file's own path, and neither from the cwd, which
moves within a turn, nor from `CLAUDE_PROJECT_DIR`, which is the main checkout
for one session and a worktree for another. Each checkout gates its own
`<gauntlet dir>/red/`. A missing red directory is not an unruled run: a
consumer project that copies the kit and never runs `pair.sh` is never blocked.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import hook_payload  # noqa: E402
import hook_shape  # noqa: E402
import lane_config  # noqa: E402
import lane_paths  # noqa: E402
import shell_binds  # noqa: E402

SPEC_REVIEWER = "arbiter"
PLAN_REVIEWER = "prosecutor"
WRITER = "scrivener"
JUROR = "juror"

#: tools that hand back a file's contents; `Glob` returns names only and is not one
READ_TOOLS = ("Read", "Grep")

#: the lane directories, from the one table that also drives the mount table
#: `bwrap-wrap.py` builds. A lane added to one and not the other is a hook and
#: a sandbox that disagree, and `--self-test` fails on the difference.
_DIRS = lane_config.lane_dirs()
SPECS = _DIRS["specs"]
PLANS = _DIRS["plans"]
TESTS = _DIRS["tests"]
REVIEWS = _DIRS["reviews"]
VERDICTS = _DIRS["verdicts"]
#: where an unreviewed artifact is drafted: beside its lane, never in it
SPEC_DRAFTS = lane_config.gauntlet_dir() + "/specs/drafts"
PLAN_DRAFTS = lane_config.gauntlet_dir() + "/plans/drafts"
RED_DIR = lane_config.gauntlet_dir() + "/red"

ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class Lane:
    """One lane's whole policy.

    `name` labels the row in a self-test line and nowhere else. The three
    exceptions the rows carry -- the spec-tree check, the second lane, the
    reviewer read-block -- are fields rather than branches, so a lane that does
    not take one leaves it at its default and the table stays readable as a
    table.
    """

    name: str
    lane: str
    writers: frozenset[str]
    lane_msg: str
    confined_msg: str = ""
    second: dict[str, str] = field(default_factory=dict)
    spec_tree: bool = False
    read_msg: str = ""

    @property
    def confined(self) -> bool:
        """Whether this row's writers may write into this lane and no other."""
        return bool(self.confined_msg)


_SPECS_LANE = (
    f"{SPECS}/ is the arbiter's lane. An approved spec is "
    "written there by the reviewer that approved it, and by nothing else: it is "
    "the only evidence the blind scrivener has that the behavior it is about "
    f"to pin was reviewed. Draft under {SPEC_DRAFTS}/ and send the draft "
    "to the arbiter. (hooks/lanes.py)"
)
_PLANS_LANE = (
    f"{PLANS}/ is the prosecutor's lane. An approved plan is "
    "written there by the reviewer that approved it, and by nothing else: it is "
    "the only evidence a later stage has that the plan it works from passed the "
    f"plan gate. Draft under {PLAN_DRAFTS}/ and send the draft to the "
    "prosecutor. (hooks/lanes.py)"
)
_TESTS_LANE = (
    f"{TESTS}/ is the scrivener's lane, written only in its spec tree from the "
    "committed spec block. A test whose behavior changed goes back through the "
    "spec: a re-approved line, a new `spec:` commit, a delta to the writer. A "
    "test whose assertion survives unchanged goes through "
    "`motion: rehome`, which quotes that assertion and names where it lands, its "
    "own file included. A test a change breaks and no behavior line pins goes "
    "through a `collateral:` row of that block, which quotes the assertion the "
    "writer carries through byte-identical. "
    "Any of the three, never by hand, never in the impl tree, never on the branch. "
    "(hooks/lanes.py)"
)
_WRITER_LANE = (
    f"Blind writer: you write under {TESTS}/ of your own spec tree and nowhere else. "
    f"Not the source tree, not {lane_config.docs_dir()}/, not another worktree. (hooks/lanes.py)"
)
_REVIEWS_LANE = (
    f"{REVIEWS}/ is the reviewers' lane: a verdict file is written by "
    "the arbiter or prosecutor that produced it, and the chain reads "
    "the verdict from that file. Nothing else writes there. "
    "(hooks/lanes.py)"
)
_REVIEWER_LANE = (
    f"Reviewer: your verdict goes to {REVIEWS}/<slug>.<N>.txt of the "
    "main checkout, the arbiter's approved block to "
    f"{SPECS}/<slug>.txt, and the prosecutor's approved plan to "
    f"{PLANS}/<slug>.txt. Nowhere else: not the source tree, not {TESTS}/, "
    f"not the rest of {lane_config.docs_dir()}/, and not the other reviewer's lane. "
    "(hooks/lanes.py)"
)
_REVIEWER_READ = (
    f"Reviewer: {REVIEWS}/ is not yours to read. A prior round reaches "
    "you as the carried verdicts in the main agent's return, never as a file: the round "
    "that refused a brief printed the leading back verbatim, and it is written "
    "nowhere for you to find. The path you write is not yours to count either: "
    "your brief carries it, from `scripts/pair.sh review <slug>`. "
    "(hooks/lanes.py)"
)
_VERDICTS_LANE = (
    f"{VERDICTS}/ is the juror's lane. The verdict on a red run "
    "is written there by the juror that issued it, and by nothing else: it is the "
    "only evidence anyone has that the run was certified and that a blind hand "
    "certified it. Spawn a juror with the committed spec path and the path "
    "`scripts/pair.sh red` printed. (hooks/lanes.py)"
)

#: the five lanes, in the order a call is judged against them. Order decides
#: only which refusal a call that breaks two rows at once is given, never
#: whether it is refused: a reviewer writing a test breaks the test lane and
#: its own confinement, and the message it gets is the test lane's.
LANES = (
    Lane("specs", SPECS, frozenset({SPEC_REVIEWER}), _SPECS_LANE),
    Lane("plans", PLANS, frozenset({PLAN_REVIEWER}), _PLANS_LANE),
    Lane(
        "tests",
        TESTS,
        frozenset({WRITER}),
        _TESTS_LANE,
        confined_msg=_WRITER_LANE,
        spec_tree=True,
    ),
    Lane(
        "reviews",
        REVIEWS,
        frozenset({SPEC_REVIEWER, PLAN_REVIEWER}),
        _REVIEWS_LANE,
        confined_msg=_REVIEWER_LANE,
        second={SPEC_REVIEWER: SPECS, PLAN_REVIEWER: PLANS},
        read_msg=_REVIEWER_READ,
    ),
    Lane("verdicts", VERDICTS, frozenset({JUROR}), _VERDICTS_LANE),
)


def _is_spec_tree(root: str | None) -> bool:
    """Is this checkout root a spec worktree the chain cut?"""
    if root is None:
        return False
    path = Path(root)
    return path.name.endswith("-spec") and path.parent.name == "worktrees"


def _row_write(row: Lane, target: str, cwd: str, agent: str) -> str | None:
    """Why this row refuses this write, or None if the row has nothing to say."""
    if lane_paths.path_in_lane(target, cwd, row.lane):
        if agent not in row.writers:
            return row.lane_msg
        #: the blind writer's own lane is its own tree's: the same directory in
        #: the impl tree or the main checkout is a test it must not touch
        if row.spec_tree and not _is_spec_tree(lane_paths.split_root(target, cwd)[0]):
            return row.confined_msg
        return None
    if not row.confined or agent not in row.writers:
        return None
    #: a confined writer outside its lane: the one other lane it holds, or the
    #: refusal. `second` is per writer, so neither reviewer reaches the other's
    second = row.second.get(agent)
    if second is not None and lane_paths.path_in_lane(target, cwd, second):
        return None
    return row.confined_msg


def _write_verdict(target: str, cwd: str, agent: str) -> str | None:
    """The first row that refuses this write, or None if every row passes it."""
    for row in LANES:
        refusal = _row_write(row, target, cwd, agent)
        if refusal is not None:
            return refusal
    return None


def _read_verdict(tool_input: hook_payload.ToolInput, cwd: str, agent: str) -> str | None:
    """A lane's own writers read no file in it, where the row says so.

    `Read` names one path, `Grep` names a directory and may carry a glob, so
    all three keys are scored.
    """
    targets = (tool_input.get("file_path"), tool_input.get("path"), tool_input.get("glob"))
    for row in LANES:
        if not row.read_msg or agent not in row.writers:
            continue
        if any(t and lane_paths.path_in_lane(t, cwd, row.lane) for t in targets):
            return row.read_msg
    return None


def _verdict(
    name: str, tool_input: hook_payload.ToolInput, payload: hook_payload.Payload
) -> str | None:
    """Why this call is refused, or None to let it through."""
    return hook_shape.dispatch(
        name,
        tool_input,
        payload,
        on_write=_write_verdict,
        on_read=_read_verdict,
        read_tools=READ_TOOLS,
    )


GUARDS = hook_shape.WRITE_TOOLS + READ_TOOLS


def main() -> None:
    hook_shape.hook_main(_verdict, guards=GUARDS)


#: one line per unruled or unrulable red run, keyed by what is wrong with it
_EMPTY = "{slug}: " + RED_DIR + "/{slug}.txt is empty. The run printed nothing, so there is "
_EMPTY += "nothing to rule on. Re-run `scripts/pair.sh red {slug}`, or delete the file."
_MISSING = "{slug}: no verdict. " + RED_DIR + "/{slug}.txt is a red run nobody ruled on. Spawn "
_MISSING += "a juror with " + SPECS + "/{slug}.txt and "
_MISSING += RED_DIR + "/{slug}.txt, or delete the red file if the slug was abandoned."
_UNREADABLE = "{slug}: " + RED_DIR + "/{slug}.txt could not be read ({error}). A red run this "
_UNREADABLE += "gate cannot open is one nobody can be shown a verdict for, so it is a complaint "
_UNREADABLE += "and not a file to step over. Fix its permissions, or delete it."
_STALE = "{slug}: stale verdict. " + VERDICTS + "/{slug}.txt is older than "
_STALE += RED_DIR + "/{slug}.txt, so the run it ruled on has been overwritten since. Spawn "
_STALE += "a fresh juror on the run now on disk."


def _complaints(root: Path) -> list[str]:
    """Each red run with no live verdict, and each test no commit carries."""
    out = shell_binds.untracked_tests(root)
    red_dir = root / RED_DIR
    if not red_dir.is_dir():
        return out  # no red run here; a consumer project that never runs pair.sh
    for red in sorted(red_dir.glob("*.txt")):
        slug = red.stem
        try:
            red_stat = red.stat()
        except OSError as exc:
            #: a red run that cannot be statted is not a red run that is fine.
            #: Stepping over it drops it out of the gate entirely, which is the
            #: one outcome an unruled run must never have.
            out.append(_UNREADABLE.format(slug=slug, error=exc.strerror or exc))
            continue
        if red_stat.st_size == 0:
            out.append(_EMPTY.format(slug=slug))
            continue
        verdict = root / VERDICTS / f"{slug}.txt"
        try:
            verdict_stat = verdict.stat()
        except OSError:
            out.append(_MISSING.format(slug=slug))
            continue
        if verdict_stat.st_mtime_ns < red_stat.st_mtime_ns:
            out.append(_STALE.format(slug=slug))
    return out


def looping() -> bool:
    """Whether this `Stop` payload says the gate already held the turn open once.

    Claude Code sets `stop_hook_active` on the payload when the turn it is
    ending was itself started by a `Stop` hook. The gate has already been read
    by then, so a second exit 2 buys no new information and the pair of them is
    a turn that cannot end.

    A payload this cannot read is not a loop: stdin that will not read and text
    that is not a JSON object both come back false, which holds the gate at its
    normal strength rather than dropping it on a malformed payload.
    """
    try:
        data = json.loads(sys.stdin.read())
    except (OSError, ValueError):
        return False
    return isinstance(data, dict) and data.get("stop_hook_active") is True


def stop(root: Path = ROOT, *, loop: bool = False) -> int:
    """The complaints on stderr, and 2 to hold the turn open -- 0 on a loop.

    `loop` is the guard: the complaints still print, so the state reaches the
    user unchanged, and the turn ends instead of being handed back to an agent
    that has already been told once.
    """
    complaints = _complaints(root)
    if not complaints:
        return 0
    for line in complaints:
        print(line, file=sys.stderr)
    return 0 if loop else 2


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        from lanes_selftest import self_test

        sys.exit(self_test())
    # The `--stop` guard sits here rather than inside `stop()`, because
    # `self_test()` calls `stop()` directly for four of its lines and a guard
    # inside it would pass those four vacuously under `GAUNTLET=off`. The
    # `--self-test` branch above is reached first and is never gated at all.
    if "--stop" in sys.argv:
        sys.exit(0 if lane_paths.bypassed() else stop(loop=looping()))
    main()
