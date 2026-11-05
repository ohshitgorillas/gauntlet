Status: proposed.

# Gauntlet writing

## Why

Writing is phase 5, block `write` of the tree run `gauntlet-tree`, after the baseline (`gauntlet-design.md`). That design gives the block's signature, its nodes `enter` and `handoff`, the approved revisions and the run's end on `defective`; this file gives the rest of the block and nothing it restates. Every path is in the tree unless it names the pack root.

Inside one loop, the divvyer cuts the approved plan and spec into blocks and orders them in waves. Test writers write the tests from the approved spec, then coders write the code from the approved plan. A juror rules on every red: a block's contest, a failed commit, a red test run or a failed final commit. A wrong spec or plan is revised in the same loop, tried by a fresh reviewer and approved by the owner at `bench`. A defective plan ends the run.

What the tree holds for the concerns writing touches:

- Running a test command for an agent: one copy, `fence/checks.py`, which runs `FENCE_TEST_COMMAND` and returns its last 200 lines, tracebacks included. Writing reuses it unchanged, set per role. The test writer's copy runs the repository's brief command, which prints no test source.
- Baseline comparison: no copy. The cut design's `gauntlet/baseline/<slug>.txt` holds the whole test output, unparsed, with no per-test listing.
- Commits: no copy. No Gauntlet file commits, and `fence/files.py` has no git tool.
- Round logic: designed and unbuilt, `.shared/rounds.py` (spec review design). Writing's revision hearing uses it through a `write/scripts/ledger.py` `Profile`, as `gauntlet-design.md` requires.
- Steering screening: designed and unbuilt, the `screen` workflow (spec review design). Its fence, `screen/screener.mcp.json`, reads only `gauntlet/plans/*.txt` and `gauntlet/specs/*.txt`, so it cannot read a revision round.
- Hidden reads: designed and unbuilt, `FENCE_HIDE` in `fence/files.py` (`gauntlet-design.md`). The coder's blindness to `tests/` rests on it.
- Roles: no copy usable here. `gauntlet-design.md` gives writing its own `write/commands/`.
- Parallel writers: Archon runs `include:` with `fan_out:` inside the run, but rejects a `wait:` anywhere in the fanned-out block. The only wait is `bench`, in writing's loop.

Unmeasured: whether the repository's `.archon/config.yaml` `env:` reaches an agent node's MCP server processes. Measured only for bash nodes (cut design).

## Terms

- **Block**: one writer's share of the work: `{ id, kind, specs, steps, paths, ruling }`, `kind` is `tests` or `code`. `specs` lists spec ids, `steps` lists plan steps, `paths` lists every file the block may change. `ruling` holds the juror's `To the writers:` text when the cut answers a verdict, and `""` otherwise.
- **Wave**: blocks of one kind that share no path and run at once, at most 2 at a time.
- **Cut**: the divvyer's waves for one cause, test waves first. The first cut covers the whole plan and spec. A later cut covers only what its cause affects. The cause is a juror verdict `TESTS` or `CODE`, or an approved revision.
- **Move** `N`: one file `gauntlet/write/<slug>.<kind>.N.<ext>`, with one counter over every kind. Each loop iteration makes at most one move.
- **Red**: the latest test run timed out, or names a failing test (`FAILED` or `ERROR`) that the brief baseline does not name as failing. A run that exits non-zero with no failing line is also red when the brief baseline exited 0. A baseline failure that now passes is not red.
- **Revision round** `N`: one file `gauntlet/revisions/<slug>.N.txt`, with its review, ruling and summary, under `.shared/rounds.py`. Line 1 is `Revises: plan` or `Revises: spec`. Line 2 is `Answers: <tree path>`, naming the verdict, or the entered plan revision it follows. The clauses it changes come after, each as it now reads. A spec revision that follows a plan revision and changes nothing holds `No change.` after the two lines.
- **Plan files**, **spec files**: `approved/<slug>.txt`, then each `approved/<slug>.rev<N>.txt` in order of N. An agent that needs the plan or the spec is handed these.

Juror verdicts, first line of `<slug>.verdict.N.txt`, `Verdict: <verdict>`:

| Verdict | Next |
|---|---|
| `TESTS` | a cut of test blocks for the tests the verdict names |
| `CODE` | a cut of code blocks for the code the verdict names |
| `SPEC` | a spec revision of the quoted clause, then a cut of the affected tests |
| `PLAN` | a plan revision of the quoted clause; with a spec, a spec revision of the affected specs; then a cut of the affected tests and code |
| `DEFECTIVE` | the loop ends; writing hands off `defective` and the verdict's path |

A change too large for a revision gets `DEFECTIVE`.

Files in `gauntlet/write/`:

| File | Writer | Rule |
|---|---|---|
| `<slug>.cut.N.json` | `stage.py cut` | the divvyer's waves and their cause; a rejected cut holds its problems and no waves |
| `<slug>.blocks.N.json` | `stage.py result` | one wave's block outcomes, in block order |
| `<slug>.run.N.txt` | node `test` | `exit=<n> timed_out=<true\|false>`, then the brief command's output |
| `<slug>.seal.N.txt` | node `seal` | `exit=<n>`, then git's and the hooks' output; `nothing` when the tree had no change |
| `<slug>.verdict.N.txt` | juror | once |
| `<slug>.ruling.N.txt` | `stage.py record` | the owner's reply to a `stalled` or `cap` case, verbatim; once |

Files in `gauntlet/revisions/`: `<slug>.N.txt` (reviser), `<slug>.review.N.txt` (reviewer, or `ledger.py screen` for `SCREENED`), `<slug>.ruling.N.txt` (`stage.py record`), `<slug>-summary.N.md` (reporter), each as `.shared/rounds.py` rules them.

## Modules

### `fence/files.py` (commit)

Adds the tool `commit`, registered only when `FENCE_COMMIT=1`. The writer pens the message and commits its own block. Replaces nothing.

```python
# FENCE_COMMIT=1: commit is registered; unset: absent.
# Every path this server process wrote, edited, copied or deleted is recorded.
def commit(message: str, paths: list[str]) -> str: ...
# Under an exclusive flock on <git rev-parse --git-dir>/gauntlet-commit.lock, held across both commands:
#   git add -A -- <paths>, then git commit --only -m <message> -- <paths>; hooks run, never --no-verify.
# PermissionError, nothing staged: a path outside FENCE_WRITE or inside FENCE_DENY or FENCE_HIDE;
#   a recorded path missing from paths; message blank.
# Returns "exit=<n>", then git's and the hooks' output cut as checks.py cuts it; exit 0 adds "commit=<full hash>".
```

Suite: `fence/test_files_commit.py`, run as `docs/testing.md` states with the folder `fence`, against a real git repository under `tmp_path`. It pins a commit holding exactly `paths` while another path is staged, the refusal of a recorded path left out of `paths`, a failing `pre-commit` hook giving a non-zero `exit` and no commit, and the tool's absence without `FENCE_COMMIT`.

### `write/scripts/ledger.py`

Writing's revision-hearing `Profile` on `.shared/rounds.py`. It defines `PROFILE` and calls `main(PROFILE)` under `if __name__ == "__main__"`, so `stage.py` imports `PROFILE`. Header and import lines are those of the planning ledger. Replaces nothing.

```python
PROFILE = Profile(
    folder="gauntlet/revisions", author="reviser", reviewer="reviewer", letter="r",
    verdicts=("SOUND", "UNSOUND", "APPROACH THE BENCH", "OBJECTION: LEADING", "OBJECTION: NON-RESPONSIVE", "SCREENED"),
    retire="OBJECTION: LEADING", non_responsive="OBJECTION: NON-RESPONSIVE",
    attempts=("UNSOUND", "APPROACH THE BENCH"),
    owner_cases=(
        OwnerCase("SOUND", "review", (("approve", "Approve"), ("revise", "Revise")), summary=True, ends="approve"),
        OwnerCase("APPROACH THE BENCH", "bench", (("reply", "Reply"),), summary=False, ends=""),
    ),
    filed=lambda text: True,
)
```

Suite: `write/tests/test_ledger.py`. It pins `UNSOUND` counted as an attempt, `SOUND` opening case `review`, and slot names `r1` to `r12`.

### `write/scripts/stage.py`

Writing's progress: what is owed next, the cut and wave records, red, the owner's cases outside the hearing, and the run's end. It derives everything from `gauntlet/write/`, `gauntlet/revisions/` and `approved/`, so a resumed run reads the same state. It takes the hearing's state, docket, screen and record from `.shared/rounds.py` with `PROFILE`, and computes none of them itself. Standard library only. Replaces nothing.

```python
# /// script
# requires-python = ">=3.12"
# ///
# Env: INPUTS_MODE, INPUTS_SLUG, INPUTS_PLAN, INPUTS_SPEC, INPUTS_BRIEF (block inputs); INPUTS_START in the loop;
#   per mode below. GAUNTLET_TEST_COMMAND or GAUNTLET_TEST_BRIEF_COMMAND blank: every mode exits 1 naming it.

def open_() -> dict: ...          # mode "open", before the loop: { "start": highest move, 0 when none }

def state(start: int) -> dict: ...
# { "next": "divvy" | "tests" | "code" | "test" | "seal" | "juror" | "revise" | "review" | "vacant" | "none",
#   "move": int,                  # the next move's N
#   "wave": [block],              # tests and code: the latest cut's first unrun wave, ruling filled from its cause
#   "kind": "plan" | "spec" | "", # revise and review
#   "round": int,                 # revise and review: rounds.state's round
#   "cause": str,                 # divvy: the tree path the cut answers; juror: the case's files, newline-separated
#   "problems": str,              # divvy: the latest rejected cut's problems, "" when none
#   "plans": str, "specs": str }  # plan files and spec files, newline-separated absolute paths; "" for a "" input
# First that holds:
#   latest verdict DEFECTIVE, or latest seal exit 0 or nothing: none.
#   a revision owed: latest verdict SPEC or PLAN not yet answered by an approved round; an entered plan revision,
#     spec not "", and no spec round answering it closed. A round is closed by an approve ruling, or a SOUND
#     review of a "No change." round. next from rounds.state: reviser owes: revise; slot r1..r12: review;
#     vacant: vacant.
#   a case for the juror: the latest blocks file holds a contest or commit-failed; the latest run is red; the
#     latest seal exit is not 0; a writing ruling newer than the latest verdict.
#   no cut since the latest cause, or the latest cut rejected: divvy. The cause is the latest verdict TESTS or
#     CODE, or the latest closed round; no verdict and no round: the approved files.
#   the latest cut has an unrun wave: its kind.
#   no run since the latest wave: test.
#   no seal since the latest run: seal.

def cut(move: int, divvy: str, cause: str) -> dict: ...
# Writes <slug>.cut.<move>.json: { "cause", "waves", "problems" }. Problems, each one line: an empty wave; a code
#   wave before a test wave; a path in two blocks of one wave; a tests block path outside tests/ and
#   GAUNTLET_TEST_BASE; a code block path inside tests/ or gauntlet/; a block id repeated; a step of an
#   uncommitted earlier block missing from a code cut. Any problem: "waves" is []. stdout { "problems" }.

def result(move: int, tests: str, code: str) -> dict: ...
# Writes <slug>.blocks.<move>.json from the wave's ordered outcomes, the one of tests and code not ""; an { "archon_failed": true } item is
#   recorded as commit-failed with its error. stdout { "contested": bool }.

def red(run: str, brief: str) -> bool: ...
# One line per test, "PASSED <id>", "FAILED <id>" or "ERROR <id>", text from " - " on dropped; other lines ignored.

def docket(start: int) -> dict: ...
# { "case": <rounds.docket case> | "stalled" | "cap" | "none", "ask": bool, "attention": str,
#   "options": [ { "id", "label" } ], "round": int, "summary": bool, "end": "written" | "defective" | "" }
#   First that holds: rounds.docket's case when not none, except a SOUND review of a "No change." round;
#   stalled (verdicts and rejected cuts since the latest writing ruling >= 5); cap (moves since start >=
#   rounds.CAP); none. stalled and cap offer one option, reply. end follows the first rule of state.

def record(move: int, round: int, case: str, decision: str, text: str) -> dict: ...
# Hearing cases: rounds.record. stalled and cap: writes <slug>.ruling.<move>.txt. stdout { "enter": tree path of
#   the round file when decision approves a review case, else "" }.

def close() -> dict: ...
# { "outcome": "written" | "defective", "verdict": absolute path of the DEFECTIVE verdict, "" when written }

def main() -> int: ...             # dispatches on INPUTS_MODE, prints JSON to stdout
```

Suite: `write/tests/test_stage.py`, run as `docs/testing.md` states with the folder `write/tests`. It drives `main` through real files under `tmp_path`. It pins each rule of `state` in its precedence, red against a baseline failure that now passes and against a new failure, each cut problem, and `close` on `DEFECTIVE`.

### Roles: `write/commands/divvyer.md`, `juror.md`, `reviser.md`, `reviewer.md`, `reporter.md`

Each starts a fresh session, primed from files. Replace nothing.

```markdown
divvyer.md
Inputs: the cause, the problems of the latest rejected cut, the plan files, the spec files, every earlier cut and
blocks file, every writing ruling.
Output the waves: test waves before code waves; one block per related set of specs or plan steps; blocks of one
wave share no path; a block that needs another's files sits in a later wave. A cause other than the approved files:
only the tests and code it affects. Test block paths sit in tests/ or the repository's test base files; code block
paths sit outside tests/ and gauntlet/. Writes nothing.
Tools: the fence-files server only.
```

```markdown
juror.md
Inputs: move N and the case's files; read the task, the plan files, the spec files, every verdict, every writing
ruling and the code and tests the case touches. The owner's words in rulings bind the verdict.
Write gauntlet/write/<slug>.verdict.N.txt once. Line 1 "Verdict: <TESTS|CODE|SPEC|PLAN|DEFECTIVE>". SPEC and
PLAN: a line "Clause:" quoting the one clause wrong, verbatim. TESTS and CODE: a section "To the writers:"
naming what each writer must change. A CODE section names failing tests and plan clauses, and quotes no spec
text or test source. Then "Grounds:".
TESTS: a test departs from its approved spec. CODE: the code fails the plan or a test that matches its spec.
SPEC or PLAN: the clause itself is wrong and a revision of it fixes it. DEFECTIVE: the plan cannot stand, or the
change needed is too large for a revision. A failed commit is ruled like any red, on the file that fails the hook.
Tools: the fence-files server only.
```

```markdown
reviser.md
Inputs: round N, kind (plan or spec), the tree path the round answers, the plan files, the spec files, every
revision ruling, the latest review (may be "").
Write gauntlet/revisions/<slug>.N.txt: "Revises: <kind>", "Answers: <path>", then each clause it changes as it
now reads, nothing else. Answering a verdict: only the quoted clause. Following a plan revision: only the specs
it affects, or "No change.". Latest review OBJECTION: LEADING or SCREENED: the previous round with the quoted text
removed, nothing else changed. A spec revision holds no source text, as speccer.md rules a spec block.
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
Input: round N, SOUND. Write gauntlet/revisions/<slug>-summary.N.md once: what the revision changes in the plan or
spec and why, in plain English, no code, no path:line, no review history.
Tools: the fence-files server only.
```

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
returns: write
nodes:
  - id: write
    command: test-writer
    context: fresh
    allowed_tools: []
    mcp: test-writer.mcp.json
    prompt: <block $INPUTS.block; spec files $INPUTS.specs>
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [committed, contest, commit-failed] }
        commit: { type: string }       # full hash, "" unless committed
        grounds: { type: string }      # contest: what in the spec cannot be tested as written; commit-failed: the commit tool's output
      required: [outcome, commit, grounds]
```

```markdown
Inputs: one block (its specs, paths and ruling) and the spec files. Work from the approved spec only.
Write a test for each spec of the block, in the block's paths, as docs/testing.md or the repository's testing
policy rules. Run the tests through fence-checks; the output names tests and pass or fail only.
Free to do: repair a mechanical mistake that changes no testing contract or behavior; move tests to meet a
file size limit.
A change to a test's contract: only to match the block's ruling or a spec file. Any other request to change a test
is refused.
A spec that cannot be tested as written: stop, outcome contest, grounds.
Done: commit through the commit tool, with a message of your own and the block's paths. A failed commit: stop,
outcome commit-failed, the tool's output as grounds. Never retry it.
Tools: fence-files, fence-checks.
```

`test-writer.mcp.json` has two servers. Each is launched by `sh -c`, with every `FENCE_*` built from the repository's `env:` in the launch line. Neither sets `CLAUDE_PROJECT_DIR`.

| Server | Settings |
|---|---|
| `fence-files` | `FENCE_READ=tests:gauntlet/specs/approved` plus `:$GAUNTLET_TEST_BASE` when set; `FENCE_WRITE=tests` plus `:$GAUNTLET_TEST_BASE`; `FENCE_COMMIT=1` |
| `fence-checks` | `FENCE_TEST_COMMAND=$GAUNTLET_TEST_BRIEF_COMMAND`, `FENCE_TEST_TIMEOUT=${GAUNTLET_TEST_TIMEOUT:-900}` |

Fixtures: `write-tests/fixtures/committed.stubs.yaml`, `write-tests/fixtures/contest.stubs.yaml`.

### `write-code/write-code.yaml`, `write-code/commands/coder.md`, `write-code/coder.mcp.json`

One code block, fanned out by writing. The YAML is `write-tests.yaml`'s with `name: write-code`, the description naming code writing, input `plans` (the plan files) in place of `specs`, command `coder` and `mcp: coder.mcp.json`. Its `grounds` for a contest holds why the coder believes a test or its spec is wrong. Replaces nothing.

```markdown
Inputs: one block (its plan steps, paths and ruling) and the plan files. Work from the approved plan only.
Write the code for the block's steps, changing only the block's paths. Run the repository's tests through
fence-checks as often as the work needs.
A test you believe wrong, or a step that needs a path outside the block: stop, outcome contest, grounds.
Never ask for a test to be changed any other way.
Done: commit through the commit tool, with a message of your own and the block's paths. A failed commit: stop,
outcome commit-failed, the tool's output as grounds. Never retry it.
Tools: fence-files, fence-checks.
```

| Server | Settings |
|---|---|
| `fence-files` | `FENCE_READ=.`; `FENCE_WRITE=.`; `FENCE_DENY=tests:gauntlet`; `FENCE_HIDE=tests:gauntlet/tasks:gauntlet/specs:gauntlet/baseline:gauntlet/revisions:gauntlet/write`; `FENCE_COMMIT=1` |
| `fence-checks` | `FENCE_TEST_COMMAND=$GAUNTLET_TEST_COMMAND`, `FENCE_TEST_TIMEOUT=${GAUNTLET_TEST_TIMEOUT:-900}` |

Fixtures: `write-code/fixtures/committed.stubs.yaml`, `write-code/fixtures/contest.stubs.yaml`.

### Writing's fences: `write/divvyer.mcp.json`, `juror.mcp.json`, `reviser.mcp.json`, `reviewer-plan.mcp.json`, `reviewer-spec.mcp.json`, `reporter.mcp.json`

One server each, `fence-files`, launched as the spec review design's fences are. `FENCE_COPY` and `FENCE_COMMIT` stay unset. No agent reaches `approved/` for writes.

| File | `FENCE_READ` | `FENCE_WRITE` | `FENCE_DENY` | `FENCE_ONCE` |
|---|---|---|---|---|
| `divvyer.mcp.json` | `.` | unset | unset | unset |
| `juror.mcp.json` | `.` | `gauntlet/write/*.verdict.*.txt` | unset | `gauntlet/write/*.verdict.*.txt` |
| `reviser.mcp.json` | `.` | `gauntlet/revisions/*.txt` | `gauntlet/revisions/*.review.*.txt:gauntlet/revisions/*.ruling.*.txt` | unset |
| `reviewer-plan.mcp.json` | `.` | `gauntlet/revisions/*.review.*.txt` | unset | `gauntlet/revisions/*.review.*.txt` |
| `reviewer-spec.mcp.json` | `tests:gauntlet/tasks:gauntlet/plans/approved:gauntlet/specs/approved:gauntlet/revisions/*.txt:gauntlet/write/*.verdict.*.txt:docs/testing.md` | `gauntlet/revisions/*.review.*.txt` | unset | `gauntlet/revisions/*.review.*.txt` |
| `reporter.mcp.json` | `gauntlet/revisions/*.txt:gauntlet/plans/approved:gauntlet/specs/approved` | `gauntlet/revisions/*-summary.*.md` | unset | `gauntlet/revisions/*-summary.*.md` |

### `write/write.yaml` (the block's nodes)

The signature is `gauntlet-design.md`'s, plus input `brief`. The nodes `enter` and `handoff` are that design's, with `enter` placed in the loop. Every agent node starts a fresh session.

```yaml
inputs:
  # slug, task, plan, spec, baseline: as gauntlet-design.md gives them
  brief: { description: Absolute tree path of gauntlet/baseline/<slug>.brief.txt. }

nodes:
  - id: open
    runtime: uv
    script: stage
    with: { mode: open }

  - id: work
    depends_on: [open]
    loop_group:
      max_iterations: 200              # rounds.py CAP; from 200 moves every iteration asks, so this never fails the run
      until_bash: 'end=$docket.output.end; [ -n "$end" ]'
      nodes:
        - id: record
          when: "$LOOP_PREV.bench.output.decision != ''"
          runtime: uv
          script: stage
          with: { mode: record, start: $open.output.start, round: $LOOP_PREV.docket.output.round,
                  case: $LOOP_PREV.docket.output.case, decision: $LOOP_PREV.bench.output.decision,
                  text: $LOOP_PREV.bench.output.text }

        - id: enter                    # gauntlet-design.md's node
          depends_on: [record]
          when: "$record.output.enter != ''"
          bash: <as gauntlet-design.md gives it, for the round file $record.output.enter; its "Revises:" line names plans or specs>

        - id: state
          depends_on: [record, enter]
          trigger_rule: all_done
          runtime: uv
          script: stage
          with: { mode: state, start: $open.output.start }

        - id: vacate
          depends_on: [state]
          when: "$state.output.next == 'vacant'"
          cancel: "Twelve OBJECTION: LEADING verdicts passed the screener on revisions in this run; no reviewer is left. The run stops."

        - id: divvy
          depends_on: [state]
          when: "$state.output.next == 'divvy'"
          command: divvyer
          context: fresh
          allowed_tools: []
          mcp: divvyer.mcp.json
          prompt: <cause $state.output.cause; problems $state.output.problems; plan files $state.output.plans; spec files $state.output.specs>
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
          fan_out: { items: $state.output.wave, as: block, max_parallel: 2 }

        - id: code
          depends_on: [state]
          when: "$state.output.next == 'code'"
          include: write-code
          with: { plans: $state.output.plans }
          fan_out: { items: $state.output.wave, as: block, max_parallel: 2 }

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
          timeout: <GAUNTLET_TEST_TIMEOUT plus 60 s, in ms; 960000 when unset>
          bash: <run timeout -k 10 "${GAUNTLET_TEST_TIMEOUT:-900}" nice -n 10 bash -c "$GAUNTLET_TEST_BRIEF_COMMAND" < /dev/null
                in the tree's root, in the foreground; write gauntlet/write/<slug>.run.$state.output.move.txt:
                "exit=<n> timed_out=<true|false>", then the whole output; exit 0>

        - id: seal                     # the mechanical final commit
          depends_on: [state]
          when: "$state.output.next == 'seal'"
          bash: <git status --porcelain empty: write gauntlet/write/<slug>.seal.$state.output.move.txt "exit=0", "nothing".
                Else git add -A, git commit -m "<slug>: final", hooks run; write the file: "exit=<n>", then the output; exit 0>

        - id: juror
          depends_on: [state]
          when: "$state.output.next == 'juror'"
          command: juror
          context: fresh
          allowed_tools: []
          mcp: juror.mcp.json
          prompt: <move $state.output.move; case $state.output.cause; plan files; spec files>

        - id: revise
          depends_on: [state]
          when: "$state.output.next == 'revise'"
          command: reviser
          context: fresh
          allowed_tools: []
          mcp: reviser.mcp.json
          prompt: <round $state.output.round; kind $state.output.kind; plan files; spec files>

        - id: screen
          depends_on: [state]
          when: "$state.output.next == 'review'"
          include: screen
          with: { file: gauntlet/revisions/<slug>.$state.output.round.txt }

        - id: flag
          depends_on: [screen]
          when: "$screen.output.steering == true"
          runtime: uv
          script: ledger
          with: { mode: screen, slug: <slug>, round: $state.output.round, quote: $screen.output.quote }

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
          depends_on: [state, cut, result, test, seal, juror, revise, flag, review-plan, review-spec]
          trigger_rule: none_failed_min_one_success
          runtime: uv
          script: stage
          with: { mode: docket, start: $open.output.start }

        - id: report
          depends_on: [case]
          when: "$case.output.summary == true"
          command: reporter
          context: fresh
          allowed_tools: []
          mcp: reporter.mcp.json
          prompt: <round $case.output.round>

        - id: docket
          depends_on: [case, report]
          trigger_rule: none_failed_min_one_success
          runtime: uv
          script: stage
          with: { mode: docket, start: $open.output.start }

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

`<slug>`, plan files and spec files in prompts and `with:` come from `$INPUTS.slug` and `$state.output`. A script reads them as `INPUTS_<NAME>`, and no `when:` reads `$INPUTS`.

Fixtures, `write/fixtures/<route>.stubs.yaml`, one per route: tests then code, the run green, sealed (`written`); no spec, code only; a coder's contest ruled `TESTS`, fixed, green; a red run ruled `CODE`; a failed commit ruled; a failed seal ruled; `SPEC`, revision `SOUND`, the owner approves, tests re-cut; the owner revises a `SOUND` revision; `PLAN`, then a `No change.` spec round closing without the owner; `UNSOUND` then `SOUND`; a revision `SCREENED`; a rejected cut re-divvied; `stalled` after 5 verdicts; `DEFECTIVE` (`defective`); all twelve slots retired, `vacate` cancelling the run.

### `screen/screener.mcp.json`, `screen/screen.yaml` (revision rounds)

`FENCE_READ` adds `gauntlet/revisions/*.txt`. Input `file`'s description adds `gauntlet/revisions/<slug>.N.txt`. The spec review design is otherwise unchanged.

### `gauntlet-tree/gauntlet-tree.yaml` (brief baseline)

Node `baseline` also writes `gauntlet/baseline/<slug>.brief.txt`, once. It runs `GAUNTLET_TEST_BRIEF_COMMAND` exactly as it runs `GAUNTLET_TEST_COMMAND`, with the same first line. The file holds the one line `no test command` when the variable is blank. Node `paths` also prints `brief`, its absolute tree path. Node `write` passes `brief: $paths.output.brief`. The rest of the file is as the cut design and `gauntlet-design.md` give it.

### The repository's `.archon/config.yaml` (writing)

```yaml
env:
  GAUNTLET_TEST_BRIEF_COMMAND: "<the whole test command, printing one line per test: PASSED <id>, FAILED <id> or ERROR <id>, and no test source; for pytest, the command with --tb=no -rA -q>"
  GAUNTLET_TEST_BASE: "<colon-separated root paths the test writer may read and write besides tests/, such as pyproject.toml>"
```

`GAUNTLET_TEST_COMMAND` and `GAUNTLET_TEST_TIMEOUT` are the cut design's. Writing needs `GAUNTLET_TEST_COMMAND` and `GAUNTLET_TEST_BRIEF_COMMAND` to be set.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| What is owed next, cuts, wave records, red, writing's owner cases, the run's end | `write/scripts/stage.py` | any of it computed in a node, prompt or role; a `when:` deciding more than which node runs for `next` |
| The revision hearing's rounds, verdicts and owner cases | `.shared/rounds.py` with `write/scripts/ledger.py`'s `PROFILE` | `stage.py` or a node computing a round, slot or count |
| Cutting work into blocks and waves; what runs in parallel | the divvyer's output, checked by `stage.py cut` | blocks of one wave sharing a path; a block named by any other role or node |
| Running the blocks of a wave | `include:` with `fan_out:` of `write-tests` or `write-code`, `max_parallel: 2` | a `wait:` in either block; a `workflow:` child per block |
| Ruling on a red, a contest or a failed commit | the juror's verdict file | a writer, node or script deciding who is wrong; a writer retrying a failed commit |
| A wrong spec or plan | a revision round in `gauntlet/revisions/`, tried by the reviewer, approved at `bench`, entered by `enter` | any other edit of the approved files; the reviser revising past the quoted clause or the affected specs |
| Ending on a defective plan | the juror's `DEFECTIVE`, read by `stage.py close` | a size or line-count threshold; any other node ending writing |
| Commits | the writer's own message through `commit` of `fence/files.py`; node `seal` for the final commit | a writer's Bash; any other `git add` or `git commit` in a Gauntlet file; `--no-verify` |
| Test output a test writer sees | `fence/checks.py` running `GAUNTLET_TEST_BRIEF_COMMAND` | the test writer reaching `GAUNTLET_TEST_COMMAND` or the full baseline |
| The per-test listing | `GAUNTLET_TEST_BRIEF_COMMAND`'s `PASSED`, `FAILED` and `ERROR` lines, read by `stage.py red` | parsing a runner's full output; any other baseline comparison |
| What a test writer can see | `write-tests/test-writer.mcp.json`: `tests/`, the approved spec, `GAUNTLET_TEST_BASE` | a test writer handed the plan, code or a CODE section |
| What a coder can see | `write-code/coder.mcp.json`'s `FENCE_HIDE`; the block's ruling text | a coder handed the task, the spec, a test file or a verdict file |
| Writers' tools | the fence-files and fence-checks servers | `Bash`, `Task` or any built-in tool on a writer node |
| Writing's roles | `write/commands/`, `write-tests/commands/`, `write-code/commands/` | role rules restated in prompts; a role file of another phase |

## Order

1. Commits in the fence: `fence/files.py` (`commit`, `FENCE_COMMIT`), `fence/test_files_commit.py`. Needs `gauntlet-design.md`'s step 6. Agent: `builder`.
2. Writing's ledger: `write/scripts/ledger.py`, `write/tests/test_ledger.py`. Needs the spec review design's step 1. Agent: `builder`.
3. Writing's stage: `write/scripts/stage.py`, `write/tests/test_stage.py`. Needs step 2. Agent: `builder`.
4. Roles: `write/commands/divvyer.md`, `write/commands/juror.md`, `write/commands/reviser.md`, `write/commands/reviewer.md`, `write/commands/reporter.md`, `write-tests/commands/test-writer.md`, `write-code/commands/coder.md`. Agent: `role-author`.
5. Screen reads revisions: `screen/screener.mcp.json`, `screen/screen.yaml`. Needs the spec review design's step 5. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
6. Writer blocks: `write-tests/write-tests.yaml`, `write-tests/test-writer.mcp.json`, `write-tests/fixtures/committed.stubs.yaml`, `write-tests/fixtures/contest.stubs.yaml`, `write-code/write-code.yaml`, `write-code/coder.mcp.json`, `write-code/fixtures/committed.stubs.yaml`, `write-code/fixtures/contest.stubs.yaml`. Needs steps 1 and 4. The builder measures whether the repository's `env:` reaches a node's MCP servers. If it does not, the builder stops and reports the gap. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
7. Writing block: `write/write.yaml`, `write/divvyer.mcp.json`, `write/juror.mcp.json`, `write/reviser.mcp.json`, `write/reviewer-plan.mcp.json`, `write/reviewer-spec.mcp.json`, `write/reporter.mcp.json`, `write/fixtures/*.stubs.yaml`. Needs steps 3 to 6. If Archon rejects `include:` with `fan_out:` inside a `loop_group` body, the builder stops and reports the gap. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
8. Brief baseline: `gauntlet-tree/gauntlet-tree.yaml` (`baseline`, `paths`, `write`), `gauntlet-tree/fixtures/tree.stubs.yaml`. Needs step 7 and `gauntlet-design.md`'s step 4. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
