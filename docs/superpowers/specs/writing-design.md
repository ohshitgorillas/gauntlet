Status: proposed.

# Gauntlet writing

## Why

Writing is phase 5, block `write` of the tree run `gauntlet-tree`, after the baseline (`gauntlet-design.md`). That design gives the block's signature, its nodes `enter` and `handoff`, the approved revisions and the exit to planning; this file gives the rest of the block and nothing it restates. Every path is in the tree unless it names the pack root.

Inside one loop, the divvyer cuts the approved plan and spec into blocks and orders them in waves, within one stage of the plan. Test writers write the tests from the approved spec, then coders write the code from the approved plan. The amicus briefs the owner on every red: a block's contest, a blocked block, a failed commit, a red test run, a failed final commit or an iteration that made no progress. It rules on nothing; the owner chooses at `bench` (the owner-control design, section 2). A wrong spec or plan is revised in the same loop when the owner's direction asks for it, tried by a fresh reviewer and approved by the owner at `bench`. The owner's back to planning ends the block.

What the tree holds for the concerns writing touches:

- Running a test command for an agent: one copy, `fence/checks.py`, which runs the brief command recorded in `gauntlet/settings.json` of its root and returns its last 200 lines. Every writer's `fence-checks` runs the brief command, which prints one line per test and no test source, so no traceback reaches a coder; writing reuses `checks.py` with the settings-file change of `fence/files.py` and `fence/checks.py` (settings) below.
- Baseline comparison: designed and unbuilt, `.shared/red.py` (`gauntlet-design.md`), shared with landing. The cut design's `gauntlet/baseline/<slug>.brief.txt` holds the brief command's output, one line per test.
- Commits: no copy. No Gauntlet file commits, and `fence/files.py` has no git tool.
- Round logic: designed and unbuilt, `.shared/rounds.py` (spec review design). Writing's revision hearing uses it through a `write/scripts/ledger.py` `Profile`, as `gauntlet-design.md` requires.
- Steering screening: designed and unbuilt, the `screen` workflow (spec review design). Its fence, `screen/screener.mcp.json`, reads only `gauntlet/plans/*.txt` and `gauntlet/specs/*.txt`, so it cannot read a revision round.
- Hidden reads: designed and unbuilt, `FENCE_HIDE` in `fence/files.py` (`gauntlet-design.md`). The coder's blindness to `tests/` rests on it.
- Roles: no copy usable here. `gauntlet-design.md` gives writing its own `write/commands/`. The one role shared with another phase is the amicus, which this design homes as an included block (`amicus/`, below).
- Fanned-out writers: Archon runs `include:` with `fan_out:` inside the run, but rejects a `wait:` anywhere in the fanned-out block. The only wait is `bench`, in writing's loop.

The repository's `.archon/config.yaml` `env:` reaches bash nodes only (cut design), so the fences and `stage.py` read `gauntlet/settings.json`, which node `settings` of the tree run writes, and no fence config carries a test value.

## Terms

- **Block**: one writer's share of the work: `{ id, kind, specs, steps, paths, ruling }`, `kind` is `tests` or `code`. `specs` lists spec ids, `steps` lists plan steps, `paths` lists every file the block may change. `ruling` holds the owner's direction text, verbatim, when the cut answers a direction, and `""` otherwise.
- **Wave**: blocks of one kind that share no path and run in one fan-out, one block at a time.
- **Cut**: the divvyer's waves for one cause, test waves first. The first cut covers the whole stage's plan steps and the specs they serve. A later cut covers only what its cause affects; `stage.py state` carries the unrun waves of the cuts it replaces. The cause is an owner's direction `tests` or `code`, or an approved revision.
- **Move** `N`: one file `gauntlet/write/<slug>.<kind>.N.<ext>`, with one counter over every kind. Each loop iteration makes at most one move besides a direction or a writing ruling.
- **Red**: the latest test run timed out and the brief baseline did not, or names a failing test (`FAILED` or `ERROR`) that the brief baseline does not name as failing. A run that exits non-zero with no failing line is also red when the brief baseline exited 0. A baseline failure that now passes is not red.
- **Revision round** `N`: one file `gauntlet/revisions/<slug>.N.txt`, with its review, ruling and summary, under `.shared/rounds.py`. Line 1 is `Revises: plan` or `Revises: spec`. Line 2 is `Answers: <tree path>`, naming the direction, or the entered plan revision it follows. The clauses it changes come after, each as it now reads; `enter` copies the round to its revision file without the two header lines. A spec revision that follows a plan revision and changes nothing holds `No change.` after the two lines.
- **Plan files**, **spec files**: `approved/<slug>.txt`, then each `approved/<slug>.rev<N>.txt` in order of N. An agent that needs the plan or the spec is handed these.
- **Stage**: the plan's stage `stage` (the block's input, counted from 1; a plan with no stage lines is stage 1), its steps and the specs they serve. A stage's writing starts at `start`, the highest move on disk when the block began (`stage.py open`): every rule of `state` reads only files whose move is above `start`, and every counter continues above it, so the earlier stages' records that `copy-in` brought in (worktree cut design) are history and not state. The divvyer cuts blocks and waves within the stage, never across one, and each stage seals with a final commit of its own (`runtime-model-design.md`, "Commit model"). `gauntlet-design.md` gives the stages' order, bound and node ids.
- **Amicus**: the owner-control design's briefing role (the owner is the bench); it rules on nothing. It runs, and the loop stops for the owner at `bench`, on every amicus case, and the existence of the case is the trigger, never an agent's judgment: a **red** (the latest test run is red), a block's **contest** (a writer says a test or its spec is wrong), a **blocked** block (edits outside its `paths`; the grounds are those paths), a **failed commit** (a block's commit, or the final commit by `seal`), and the **idle** case (an iteration that wrote no file). `cap` is no amicus case: it asks a plain reply. The amicus works out why the run failed, explains it to the owner in plain words with no other agent checking the explanation, and discusses the way forward with the owner. The discussion is a wait: the amicus is the agent node `amicus` of block `write`'s loop `work`, ahead of its sole terminal wait `bench`; each answer of `discuss` runs one more iteration in which the amicus reads the owner's words as `$LOOP_PREV.bench.output.text` and answers, and any other answer ends the discussion (contracts A30). One shared included block, `amicus/`, holds the role for writing, the mend and the review before landing, as `screen` does for steering: a role file resolves only from its own workflow's `commands/` (contracts A6), so one block states the role once where per-workflow copies would restate it in `write/commands/` and `mend/commands/`.
- **Direction**: the owner's answer to an amicus case that ends the discussion, recorded by `stage.py record` as the file `gauntlet/write/<slug>.direction.N.md`, N the next free move, once. Line 1 is `Rework: tests`, `Rework: code`, `Rework: spec`, `Rework: plan` or `Rework: planning`, from the owner's choice at `bench` (options below); line 2 is `Landed: <n>`, the stages landed before this one; then a blank line and the owner's text verbatim, which may be empty. The next pass is bound by it: the file names which part is reworked, so no agent rules on that. `stage.py state` reads it: `tests` and `code` start a cut, `spec` and `plan` start a revision hearing, `planning` ends the block. Every writer, the divvyer and the reviser are handed the latest direction's text (blocks carry it as `ruling`; the divvyer and the reviser read every direction), and no direction is edited or removed. The amicus record `gauntlet/write/<slug>.amicus.N.md`, N the same next free move, holds the amicus's explanation as it stands, rewritten each turn; it is no move. The mend writes its own direction files, `gauntlet/mend/<slug>.direction.N.md` (landing design), in this form with `Rework: code`, `Rework: tests`, `Rework: again` (the tests rerun with no mender) or `Rework: planning`. Both files reach plan review on a back to planning (`gauntlet-design.md`, "Back to planning").

Files in `gauntlet/write/`:

| File | Writer | Rule |
|---|---|---|
| `<slug>.cut.N.json` | `stage.py cut` | the divvyer's waves and their cause; a rejected cut holds its problems and no waves |
| `<slug>.blocks.N.json` | `stage.py result` | one wave's block outcomes, in block order; each committed block also holds `outside`, the paths of its commit that lie outside the block's `paths` (the paths mark, `[]` when none), the second mechanical scope check, read by the review before landing (landing design) |
| `<slug>.run.N.txt` | node `test` | `exit=<n> timed_out=<true\|false>`, then the brief command's output |
| `<slug>.seal.N.txt` | node `seal` | `exit=<n>`, then git's and the hooks' output; `nothing` when the tree had no change |
| `<slug>.direction.N.md` | `stage.py record` | the owner's direction (Terms), once |
| `<slug>.amicus.N.md` | node `amicus` | the amicus's explanation of the case at move N, rewritten each turn; no move counts it |
| `<slug>.ruling.N.txt` | `stage.py record` | the owner's reply to a `cap` case, verbatim; once |
| `<slug>.leftover.N.patch` | `stage.py result` | `runtime-model-design.md`, "Commit model" |
| `<slug>.scope.rev<M>.txt` | `stage.py state` | the scope marks of the approved plan revision `approved/<slug>.rev<M>.txt`, once; no move counts it; read by `stage.py`, the divvyer and the review before landing |

Files in `gauntlet/revisions/`: `<slug>.N.txt` (reviser), `<slug>.review.N.txt` (reviewer, or `ledger.py screen` for `SCREENED`), `<slug>.ruling.N.txt` (`stage.py record`), `<slug>-summary.N.md` (reporter), each as `runtime-model-design.md`, "Hearing state", rules them.

## Modules

### `fence/files.py` (commit)

Adds the tool `commit`, registered only when `FENCE_COMMIT=1`. The writer pens the message and commits its own block. The tool's rules (which paths it adds, `exit=0 nothing`, the lock, the one retry after a hook changed files, what it returns) are `runtime-model-design.md`'s, heading "Commit model". Replaces nothing.

```python
# FENCE_COMMIT=1: commit is registered; unset: absent.
# Every path this server process wrote, edited, copied or deleted is recorded.
def commit(message: str, paths: list[str]) -> str: ...
# Rules, errors and return value: runtime-model-design.md, "Commit model".
```

Suite: `fence/test_files_commit.py`, run as `docs/testing.md` states with the folder `fence`, against a real git repository under `tmp_path`. It pins a commit holding exactly `paths` while another path is staged, the refusal of a recorded path left out of `paths`, a listed path that does not exist left out of the commit, the "nothing" answer when no path changed and the one retry after a hook changed files (both `runtime-model-design.md`, "Commit model"), a failing `pre-commit` hook giving a non-zero `exit` and no commit, and the tool's absence without `FENCE_COMMIT`.

### `fence/files.py` and `fence/checks.py` (settings)

Both servers take the repository's test settings from `gauntlet/settings.json` of their root, which node `settings` of the tree run writes once per tree run from the repository's `env:` (cut design). No fence config carries a test value and no launch line builds one, so every fence launches as plainly as the intake design's. Replaces the `FENCE_TEST_COMMAND` and `FENCE_TEST_TIMEOUT` environment of `checks.py`.

```python
# checks.py: run_tests() runs settings["brief"] with timeout settings["timeout"] (default 900 s) as it ran FENCE_TEST_COMMAND,
#   a process-group kill at the timeout, and returns the last 200 lines. The brief command prints one line per test and no test source.
#   FENCE_CUT=1 (the coder's fence, whose value sits in the section `write-code/write-code.yaml`): each returned line is cut at its first " - " by .shared/red.py's cut, whatever the
#   repository's command prints, so no assertion message reaches a coder.
#   File missing or "brief" blank at the first call: the tool returns the error, runs nothing.
# files.py: the entry "@base" in FENCE_READ or FENCE_WRITE stands for the paths in settings["base"] (none when the list is empty);
#   an entry "@base" with the file missing stands for nothing.
```

Suite: `fence/test_settings.py`, run as `docs/testing.md` states with the folder `fence`, against a settings file under `tmp_path`. It pins the command and timeout read from the file, the default 900, the `@base` expansion, the coder-fence cut of a `FAILED <id> - <message>` line, and the refusal on a missing file.

### `write/scripts/ledger.py`

Writing's revision-hearing `Profile` on `.shared/rounds.py`. It defines `PROFILE` and calls `main(PROFILE)` under `if __name__ == "__main__"`, so `stage.py` imports `PROFILE`. Header and import lines are those of the planning ledger. Replaces nothing.

```python
PROFILE = Profile(
    folder="gauntlet/revisions", author="reviser", reviewer="reviewer", letter="r",
    verdicts=("SOUND", "UNSOUND", "APPROACH THE BENCH", "OBJECTION: LEADING", "OBJECTION: NON-RESPONSIVE", "SCREENED"),
    retire=None,                     # the reviewer is a fresh node each round: no slot to retire, "next" is never "vacant"
    non_responsive="OBJECTION: NON-RESPONSIVE",
    attempts=("UNSOUND", "APPROACH THE BENCH"),
    owner_cases=(
        OwnerCase("SOUND", "review", (("approve", "Approve"), ("revise", "Revise")), summary=True, ends="approve"),
        OwnerCase("APPROACH THE BENCH", "bench", (("reply", "Reply"),), summary=False, ends=""),
    ),
    filed=lambda folder, slug, round: True,
)
```

Suite: `write/tests/test_ledger.py`. It pins `UNSOUND` counted as an attempt, `SOUND` opening case `review`, and `OBJECTION: LEADING` retiring no slot.

### `write/scripts/stage.py`

Writing's progress: what is owed next, the cut and wave records, red, the paths mark, the owner's cases outside the hearing, the direction and the block's end. It derives everything from `gauntlet/write/`, `gauntlet/revisions/` and `approved/` (what that gives a resume: `runtime-model-design.md`, "Resume and rerun"). It takes the hearing's state, docket, screen and record from `.shared/rounds.py` with `PROFILE`, and red from `.shared/red.py`, and computes none of them itself. Standard library only. Replaces nothing.

```python
# /// script
# requires-python = ">=3.12"
# ///
# Env: INPUTS_MODE, INPUTS_SLUG, INPUTS_PLAN, INPUTS_SPEC, INPUTS_BRIEF, INPUTS_STAGE (block inputs); INPUTS_START in the
#   loop; INPUTS_BASE in docket; per mode below. The test base is "base" of gauntlet/settings.json (none when the file is
#   missing or the list is empty).
#   The slug is INPUTS_SLUG; the hearing's rounds.py calls take theirs from INPUTS_ITEMS through .shared/pin.py's slug,
#   the one derivation (worktree cut design). Every rounds.state and rounds.docket call passes first (runtime-model-design.md, "Hearing state"): the round after
#   the latest closed round, 1 when none, so each revision hearing in gauntlet/revisions/ starts there.
#   Stage (Terms): every rule below reads only files whose move is above START, the highest move when the block began; the
#   stage's plan steps are the steps of approved/<slug>.scope.txt (plan review design) whose stage is INPUTS_STAGE, then those
#   of each gauntlet/write/<slug>.scope.rev<M>.txt (the marks of an approved plan revision; Terms, Files in `gauntlet/write/`) in order of M, a step of
#   a later file replacing the step of the same number, and the counters of move and round continue above whatever the tree
#   already holds. A plan revision carries the `Stage <k>:` line above every step it holds, a text-only change included (plan review design, Terms "Plan grammar").

def open_() -> dict: ...          # mode "open", before the loop: { "start": highest move, 0 when none, "base": lines of <slug>.iter.txt }

def state(start: int) -> dict: ...
# Each call first writes, for each gauntlet/plans/approved/<slug>.rev<M>.txt that has no gauntlet/write/<slug>.scope.rev<M>.txt, that
#   file (Terms, Files in `gauntlet/write/`): plan-review/scripts/scope.py's function `marks` over the revision and the item file, `revision=True` (imported relative to this file, as
#   .shared/ is; the one parse of the plan grammar, plan review design Homes row "The plan grammar"), the Files-table line
#   unchanged. It is read from the approved files, so a failure resume that lost it writes it again.
#   It then appends one line to gauntlet/write/<slug>.iter.txt (state runs once per iteration), holding the highest move
#   and rounds.state's round, owed and guard-record count, which docket counts.
# { "next": "divvy" | "tests" | "code" | "test" | "seal" | "amicus" | "revise" | "review" | "none",
#   "move": int,                  # the next move's N
#   "wave": [block],              # tests and code: one wave, the first unrun one in this order: test waves before code
#                                 #   waves; of one kind, the waves carried from the cuts the latest cut replaced, oldest
#                                 #   first, before the latest cut's. Carried: a replaced cut's unrun waves, and of its run
#                                 #   waves the blocks that did not end committed (blocked, contest or commit-failed). A carried block loses the specs (tests) or steps
#                                 #   (code) a newer cut holds; a block left empty is dropped, and so is a wave left with no block.
#                                 #   Each block's ruling is filled from its own cut's cause. A blocks file closes the wave
#                                 #   handed out at its move.
#   "kind": "plan" | "spec" | "", # revise and review
#   "round": int,                 # revise and review: rounds.state's round
#   "file": str,                  # review: gauntlet/revisions/<slug>.<round>.txt
#   "cause": str,                 # divvy: the tree paths the cut answers, newline-separated; amicus: the case's name (red,
#                                 #   contest, blocked, commit-failed or idle) on line 1, then the case's files,
#                                 #   newline-separated, the leftover patch of the case's move among them when there is one;
#                                 #   revise: the tree path the round answers
#   "problems": str,              # divvy: the latest rejected cut's problems, "" when none
#   "plans": str, "specs": str,   # plan files and spec files, newline-separated absolute paths; "" for a "" input
#   "approved": str }             # seal: the summary files of the revision rounds the owner approved (an approve ruling),
#                                 #   in order of N, newline-separated tree paths; a round sent back is not listed
# First that holds:
#   latest direction `Rework: planning`, or latest seal exit 0 or nothing: none.
#   a revision owed: latest direction `Rework: spec` or `Rework: plan` not yet answered by an approved round; an entered
#     plan revision, spec not "", and no spec round answering it closed. A round is closed by an approve ruling, or a SOUND
#     review of a "No change." round. next from rounds.state: reviser owes: revise; reviewer owes: review; owner owes:
#     none (runtime-model-design.md, "Resume and rerun").
#   a case for the amicus: the latest blocks file holds a contest, commit-failed or blocked newer than the latest direction
#     (a blocked block's grounds are the paths outside it; the owner's direction `tests` or `code` starts the cut that carries
#     the block, and the case precedes test and seal, so no seal runs over a blocked wave); the
#     latest run is red and newer than the latest direction; the latest seal exit is not 0 and is newer than the latest
#     direction. next amicus, cause as above. A discussion that gave no direction leaves the case open, so the next
#     iteration is the amicus again. A reply to a cap case opens no amicus case.
#   no cut since the latest cause, or the latest cut rejected: divvy. The cause is the latest direction when it is `tests`
#     or `code`; after a revision, every round closed since the latest direction, oldest first; no direction and no round: the stage's plan steps and the specs
#     they serve in the approved files.
#   an unrun wave, the latest cut's or a carried one: the kind of the wave handed out.
#   no run since the latest wave or cut: test.
#   no seal since the latest run: seal.

def cut(move: int, divvy: str, cause: str) -> dict: ...
# Writes <slug>.cut.<move>.json: { "cause", "waves", "problems" }. Problems, each one line: an empty wave; a code
#   wave before a test wave; a path in two blocks of one wave; a tests block path outside tests/ and
#   the test base; a code block path inside tests/ or gauntlet/; a block id repeated; a step of an
#   uncommitted earlier block missing from a code cut; a step outside the stage; a code block in a cut answering a
#   direction `tests`; a test block in a cut answering a direction `code`. Any problem: "waves" is []. stdout { "problems" }.

def result(move: int, tests: str, code: str) -> dict: ...
# Writes <slug>.blocks.<move>.json from the wave's ordered outcomes, the one of tests and code not ""; an { "archon_failed": true } item is
#   recorded as commit-failed with its error. stdout { "contested": bool }.
# The paths mark: for each committed block, `git -C <tree> diff-tree --no-commit-id --name-only -r <commit>` against the block's
#   paths; the block's record holds "outside", the changed paths no entry of "paths" covers, [] when none. A mark is no stop.
# A block of the wave that did not end committed: the leftover patch and the restore of the tree to HEAD are
#   runtime-model-design.md's, "Commit model"; the patch is named in the amicus case's files.

def red(run: str, brief: str) -> bool: ...
# The latest run file and the brief baseline, passed to .shared/red.py's red with no head; returns its answer.

def docket(start: int, base: int) -> dict: ...
# { "case": <rounds.docket case> | "amicus" | "cap" | "none", "ask": bool, "attention": str,
#   "options": [ { "id", "label" } ], "round": int, "summary": bool, "amicus": bool,
#   "name": str, "files": str,   # case amicus: the case (red, contest, blocked, commit-failed or idle) and its files, newline-separated
#                                #   (idle: the iteration file and the latest cut, blocks, run, seal, direction and revision files)
#   "record": str,  # case amicus: the amicus record's tree path, gauntlet/write/<slug>.amicus.<N>.md, N one above the highest move (the direction takes it too)
#   "end": "written" | "planning" | "" }
#   First that holds: rounds.docket's case when not none, except a SOUND review of a "No change." round;
#   amicus (state's next is amicus, or the last rounds.IDLE lines of <slug>.iter.txt hold the highest move and the round,
#   owed and guard-record count docket now reads, so an iteration that wrote no file is the idle case at once; "amicus" is
#   true in both, and the case's name is state's cause or "idle"); cap (loop iterations since open, the lines of
#   <slug>.iter.txt above INPUTS_BASE, >= rounds.CAP); none.
#   amicus: ask true; attention is the case's name, then the text of <slug>.amicus.<move>.md verbatim once the amicus has written
#   it, else the case's name alone; options: discuss, only when state's next is amicus ("Discuss it with the amicus (your words in the text)"), rework-tests,
#   rework-code (each "Run the tests / the code again with my direction"), revise-spec when spec is not "", revise-plan when
#   plan is not "" ("Revise the spec / the plan, with my direction"), and back-to-planning ("Back to planning").
#   cap offers one option, reply. end follows the first rule of state. ask is false whenever end is not "".

def record(round: int, case: str, decision: str, text: str) -> dict: ...
# decision "": records nothing. Hearing cases: rounds.record. cap: writes <slug>.ruling.N.txt, N the next free move number
#   of gauntlet/write/. amicus: decision discuss records nothing; any other decision writes <slug>.direction.N.md (Terms),
#   N the case's move, line 1 `Rework: ` and tests, code, spec, plan or planning for rework-tests, rework-code, revise-spec,
#   revise-plan or back-to-planning, line 2 `Landed: ` and INPUTS_STAGE less one, the owner's text verbatim after a blank line.
#   stdout { "enter": tree path of the round file of the earliest approve ruling (a case review, decision approve) that no
#   `approved/<slug>.rev<N>.txt` of its kind holds yet, else "" } (the Mth approve ruling of kind plan or spec, in order of
#   round, against M - 1 revision files of that kind). It is read from the rulings and the approved files on every call, not from
#   this call's decision, so the iteration after the approval and the first iteration of a failure resume both enter the revision.

def close() -> dict: ...
# { "outcome": "written" | "planning", "direction": absolute path of the latest direction when outcome is planning, "" when written,
#   "amicus": absolute path of the amicus record of that direction's N, "" when written,
#   "summary": the plan summary file's text when plan is not "", then the text of each approved revision summary in order of N,
#   blank-line separated; "" when planning }

def main() -> int: ...             # dispatches on INPUTS_MODE, prints JSON to stdout
```

Suite: `write/tests/test_stage.py`, run as `docs/testing.md` states with the folder `write/tests`. It drives `main` through real files under `tmp_path`. It pins each rule of `state` in its precedence, the wave order and each carry rule of `wave`, a red run reaching the amicus, the start rule that makes an earlier stage's records history, the paths mark of a commit outside its block, each cut problem, `record` writing a direction at the case's move and nothing for `discuss`, and `close` on a `planning` direction.

### Roles: `write/commands/divvyer.md`, `reviser.md`, `reviewer.md`, `reporter.md`

Each starts a fresh session, primed from files. Replace nothing.

```markdown
divvyer.md
Inputs: the cause, the stage, the problems of the latest rejected cut, the plan files, the spec files, the plan's scope
marks (approved/<slug>.scope.txt and each gauntlet/write/<slug>.scope.rev<M>.txt (Terms, Files in `gauntlet/write/`) in order of M; the plan review design gives the step grammar and the marks), every earlier cut and blocks file, every direction and writing ruling.
Output the waves: test waves before code waves; one block per related set of specs or plan steps; blocks of one
wave share no path; a block that needs another's files sits in a later wave. Cut only the stage's own steps and the
specs they serve, never across a stage. Read each step's item ids and its mark in the scope marks: a step marked "added
scope" serves no item of the item file; cut it in a block of its own, so the review before landing can see it, and
never fold it into another step's block. A cause other than the approved files: only the tests and code it affects. A
block that answers an owner's direction carries the direction's text, verbatim, as its ruling. Test block paths sit in
tests/ or the repository's test base files; code block paths sit outside tests/ and gauntlet/. Writes nothing.
Tools: the fence-files server only.
```

```markdown
reviser.md
Inputs: round N, kind (plan or spec), the tree path the round answers, the plan files, the spec files, every
revision ruling, every direction, the latest review (may be "").
Write gauntlet/revisions/<slug>.N.txt: "Revises: <kind>", "Answers: <path>", then each clause it changes as it
now reads, nothing else; a plan step it writes sits under its `Stage <k>:` line (plan review design, Terms "Plan grammar"). Answering a direction: what the owner's words ask, and nothing past it. Following a plan
revision: only the specs it affects, or "No change.". Latest review OBJECTION: LEADING or SCREENED: the previous
round with the quoted text removed, nothing else changed. A spec revision holds no source text.
Never tell the reviewer how to rule. Never paraphrase the owner's words.
Tools: the fence-files server only.
```

```markdown
reviewer.md
Input: round N. Read the round, the path it answers, the plan files, the spec files and every revision ruling.
Write gauntlet/revisions/<slug>.review.N.txt once. Line 1 "Verdict: <verdict>", then the grounds.
SOUND: it fixes what it answers, changes nothing else, and leaves the plan or spec consistent.
UNSOUND: each flaw. APPROACH THE BENCH: a product question for the owner. OBJECTION: LEADING: steering, quoted.
OBJECTION: NON-RESPONSIVE: a demand of an earlier review dodged, quoted. Never prescribe a fix.
Tools: the fence-files server only.
```

```markdown
reporter.md
Inputs: the round file to read, gauntlet/revisions/<slug>.N.txt of a SOUND round N, and the summary file to write,
gauntlet/revisions/<slug>-summary.N.md. Write the summary file once: what the revision changes in the plan or
spec and why, in plain English, no code, no path:line, no review history.
Tools: the fence-files server only.
```

### `amicus/amicus.yaml`, `amicus/commands/amicus.md`, `amicus/amicus.mcp.json` (the amicus, shared)

The amicus block, the one home of the role, included by `write` (node `amicus`), by `mend` (landing design: its node `amicus`, for the mend's cases and the review before landing) and by no other block. Pick: **one shared included block, as `screen` is**, and not a copy of the role in `write/commands/` and `mend/commands/`: a role file resolves only from its own workflow's `commands/` (contracts A6), and the block states the role and its fence once (D-61). The block holds the agent and nothing else: the owner's wait stays in the host's loop body, its sole terminal sink, so the block has no `wait:`. Replaces nothing.

```yaml
name: amicus
description: >-
  Gauntlet amicus, included by write and mend only. Not for direct use.
provider: claude
model: claude-opus-5-5
inputs:
  slug: { description: The item file's slug. }
  case: { description: "The case: red, contest, blocked, commit-failed, idle (writing), unsound or review (the mend)." }
  files: { description: The case's files, newline-separated tree paths. }
  record: { description: The tree path of the record file to write, rewritten each turn. }
  words: { default: "", description: "The owner's words from the last answer, $LOOP_PREV.<wait>.output.text, or \"\"." }
returns: explain
nodes:
  - id: explain
    command: amicus
    context: fresh
    allowed_tools: []
    mcp: amicus.mcp.json
    prompt: <slug $INPUTS.slug; case $INPUTS.case; files $INPUTS.files; record $INPUTS.record; the owner's words $INPUTS.words>
    output_format: { type: object, properties: { record: { type: string } }, required: [record] }
```

```markdown
amicus.md
Inputs: the case and its files (the run, blocks, seal and leftover files, or the mend's, or the review before landing's file),
the record file to write, the owner's last words (may be ""), the item file, the plan files, every direction.
You brief the owner and rule on nothing; the owner is the bench. No agent reads your explanation before the owner does.
1. Work out why the run failed (case review: what the review found); read the code, the tests and the files as needed.
2. Explain it to the owner in plain words, short, no code and no path:line. If you cannot state the problem so that it holds
   together, say so; do not guess past the evidence.
3. Discuss the way forward: answer the owner's last words, and say what each choice at the bench would do.
Write the record file with the explanation as it now stands, over the earlier turn's. Write nothing else.
Tools: the fence-files server only.
```

`amicus.mcp.json` names one server, `fence-files`, launched as the intake design's section `intake/clerk.mcp.json` gives: `FENCE_READ=.`, `FENCE_WRITE=gauntlet/write/*.amicus.*.md:gauntlet/mend/*.amicus.*.md`, `FENCE_DENY` and `FENCE_ONCE` unset, `FENCE_COMMIT` unset. Fixtures: `amicus/fixtures/explain.stubs.yaml`.

### `write-tests/write-tests.yaml`, `write-tests/commands/test-writer.md`, `write-tests/test-writer.mcp.json`

One test block, fanned out by writing. Replaces nothing.

```yaml
name: write-tests
description: >-
  Gauntlet test writing, one block, included by write only. Not for direct use.
provider: claude
model: claude-opus-5-5
inputs:
  block: { description: One block, JSON. }
  specs: { description: The spec files, newline-separated. }
returns: done
nodes:
  - id: clean                          # no writer session over edits another block left
    bash: <git status --porcelain in the tree's root; each changed or untracked path outside the paths of $INPUTS_BLOCK:
          print { "outcome": "blocked", "commit": "", "grounds": those paths, newline-separated }; none: print
          { "outcome": "clean", "commit": "", "grounds": "" }; exit 0>
    output_format: <object: outcome (enum clean, blocked), commit, grounds; required>

  - id: write
    depends_on: [clean]
    when: "$clean.output.outcome == 'clean'"
    command: test-writer
    context: fresh
    allowed_tools: []
    mcp: test-writer.mcp.json
    prompt: <block $INPUTS.block; spec files $INPUTS.specs>
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [committed, contest, commit-failed] }
        commit: { type: string }       # full hash; "" unless committed, and "" when the commit tool found nothing changed
        grounds: { type: string }      # contest: what in the spec cannot be tested as written; commit-failed: the commit tool's output
      required: [outcome, commit, grounds]

  - id: done                           # the block's result: write's, or clean's when write did not run
    depends_on: [clean, write]
    trigger_rule: none_failed_min_one_success
    runtime: bun
    script: <inline: print INPUTS_WRITE, or INPUTS_CLEAN when INPUTS_WRITE is "">
    with: { clean: $clean.output, write: { from: $write.output, if_skipped: "" } }
    output_format: <write's, with outcome enum committed, contest, commit-failed, blocked>
```

A failed `write` skips `done`, so the fan-out records the block as `archon_failed`.

```markdown
Inputs: one block (its specs, paths and ruling) and the spec files. Work from the approved spec only.
Write a test for each spec of the block, in the block's paths, as docs/testing.md rules.
Run the tests through fence-checks; the output names tests and pass or fail only.
Free to do: repair a mechanical mistake that changes no testing contract or behavior; move tests to meet a
file size limit.
A change to a test's contract: only to match the block's ruling or a spec file. Any other request to change a test
is refused.
A spec that cannot be tested as written: stop, outcome contest, grounds.
Done: commit through the commit tool, with a message of your own and the block's paths. The tool's "nothing" (no
path changed): outcome committed, commit "". A failed commit: stop, outcome commit-failed, the tool's output as
grounds. Never retry it.
Tools: fence-files, fence-checks.
```

`test-writer.mcp.json` has two servers, each received as the intake design's section `intake/clerk.mcp.json` gives, with no `sh -c` line building a value. The test command and timeout come from `gauntlet/settings.json` (above).

| Server | Settings |
|---|---|
| `fence-files` | `FENCE_READ=tests:gauntlet/specs/approved:docs/testing.md:@base`; `FENCE_WRITE=tests:@base`; `FENCE_COMMIT=1` |
| `fence-checks` | no `FENCE_*`: runs the brief command with the timeout from `gauntlet/settings.json` |

Fixtures: `write-tests/fixtures/committed.stubs.yaml`, `write-tests/fixtures/contest.stubs.yaml`, `write-tests/fixtures/blocked.stubs.yaml`.

### `write-code/write-code.yaml`, `write-code/commands/coder.md`, `write-code/coder.mcp.json`

One code block, fanned out by writing. The YAML is `write-tests.yaml`'s with `name: write-code`, the description naming code writing, input `plans` (the plan files) in place of `specs`, command `coder` and `mcp: coder.mcp.json`. Its `grounds` for a contest holds why the coder believes a test or its spec is wrong. Replaces nothing.

```markdown
Inputs: one block (its plan steps, paths and ruling) and the plan files. Work from the approved plan only.
Write the code for the block's steps, changing only the block's paths. Run the repository's tests through
fence-checks as often as the work needs.
A test you believe wrong, or a step that needs a path outside the block: stop, outcome contest, grounds.
Never ask for a test to be changed any other way.
Done: commit through the commit tool, with a message of your own and the block's paths. The tool's "nothing" (no
path changed): outcome committed, commit "". A failed commit: stop, outcome commit-failed, the tool's output as
grounds. Never retry it.
Tools: fence-files, fence-checks.
```

| Server | Settings |
|---|---|
| `fence-files` | `FENCE_READ=.`; `FENCE_WRITE=.`; `FENCE_DENY=tests:gauntlet`; `FENCE_HIDE=tests:gauntlet/items:gauntlet/specs:gauntlet/baseline:gauntlet/revisions:gauntlet/write`; `FENCE_COMMIT=1` |
| `fence-checks` | `FENCE_CUT=1`: runs the brief command with the timeout from `gauntlet/settings.json`, each returned line cut at its first ` - `; the coder sees test ids, never a message or a traceback |

Fixtures: `write-code/fixtures/committed.stubs.yaml`, `write-code/fixtures/contest.stubs.yaml`, `write-code/fixtures/blocked.stubs.yaml`.

### Writing's fences: `write/divvyer.mcp.json`, `reviser.mcp.json`, `reviewer-plan.mcp.json`, `reviewer-spec.mcp.json`, `reporter.mcp.json`

One server each, `fence-files`, launched as the intake design's section `intake/clerk.mcp.json` gives. `FENCE_COPY` and `FENCE_COMMIT` stay unset. No agent reaches `approved/` for writes.

| File | `FENCE_READ` | `FENCE_WRITE` | `FENCE_DENY` | `FENCE_ONCE` |
|---|---|---|---|---|
| `divvyer.mcp.json` | `.` | unset | unset | unset |
| `reviser.mcp.json` | `.` | `gauntlet/revisions/*.txt` | `gauntlet/revisions/*.review.*.txt:gauntlet/revisions/*.ruling.*.txt` | unset |
| `reviewer-plan.mcp.json` | `.` | `gauntlet/revisions/*.review.*.txt` | unset | `gauntlet/revisions/*.review.*.txt` |
| `reviewer-spec.mcp.json` | `tests:gauntlet/items:gauntlet/plans/approved:gauntlet/specs/approved:gauntlet/revisions/*.txt:gauntlet/write/*.direction.*.md:docs/testing.md` | `gauntlet/revisions/*.review.*.txt` | unset | `gauntlet/revisions/*.review.*.txt` |
| `reporter.mcp.json` | `gauntlet/revisions/*.txt:gauntlet/plans/approved:gauntlet/specs/approved` | `gauntlet/revisions/*-summary.*.md` | unset | `gauntlet/revisions/*-summary.*.md` |

### `write/write.yaml` (the block's nodes)

The signature, `brief` included, is `gauntlet-design.md`'s. The nodes `enter` and `handoff` are that design's, with `enter` placed in the loop. Every agent node starts a fresh session.

```yaml
inputs:
  # slug, items, plan, spec, brief, stage: as gauntlet-design.md gives them

nodes:
  - id: open
    runtime: uv
    script: stage
    with: { mode: open }

  - id: work
    depends_on: [open]
    loop_group:
      max_iterations: <CAP>               # the bound CAP, runtime-model-design.md, "Loop shape and bounds"
      until_bash: 'end=$docket.output.end; [ -n "$end" ]'
      nodes:
        - id: record                   # runs every iteration, so state always has a dependency that succeeded
          runtime: uv
          script: stage
          with: { mode: record, start: $open.output.start,
                  round: $LOOP_PREV.docket.output.round, case: $LOOP_PREV.docket.output.case,
                  decision: $LOOP_PREV.bench.output.decision,
                  text: $LOOP_PREV.bench.output.text }          # the string form: a `from:` directive cannot read $LOOP_PREV (loop-nodes.md:812-816); "" on iteration 1 and after a skipped bench

        - id: enter                    # gauntlet-design.md's node, run off the approve ruling on file (`record`'s enter), as plan and spec review's `enter` runs off `close`
          depends_on: [record]
          when: "$record.output.enter != ''"
          bash: <as gauntlet-design.md gives it, for the round file $record.output.enter; its "Revises:" line names plans or specs>

        - id: state
          depends_on: [record, enter]
          trigger_rule: none_failed_min_one_success   # a failed enter fails the iteration; a resume re-drives it
          runtime: uv
          script: stage
          with: { mode: state, start: $open.output.start }

        - id: divvy
          depends_on: [state]
          when: "$state.output.next == 'divvy'"
          command: divvyer
          context: fresh
          allowed_tools: []
          mcp: divvyer.mcp.json
          prompt: <cause $state.output.cause; stage $INPUTS.stage; problems $state.output.problems; plan files $state.output.plans; spec files $state.output.specs>
          output_format: <object: waves, an array of { kind (enum tests, code), blocks: array of { id, specs, steps, paths } }; required>

        - id: cut
          depends_on: [divvy]
          runtime: uv
          script: stage
          with: { mode: cut, move: $state.output.move, divvy: $divvy.output, cause: $state.output.cause }

        - id: tests
          depends_on: [state]
          when: "$state.output.next == 'tests'"
          include: write-tests
          with: { specs: $state.output.specs }
          fan_out: { items: $state.output.wave, as: block, max_parallel: 1 }

        - id: code
          depends_on: [state]
          when: "$state.output.next == 'code'"
          include: write-code
          with: { plans: $state.output.plans }
          fan_out: { items: $state.output.wave, as: block, max_parallel: 1 }

        - id: result
          depends_on: [tests, code]
          trigger_rule: none_failed_min_one_success
          runtime: uv
          script: stage
          with: { mode: result, move: $state.output.move,
                  tests: { from: $tests.output, if_skipped: "" }, code: { from: $code.output, if_skipped: "" } }

        - id: test                     # the repository's brief command, once per finished cut
          depends_on: [state]
          when: "$state.output.next == 'test'"
          bash: <read "brief" and "timeout" from gauntlet/settings.json in the tree's root, run timeout -k 10 <timeout>
                nice -n 10 bash -c <brief> < /dev/null there, in the foreground, as node baseline does; write gauntlet/write/<slug>.run.$state.output.move.txt:
                "exit=<n> timed_out=<true|false>", then the whole output; exit 0>

        - id: seal                     # the mechanical final commit
          depends_on: [state]
          when: "$state.output.next == 'seal'"
          bash: <the seal of runtime-model-design.md, "Commit model", on the tree's root: a clean tree writes gauntlet/write/<slug>.seal.$state.output.move.txt
                "exit=0", "nothing"; else the final commit, whose body holds gauntlet/plans/approved/<slug>-summary.md when plan is not ""
                and each summary file of $state.output.approved (the revision rounds the owner approved) in order; write the file:
                "exit=<n>", then the output; exit 0>

        - id: revise
          depends_on: [state]
          when: "$state.output.next == 'revise'"
          command: reviser
          context: fresh
          allowed_tools: []
          mcp: reviser.mcp.json
          prompt: <round $state.output.round; kind $state.output.kind; cause $state.output.cause; plan files; spec files>

        - id: screen
          depends_on: [state]
          when: "$state.output.next == 'review'"
          include: screen
          with: { file: $state.output.file }

        - id: flag
          depends_on: [screen]
          when: "$screen.output.steering == true"
          runtime: uv
          script: ledger
          with: { mode: screen, round: $state.output.round, quote: $screen.output.quote }

        - id: review-plan
          depends_on: [screen]
          when: "$screen.output.steering == false && $state.output.kind == 'plan'"
          command: reviewer
          context: fresh
          allowed_tools: []
          mcp: reviewer-plan.mcp.json
          prompt: <round $state.output.round; plan files; spec files>

        - id: review-spec              # as review-plan, for kind spec, mcp reviewer-spec.mcp.json

        - id: case
          depends_on: [state, cut, result, test, seal, revise, flag, review-plan, review-spec]
          trigger_rule: none_failed_min_one_success
          runtime: uv
          script: stage
          with: { mode: docket, start: $open.output.start, base: $open.output.base }

        - id: report
          depends_on: [case]
          when: "$case.output.summary == true"
          command: reporter
          context: fresh
          allowed_tools: []
          mcp: reporter.mcp.json
          prompt: <round file gauntlet/revisions/<slug>.<round>.txt; summary file gauntlet/revisions/<slug>-summary.<round>.md;
                  slug $INPUTS.slug, round $case.output.round>

        - id: amicus                   # the shared amicus block (Terms), only for an amicus case, ahead of bench
          depends_on: [case]
          when: "$case.output.amicus == true"
          include: amicus
          with: { slug: $INPUTS.slug, case: $case.output.name, files: $case.output.files,
                  record: $case.output.record,
                  words: $LOOP_PREV.bench.output.text }

        - id: docket
          depends_on: [case, report, amicus]
          trigger_rule: none_failed_min_one_success
          runtime: uv
          script: stage
          with: { mode: docket, start: $open.output.start, base: $open.output.base }

        - id: bench                    # the owner; sole terminal sink of the body
          depends_on: [docket]
          when: "$docket.output.ask == true"
          wait:
            form: select
            attention: "$docket.output.attention"
            options: "$docket.output.options"

  - id: handoff                        # gauntlet-design.md's output_format
    depends_on: [work]
    runtime: uv
    script: stage
    with: { mode: close }
```

`<slug>`, plan files and spec files in prompts come from `$INPUTS.slug` and `$state.output`. A script reads block inputs as `INPUTS_<NAME>` and binds none in its `with:`, `$INPUTS.<name>` appears in `with:` only on `include:` nodes, and no `when:` reads `$INPUTS`.

Fixtures, `write/fixtures/<route>.stubs.yaml`, one per route: tests then code, the run green, sealed (`written`); no spec, code only; a coder's contest, the amicus asking, the owner's `discuss` and then `rework-tests`, fixed, green; a contested block's edits saved as its leftover patch, the tree restored and the block carried; a red run, `rework-code`; a failed commit; a failed seal; `revise-spec`, revision `SOUND`, the owner approves, tests re-cut; the owner revises a `SOUND` revision; `revise-plan`, then a `No change.` spec round closing without the owner; `UNSOUND` then `SOUND`; a revision `SCREENED`; a rejected cut re-divvied; an iteration that writes no file, the amicus asking (case `idle`) and its answer a direction, the hearing going on; `back-to-planning` (`planning`, the direction and the amicus record handed off); a block whose commit holds a path outside its `paths`, marked in the blocks file; a second stage starting above the first stage's records; a clean tree at `seal` making no final commit; a dirty tree at `seal` making `<slug>: final`; the unrun waves of a replaced cut carried into the next.

### `screen/screener.mcp.json`, `screen/screen.yaml` (revision rounds)

`FENCE_READ` adds `gauntlet/revisions/*.txt`. Input `file`'s description adds `gauntlet/revisions/<slug>.N.txt`. The spec review design is otherwise unchanged.

### The repository's `.archon/config.yaml` (writing)

```yaml
env:
  GAUNTLET_TEST_BRIEF_COMMAND: "<the whole test command, printing one line per test: PASSED <id>, FAILED <id> or ERROR <id>, and no test source; for pytest, the command with --tb=no -rA -q>"
  GAUNTLET_TEST_BASE: "<colon-separated root paths the test writer may read and write besides tests/, such as pyproject.toml>"
  GAUNTLET_FINAL_SUBJECT: "<line 1 of the final commit, <slug> standing for the slug, such as \"feat(<slug>): final\"; optional>"
```

`GAUNTLET_TEST_TIMEOUT` is the cut design's. Writing needs only `GAUNTLET_TEST_BRIEF_COMMAND` to be set, which `gauntlet-run`'s bash node `env-check` checks at run start; `GAUNTLET_TEST_BASE` is optional, none when unset; `GAUNTLET_FINAL_SUBJECT` is optional; its use is `runtime-model-design.md`'s, "Commit model". The brief baseline, `gauntlet/baseline/<slug>.brief.txt`, is written by the cut design's node `baseline`.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| What is owed next, cuts, wave records, writing's owner cases, the run's end | `write/scripts/stage.py` | any of it computed in a node, prompt or role; a `when:` deciding more than which node runs for `next` |
| The revision hearing's rounds, verdicts and owner cases | `runtime-model-design.md`, headings "Hearing state" and "Ledger", through `write/scripts/ledger.py`'s `PROFILE` | `stage.py` or a node computing a round, slot or count |
| Cutting work into blocks and waves; what runs in one fan-out | the divvyer's output, checked by `stage.py cut` | blocks of one wave sharing a path; a block named by any other role or node |
| Running the blocks of a wave | `include:` with `fan_out:` of `write-tests` or `write-code`, `max_parallel: 1`, each block opening on node `clean` | a `wait:` in either block; a `workflow:` child per block |
| Briefing the owner on a red, a contest, a blocked block, a failed commit or an idle iteration | the shared `amicus` block (Terms, "Amicus"), included as node `amicus` of `work` ahead of `bench`; the owner's choice at `bench` | a writer, node, script or agent ruling who is wrong or whether a case warrants a stop; an agent checking, filtering or rewriting the amicus's explanation; a writer retrying a failed commit |
| The direction and how the next pass reads it | `stage.py record` writes `gauntlet/write/<slug>.direction.N.md` (Terms, "Direction"); `stage.py state` and `close` read its `Rework:` line; the divvyer and the reviser read its text | an agent writing, editing or removing a direction; a verdict file; a part reworked that the direction does not name |
| The paths mark | `stage.py result`, the `outside` list of each committed block in `<slug>.blocks.N.json` | any other comparison of a block's diff against its `paths`; a mark that stops the run |
| A stage's writing | `stage.py` over the records above `start`, the plan steps of stage `stage`, a final commit of its own | a cut across two stages; a stage reading an earlier stage's records as its state |
| A wrong spec or plan | a revision round in `gauntlet/revisions/`, tried by the reviewer, approved at `bench`, entered by `enter` | any other edit of the approved files; the reviser revising past the quoted clause or the affected specs |
| Ending the block for planning | the owner's `back-to-planning` direction, read by `stage.py close`, which hands off `planning`, the direction and the amicus record | a size or line-count threshold; any other node ending writing; an agent choosing to end it |
| Commits | `runtime-model-design.md`, heading "Commit model"; the tool is `commit` of `fence/files.py`, the final commit node `seal` | a writer's Bash; any other `git add` or `git commit` in a Gauntlet file; `--no-verify` |
| A block's uncommitted changes | `runtime-model-design.md`, heading "Commit model"; done by `stage.py result` | any other restore, clean or reset in a Gauntlet file; a restore in the checkout; a restore before the patch is written |
| Test output a writer sees | `fence/checks.py` running the brief command from `gauntlet/settings.json`, for the test writer, the coder and both menders, the coder's and `mend-code`'s lines cut at their first ` - ` (the coder-fence cut mode) | a writer running any other test command; a tool returning a traceback, a message past ` - ` or hook output to a coder |
| The per-test listing and red | The brief command's `PASSED`, `FAILED` and `ERROR` lines, read by `.shared/red.py` (`gauntlet-design.md`), which `stage.py red` calls | parsing a runner's full output; a comparison computed in `stage.py`, a node, prompt or role |
| What a test writer can see | `write-tests/test-writer.mcp.json`: `tests/`, the approved spec, `docs/testing.md`, the test base (`@base`) | a test writer handed the plan, code or a CODE section |
| What a coder can see | `write-code/coder.mcp.json`'s `FENCE_HIDE`; the block's ruling text | a coder handed the item file, the spec, a test file or a direction file |
| Writers' tools | the fence-files and fence-checks servers | `Bash`, `Agent` or any built-in tool on a writer node |
| Writing's roles | `write/commands/`, `write-tests/commands/`, `write-code/commands/`; the amicus in `amicus/commands/` | role rules restated in prompts; a role file of another phase |

## Order

1. Commits and settings in the fence: `fence/files.py` (`commit`, `FENCE_COMMIT`, `@base`), `fence/checks.py` (settings, `FENCE_CUT`), `fence/test_files_commit.py`, `fence/test_settings.py`. Needs `gauntlet-design.md`'s steps 5 and 6. Agent: `builder`.
2. Writing's ledger: `write/scripts/ledger.py`, `write/tests/test_ledger.py`. Needs the spec review design's step 1. Agent: `builder`.
3. Writing's stage: `write/scripts/stage.py`, `write/tests/test_stage.py`. Needs step 2, `gauntlet-design.md`'s step 6 and the plan review design's step 2 (`marks`). Agent: `builder`.
4. Roles: `write/commands/divvyer.md`, `write/commands/reviser.md`, `write/commands/reviewer.md`, `write/commands/reporter.md`, `amicus/commands/amicus.md`, `write-tests/commands/test-writer.md`, `write-code/commands/coder.md`. Agent: `role-author`.
5. Screen reads revisions and the amicus block: `screen/screener.mcp.json`, `screen/screen.yaml`, `amicus/amicus.yaml`, `amicus/amicus.mcp.json`, `amicus/fixtures/explain.stubs.yaml`. Needs the spec review design's step 5 and this design's step 4. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
6. Writer blocks: `write-tests/write-tests.yaml`, `write-tests/test-writer.mcp.json`, `write-tests/fixtures/committed.stubs.yaml`, `write-tests/fixtures/contest.stubs.yaml`, `write-tests/fixtures/blocked.stubs.yaml`, `write-code/write-code.yaml`, `write-code/coder.mcp.json`, `write-code/fixtures/committed.stubs.yaml`, `write-code/fixtures/contest.stubs.yaml`, `write-code/fixtures/blocked.stubs.yaml`. Needs steps 1 and 4. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
7. Writing block: `write/write.yaml`, `write/divvyer.mcp.json`, `write/reviser.mcp.json`, `write/reviewer-plan.mcp.json`, `write/reviewer-spec.mcp.json`, `write/reporter.mcp.json`, `write/fixtures/*.stubs.yaml`. Needs steps 3 to 6. If Archon rejects `include:` with `fan_out:` inside a `loop_group` body, the builder stops and reports the gap. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
