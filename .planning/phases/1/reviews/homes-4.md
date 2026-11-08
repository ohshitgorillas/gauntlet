# Round 4: moved facts and their homes (D-98, D-63)

Each moved fact has one line: the fact, a `grep -nF` token that carries its value, and its home (file and heading). Plan 7 runs `grep -nF -- '<token>'` over the seven designs, `runtime-model-design.md` and `contracts.md`; every hit must lie in the home section, or its line must name the home file. `runtime-model-design.md` is abbreviated RM below.

Plan 7 Task 1 ran every token over the seven designs, `runtime-model-design.md` and `contracts.md` and fixed one hit (`writing-design.md`, the `fence/checks.py` comment on `FENCE_CUT=1`, which now names the section that holds the coder's fence value). The last column is the count of hits outside the home whose line does not name the home, after that fix.

## Moved facts

| Fact | Token | Home | Hits outside the home not naming it |
|---|---|---|---|
| The item hash file, written once at round 1 when absent | `.items.sha256` | RM, Hearing state | 0 |
| The set-aside folder for a changed item file | `stale/<slug>.<n>/` | RM, Hearing state | 0 |
| `owed` is `approved` when `approved/<slug>.txt` exists, the hearing skipped | `owed "approved"` | RM, Hearing state | 0 |
| `first`: writing's revision hearing passes the round after the latest closed one | `passes the round after the latest closed one` | RM, Hearing state | 0 |
| `next` is `vacant` once twelve LEADING reviews with N above start exist | `as soon as twelve such reviews exist` | RM, Hearing state | 0 |
| A guard file never marks its round tried | `never marks round` | RM, Hearing state | 0 |
| One line per loop iteration in `<slug>.iter.txt` | `one line per loop iteration` | RM, Hearing state | 0 |
| Verdict parsing: longest known name after `Verdict:`, an unknown first line is an owner case | `by the longest known name the text after` | RM, Ledger | 0 |
| `INPUTS_START` is the latest tried round when the run began | `the latest tried round when the run began` | RM, Ledger | 0 |
| `screen` and `record` exit 1 when the file exists | `exit 1 when it exists` | RM, Ledger | 0 |
| A ruling resets the attempt, non-responsive and stretch counts | `a ruling resets the attempt, non-responsive and stretch counts` | RM, Ledger | 0 |
| `close` outcome `vacant` with empty file and summary | `` `outcome` `vacant` `` | RM, Ledger | 0 |
| The ending ruling is written before the loop ends | `written before the loop ends` | RM, Ledger | 0 |
| A plan is cited when the latest cite line lists no unresolved marker (D-74) | `cited when that line lists no unresolved marker` | RM, Ledger | 0 |
| Slot bound | `SLOTS = 12` | RM, Loop shape and bounds | 0 |
| Stretch bound | `STRETCH = 12` | RM, Loop shape and bounds | 0 |
| Repair-only bound (plans) | `REPAIRS = 5` | RM, Loop shape and bounds | 0 |
| Run-iteration cap | `CAP = 200` | RM, Loop shape and bounds | 0 |
| Idle iterations that call the owner | `IDLE = 1` | RM, Loop shape and bounds | 0 |
| A hearing loop's `max_iterations` | `max_iterations: 200` | RM, Loop shape and bounds | 0 |
| Attempts that call the owner | `attempts >= 5` | RM, Loop shape and bounds | 0 |
| Non-responsive reviews that call the owner | `non_responsive >= 2` | RM, Loop shape and bounds | 0 |
| A failure resume restarts a `loop_group` at iteration 1 | `the group restarts at iteration 1` | RM, Resume and rerun | 0 |
| A resumed landing owes repair until the latest mended file has a SOUND review after it | `no SOUND review after it` | RM, Resume and rerun | 0 |
| The commit tool's lock file | `gauntlet-commit.lock` | RM, Commit model | 0 |
| The commit tool's add and commit commands | `git commit --only -m` | RM, Commit model | 0 |
| The leftover patch of an uncommitted block | `.leftover.<move>.patch` | RM, Commit model | 0 |
| The tree restore after the patch | `git clean -fd -- :/` | RM, Commit model | 0 |
| The seal's commit command | `git commit -F -` | RM, Commit model | 0 |
| The seal subject at stage `k` after the first | `-s<k>` | RM, Commit model | 0 |
| The fast-forward-only merge | `--ff-only` | RM, Commit model | 0 |
| The commit tool answers "nothing" when no path changed | `exit=0 nothing` | RM, Commit model | 0 |
| How every fence config receives its variables: the `sh -c` launch line resolving `$ARCHON_HOME` | `exec uv run --script` | `gauntlet-intake-design.md`, section `intake/clerk.mcp.json` | 0 |
| The test writer's fence values (F8) | `FENCE_READ=tests:gauntlet/specs/approved:docs/testing.md:@base` | `writing-design.md`, section `write-tests/write-tests.yaml` | 0 |
| The coder's fence values (F9) | `FENCE_HIDE=tests:gauntlet/items:gauntlet/specs:gauntlet/baseline:gauntlet/revisions:gauntlet/write` | `writing-design.md`, section `write-code/write-code.yaml` | 0 |
| The coder's cut mode (F9) | `FENCE_CUT=1` | `writing-design.md`, section `write-code/write-code.yaml` | 0 |
| The review before landing's fence values (F15) | `FENCE_ONCE=gauntlet/mend/*.final.*.txt` | `landing-design.md`, section `mend/commands/mend-code.md` (the fences table) | 0 |
| The mend reviewer's fence values (F-table row of `mend-review.mcp.json`) | `FENCE_WRITE=gauntlet/mend/*.review.*.txt` | `landing-design.md`, section `mend/commands/mend-code.md` (the fences table) | 0 |
| The shared screener's fence values (F7) | `FENCE_READ=gauntlet/plans/*.txt:gauntlet/specs/*.txt` | `spec-review-design.md`, section `screen/screen.yaml` | 0 |
| The plan review defense's deny list (F1) | `gauntlet/plans/*.review.*.txt:gauntlet/plans/*.ruling.*.txt` | `plan-review-design.md`, section `plan-review/defense.mcp.json` | 0 |
| The stage bound | `STAGES = 3` | `gauntlet-design.md`, heading "Stages" | 0 |
| The back-to-planning direction copy | `gauntlet/back/<slug>.<n>.direction.md` | `gauntlet-design.md`, heading "Back to planning" | 0 |

## Candidates

Disagreements between copies that no ruling settles. The home states the value of the design whose `## Homes` table names it as home; Plan 7 puts each to the owner.

1. An uncommitted mend. Copies: `writing-design.md` `write/scripts/stage.py` `result` writes the block's uncommitted changes as `gauntlet/write/<slug>.leftover.<move>.patch` and restores the tree to `HEAD` (D-68, ruled for writing); `landing-design.md` `mend/mend.yaml` node `pose` counts an uncommitted mend as case `commit-failed` and leaves the tree as it is, and the mend never resets or discards a commit. D-68 rules writing's blocks only. Row id: none yet (a restore or leftover patch for the mender's uncommitted edits is a cross-design contract with no row). Home written: `runtime-model-design.md`, Commit model, states both behaviours as they are.
