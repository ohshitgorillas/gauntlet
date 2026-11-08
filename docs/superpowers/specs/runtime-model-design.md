Status: proposed.

# Gauntlet runtime model

## Why

The seven designs each restated the shared runtime model (how a hearing keeps its state, what the ledger answers, how a hearing loop is shaped and bounded, what a resume or a rerun does, who commits in the tree), and a ruling fixed one copy while the others kept the old value (G-108, G-64, G-65, G-82, G-85, G-97; owner ruling D-98). This file states the model once. It holds rules and values and no module and no `## Order` step: every module stays in its design with its signature, and the rule or value it implements points here by heading. The designs that point here: `gauntlet-design.md`, `gauntlet-intake-design.md`, `plan-review-design.md`, `spec-review-design.md`, `worktree-cut-design.md`, `writing-design.md` and `landing-design.md`. `contracts.md` indexes each fact below by row id and names this file as its home.

A pointer to this file names the heading, never a line. A value in this file is the value of the latest ruling that set it (the CONTEXT D-NN line, `RULINGS.md`).

## Hearing state

A hearing is the rounds of one item file in one folder, derived from the files alone. Plan review hears in `gauntlet/plans/`, spec review in `gauntlet/specs/` and writing's revisions in `gauntlet/revisions/`, each as the checkout holds it. `<slug>` is the function `slug` of `.shared/pin.py` over the item file (worktree cut design). Nothing else keeps state: a resumed run and a fresh run on the same item file read the same state (see "Resume and rerun").

**The files of one hearing**, in the hearing's folder:

| File | Rule |
|---|---|
| `<slug>.N.txt` | the round's file, round `N`; round numbers climb for the whole hearing and no file is overwritten |
| `<slug>.review.N.txt` | written once; line 1 is `Verdict: <verdict>`; the reviewer writes it, or `ledger.py screen` for a `SCREENED` round |
| `<slug>.ruling.N.txt` | written once by `ledger.py record`: the case, the question shown, the decision and the owner's text verbatim |
| `<slug>.guard.N.txt` | one entry appended per `guard`, `idle` or `cap` ask, `N` the untried round being filed or repaired; it never marks round `N` tried |
| `<slug>-summary.N.md` | written once by the reporter |
| `<slug>.idle.K.md` | written once by the analyst; `K` is one above the guard-record count at the ask |
| `<slug>.iter.txt` | one line appended per loop iteration by `ledger.py filing`: `state`'s round, owed, the guard-record count and `repairs` |
| `<slug>.items.sha256` | the sha256 of the item file the hearing runs against; written once at round 1, when absent |
| `stale/<slug>.<n>/` | the slug's set-aside files, `n` the next free number |
| `approved/<slug>.txt`, `approved/<slug>-summary.md` | written once by the hearing's `enter`, only after the owner's approval |

A round is **tried** when its review or its ruling exists. A guard file never marks a round tried.

**First round (D-67).** `first` is the hearing's first round. A folder that holds one hearing per slug passes 1. Writing holds one revision hearing per `Rework: spec` or `Rework: plan` direction in one folder, and passes the round after the latest closed one. `since`, `attempts`, `non_responsive`, `stretch` and `owed "owner"` count from `first`: a review, ruling or guard record below `first` belongs to an earlier hearing. `owed "ended"` is read only at or after `first`.

**`owed`** says who owes the round `state` names. The values:

- the author (`defense`, `speccer`, `reviser`): the round file is missing, or for plans it is not cited (`cite.py` is the one judge, see "Ledger");
- the reviewer (`prosecutor`, `arbiter`, `reviewer`): the round file is ready and untried;
- `owner`: the latest tried round's review opens an asking case (an owner case, `unknown`, `deadlock` or `non-responsive`) and no ruling or guard record follows it, whichever iteration or run wrote it, so the ask is owed again; also, from the files alone, an unanswered ask that is read from state and not from a review: `guard` while `stretch` is at `STRETCH` or `repairs` at `REPAIRS` (an answer is a guard record, which restarts both counts), and `idle` while `<slug>.idle.K.md` exists for K one above the guard-record count (an answer is a guard record, which makes that K stale). `cap` is not carried: it counts this run's iterations, and a rerun starts the count again. Where `owner` holds it comes before the author and the reviewer, so no turn is spent past a bound before the owner is asked again;
- `ended`: the latest ruling at or above `first` carries an owner-case decision that ends the hearing (`ends`);
- `approved`: `<folder>/approved/<slug>.txt` exists, so a rerun on an unchanged item file hears nothing.

**`next`** is the author when `owed` is the author. Otherwise it is the reviewer slot that tries the round, `<letter>` and `1 + the OBJECTION: LEADING reviews with N above start`, or `vacant` as soon as twelve such reviews exist, whatever the round's state (the cancel needs no repair turn first). A profile whose reviewer is a fresh node each round (writing's) retires no slot, and its `next` is never `vacant`.

**The item hash.** Outside the loop (`start` None, node `docket-in`), before anything else: `<slug>.items.sha256` absent: the ledger writes the sha256 of the item file there. Present and different: the ledger moves every file of the slug in the folder, `approved/` included, into `stale/<slug>.<n>/`, `n` the next free number, then writes the new hash, so the changed item file is heard from round 1. A back to planning sets the slug's files aside the same way, by node `back` of `gauntlet-run`, and the ledger never reads `gauntlet/back/`.

**The `approved/` short-circuit (D-27).** `owed "approved"` ends the block with no agent: the block's `handoff` returns the approved file, and `open`, `swear-in` and `hearing` are skipped. A rerun whose latest ruling already ended the hearing (the run stopped before `enter`) starts no agent either: `open` and `swear-in` skip, `close` reads the ruling and `enter` runs off it.

## Ledger

The ledger is `.shared/rounds.py`: the one reader of a hearing's state, the one writer of rulings, guard records and `SCREENED` reviews, and the runaway guard. Each workflow's `scripts/ledger.py` passes a `Profile` and calls `main` (spec review design, module `.shared/rounds.py`, holds the dataclasses and signatures; plan review's, spec review's and writing's profiles are in their designs). It is a script node run with `runtime: uv`, standard library only. A script node passes `INPUTS_MODE`; the slug is `.shared/pin.py`'s slug of `INPUTS_ITEMS`. Every in-loop mode (`state`, `filing`, `docket`) also passes `INPUTS_START`, the latest tried round when the run began (`$docket-in.output.start`); `docket` also passes `INPUTS_BASE`, the lines of `<slug>.iter.txt` when the run began (`$docket-in.output.base`); `close` passes `INPUTS_START`. Script modes hear from round 1; `stage.py` passes `first` itself.

**Verdicts.** A verdict is read from line 1 of a review, `Verdict: <verdict>`, with markdown markup stripped and case ignored, by the longest known name the text after `Verdict:` starts with. A first line naming no known verdict is an owner case (docket case `unknown`, option `reply`), never an exit 1. `OBJECTION: LEADING` and `SCREENED` are never an owner case: the next round goes to the author to repair.

**Modes.**

- `state` (in the loop: `ready`; outside it: `docket-in`): prints `{ round, slug, file, owed, next, start, since, attempts, non_responsive, stretch, repairs, base, rulings, review, verdict }`. `round` is the round to file or try: the latest round if its file is uncited or untried, else latest + 1 (1 when none). `file` is `<folder>/<slug>.<round>.txt`. `start`: outside the loop, the latest tried round, 0 when none. `base`: outside the loop, the lines of `<slug>.iter.txt`, 0 when none. `since`: N of the latest ruling, 0 when none. `attempts` and `non_responsive` count the reviews with N above `since`. `stretch` counts tried rounds with N above `since` and N at or above the latest guard record's round, plus `repairs`. `repairs` (plans only) counts the lines of `<slug>.cite.<round>.txt` that list a marker, past the count the last entry of `<slug>.guard.<round>.txt` holds, all of them when that file is absent, whatever the iteration wrote. `rulings` lists the paths of every ruling and guard file, oldest first (guard file N before ruling N); the owner's words in either bind alike. `review` is the latest review's path and `verdict` its verdict, `""` when none.
- `filing` (node `filing` only, profiles that count iterations): mode `state` that first appends one line to `<slug>.iter.txt`, so the file holds one line per loop iteration.
- `docket` (read after the iteration's try): prints `{ case, ask, attention, options, round, summary, verdict, idle, reason }`. The first case that holds, in this order: `vacant` (`next` is `vacant`: nothing asked; the hearing ends on it, see "Loop shape and bounds"); `none` when `owed` is `ended` (the ruling that ends the hearing is on file: nothing is asked, so the one iteration after an ending answer asks and spends nothing, and `idle` and `cap` cannot hold in it); each owner case of the profile, in the profile's order, on the latest verdict; `unknown`; `deadlock`; `non-responsive`; `guard`; `idle`; `cap`; `none`. The bounds behind `deadlock`, `non-responsive`, `guard`, `idle` and `cap` are stated in "Loop shape and bounds". `ask` is true for every case but `vacant` and `none`. Every asking case that is not an owner case offers one option, `reply`. `attention` is, for an owner case with `summary`, the summary file's text, for `bench` the review's question, for `guard` the counts then the latest line of `<slug>.cite.<round>.txt` (each unresolved marker with its reason) when it lists one, else the latest review's text, for `idle` the counts then the text of `<slug>.idle.<idle>.md`, and for the others the counts and the latest review's text. `summary` is true only for an owner case with `summary` whose `<slug>-summary.N.md` is still absent, so a case read again on a resume or a rerun starts no second reporter. `round` is the round of the review the case was read from; for `guard`, `idle` and `cap` it is `state`'s round, which is untried, so their answer is a guard record. `idle` is K of `<slug>.idle.K.md` (0 outside case `idle`) and `reason` is true when that file is still absent, so node `why` writes it. Every case but `vacant`, `guard`, `idle` and `cap` is read from the latest tried round's review when no ruling or guard record follows it, whichever iteration or run wrote it; with no such review the case is `none` unless `guard`, `idle` or `cap` holds.
- `screen` (`INPUTS_ROUND`, `INPUTS_QUOTE`): writes `<slug>.review.<round>.txt`, line 1 `Verdict: SCREENED`, then the screener's quote verbatim; exit 1 when it exists.
- `record` (`INPUTS_ROUND`, `INPUTS_CASE`, `INPUTS_DECISION`, `INPUTS_TEXT`), run in the iteration after the ask. The round's review exists (the case was read from it): writes `<slug>.ruling.<round>.txt`, exit 1 when it exists; a ruling resets the attempt, non-responsive and stretch counts. No such review (`guard`, `idle` or `cap`, whose round is untried): appends one entry to `<slug>.guard.<round>.txt` holding the case, the question shown, the decision, the owner's text verbatim and the count of lines of `<slug>.cite.<round>.txt` listing a marker at the ask (0 when absent). A guard record is never a ruling: the round stays untried and owed as before, attempts and `non_responsive` are not reset, the run's iteration count keeps counting, and `stretch` and `repairs` restart from the entry.
- `close` (`INPUTS_START`): prints `{ outcome, file, summary }` for the latest ruling whose decision ends the hearing, `N` the round it was given after, `outcome` `approved`, or `invalid` when that owner case is `invalid`. `file` is the bare name `<slug>.N.txt` and `summary` the bare name `<slug>-summary.N.md`, both relative to the hearing's folder (not `state`'s `<folder>/<slug>.<round>.txt` form), and the `enter` nodes put the folder in front. No such ruling and `next` is `vacant`: `outcome` `vacant`, `file` and `summary` `""`. No such ruling otherwise (node `close` after `open` found no plan or spec needed): all three `""`. The final ruling is written before the loop ends, so the block's `enter` and `handoff` read `$close.output.file`.

**The owner cases of a profile** are `OwnerCase(verdict, case, options, summary, ends)`. A case with `summary` shows the reporter's summary file. `ends` names the option that ends the hearing, `""` when none. The profiles are in the designs: plan review's (`APPROVED` opens `review`, `APPROACH THE BENCH` opens `bench`), spec review's (`READY`, `INVALID`, `APPROACH THE BENCH`) and writing's revisions (`SOUND`, `APPROACH THE BENCH`).

**Citation state (D-74).** `plan-review/scripts/cite.py` is the one judge of citation state. It appends one JSON line per run to `<slug>.cite.N.txt`, `{ "unresolved": [ "<path> | <quote> | <reason>", ... ] }`, `[]` when every marker resolved. The profile's `filed` for plans reads the latest line: a round file is cited when that line lists no unresolved marker, and no such file means it is not cited. The ledger counts the lines that list a marker as `repairs`, and the guard's attention shows them. No other code tests the text of a plan for a marker.

## Loop shape and bounds

**The shape of a hearing body** (plan review's `hearing`, spec review's `hearing`, writing's `work`). One `loop_group`, no nesting. The nodes before it open the sessions (`open`, `swear-in`), so every author turn continues the one author session and each reviewer slot continues its own fork of the sworn-in session, across rounds and across the owner's answers; an agent node in the body starts no session of its own, `screen` and `report` excepted. In the body:

- the first node, `record`, turns the owner's previous answer (`$LOOP_PREV.bench.output`) into a ruling file or a guard entry, so the answer that ends the hearing ends the loop one iteration later;
- `filing` always runs (`trigger_rule: all_done`), counts the iteration and prints `owed`;
- every agent node is gated on `owed` and `next` by its own `when:`, so the extra iteration after an ending answer runs script nodes only;
- the owner's wait, `bench`, is the body's sole terminal sink (`loop-nodes.md:682-684`: any other placement is a load error), skipped by its `when:` on iterations that need no answer;
- plans, reviews and summaries pass between nodes only as paths.

**`until_bash`.** It reads the work and never a wait its own `when:` can skip (D-28; `loop-nodes.md:667-697`): the reference is assigned to a shell variable unquoted, tested with a guard, and taken from a node that always runs. A hearing ends on `[ "$owed" = ended ] || [ "$held" = vacant ]`, with `owed=$filing.output.owed` and `held=$docket.output.case`. Writing's `work` and the mend's `repair` end on `end=$docket.output.end` and `end=$pose.output.end` being non-empty. Intake's `talk` ends on `$latest.output.phase` being `done`.

**`max_iterations`.** It bounds autonomous iterations, and each accepted answer to the terminal wait permits one more iteration past it (`loop-nodes.md:674-677`, `workflow-language.md:773`). A loop that asks on every iteration past `CAP` therefore never ends on `max_iterations`. Intake's `talk` sets 1, and the answer to each turn permits the next, so the conversation has no cap.

**Vacancy and the cancel (D-69).** Case `vacant` is a `docket` case, not a node in the body. The hearing's `until_bash` ends the loop on it, and node `vacate` after the group, `cancel:` with `when: "$close.output.outcome == 'vacant'"`, cancels the run without asking, so the cancel comes before any ask and before `max_iterations`. A `vacate` inside the body would be a second terminal sink and a load error. Plan review and spec review keep `vacate`; writing has none.

**The unrolled bounded form (D-93).** A `loop_group` body rejects a `workflow:` node (`workflow-language.md:1732-1734`, `:2543-2544`). A repeated `workflow:` node therefore takes an unrolled bounded form, each repeat with its own node id, in `gauntlet-run`'s own scope: `land` to `land-4` for the landing rounds, and the stages (`pin`, `tree`, `cut` and the land rounds, `s2-` and `s3-` prefixed after stage 1). Each repeat starts when the round before it hands off `moved` (landing) or landed (stages), and its node ids are its own.

**Bounds, each stated once.**

| Name | Value | Meaning |
|---|---|---|
| `SLOTS` | 12 | reviewer slot nodes `<prefix>-1` to `<prefix>-12`, named `<letter>1` to `<letter>12` in `next`; one slot tries every round until it returns `OBJECTION: LEADING`, which retires it |
| `STRETCH` | 12 | tried rounds since the last ruling and at or above the latest guard record's round, plus repairs, that call the owner (case `guard`) |
| `REPAIRS` | 5 | plans only: repair-only iterations of the round being filed, since its latest guard record, that call the owner at once (case `guard`), in the iteration that wrote no review |
| attempts | 5 | rounds whose verdict is an attempt (`REJECTED` or `APPROACH THE BENCH` for plans, `ANOTHER PASS` or `APPROACH THE BENCH` for specs, `UNSOUND` or `APPROACH THE BENCH` for revisions) since the last ruling that call the owner (case `deadlock`) |
| non-responsive | 2 | `OBJECTION: NON-RESPONSIVE` reviews since the last ruling that call the owner (case `non-responsive`) |
| `IDLE` | 1 | trailing iterations that wrote nothing that call the owner (case `idle`); read by `docket` for profiles with iterations and by writing's `stage.py docket`, `IDLE = 1` in every profile |
| `CAP` | 200 | the loop's `max_iterations`; from this many loop iterations in this run every iteration calls the owner (case `cap`) |

In code and YAML the bounds read `SLOTS = 12`, `STRETCH = 12`, `REPAIRS = 5`, `CAP = 200` and `IDLE = 1`, a hearing loop's `max_iterations: 200`, and the docket cases `attempts >= 5` and `non_responsive >= 2`.

Each ruling resets the attempt, `NON-RESPONSIVE` and stretch counts to zero. A guard record resets the stretch and `repairs`; attempts, `NON-RESPONSIVE` and the run's iteration count go on. `OBJECTION: LEADING` and `SCREENED` have no count of their own; they count in the stretch and the run's iterations only. The stretch counts tried rounds with N above `since` and at or above the latest guard record's round, plus `repairs`.

**Run iterations.** Every iteration of the hearing loop in this run, a repair-only or refused one included, counted by node `filing` as a line of `<slug>.iter.txt`; the ledger counts the lines above `base`. Writing's `stage.py state` appends its own line per iteration and `stage.py docket` counts the lines above `INPUTS_BASE`.

**The idle iteration (D-75).** An iteration that wrote nothing: no round filed or repaired, no review, no ruling or guard record, so the ledger's round, owed, guard-record count and repair count are as the iteration began (in writing, an iteration that writes no file). The first one is docket case `idle` and calls the owner. Before the ask, node `why` runs one fresh, read-only analyst (the same role in plan review, spec review and writing), which writes why no progress was made to `<slug>.idle.K.md`; the ask shows it. The owner's answer is a guard record that binds the next turn, and the hearing goes on: nothing is cancelled. The author's, speccer's and reviser's sessions are not used for the analysis.

**The mend's `repair` and the owner stop.** Group `repair` of the mend has `max_iterations: 200` and `fresh_context: true`. Every iteration that the owner has not ended meets the owner at its one wait `ask`, so there is no stall count; each answer permits one more iteration. The landing design holds the nodes.

**The landing rounds.** `land/land.yaml` runs once per round, `land` to `land-4` (per stage), and re-mends at most twice, whatever the timing of the moves: a round re-mends while `made` holds fewer than two branches, and a move that would need a third re-mend fails `onto`, naming the move. In the last round, `land-4`, `merge` exits 1 naming a move it finds.

## Resume and rerun

**A failure resume.** `archon workflow resume <run id>` skips completed nodes and re-drives the failed and not-yet-run ones (`workflow-language.md:966-970`); `always_run: true` reruns a node on resume while other completed nodes replay (`workflow-language.md:987`); a resumed `tree` node reuses its child run's recorded worktree (`workflow-language.md:2136`). A `loop_group` has no persisted iteration cursor: the group restarts at iteration 1 (`loop-nodes.md:945-947`). A wait cannot carry `always_run` (`workflow-language.md:718`), so a resumed run replays the owner's answer and never asks again. Every stop in a block is a failed node: the tree, its branch and any rebase in progress stay, and the resume picks the run up at that node.

**A rerun.** A rerun is a new run on the same item file. Its sessions start afresh, and the rounds continue from the files. A rerun on an unchanged item file whose hearing was approved hears nothing (`owed "approved"`, "Hearing state"); one whose latest ruling already ended the hearing starts no agent. A rerun on a changed item file (its sha256 differs from `<slug>.items.sha256`) is heard from round 1 after the slug's files are set aside into `stale/<slug>.<n>/` (G-51, "Hearing state"). A rerun after a back to planning is heard from round 1 too, because `gauntlet-run`'s node `back` set the slug's files aside the same way before it printed its command.

**What is owed is read from the files alone (D-66 (b)).** Neither a resume nor a rerun has the iteration that wrote a file, so no rule reads "what this iteration wrote":

- the owner case is read from the latest tried round with no ruling or guard record after it, whichever iteration or run wrote the review, so an ask a resume or a rerun finds unanswered is asked again (`state` owes `owner`; `docket` reads the case again, and a summary file already written starts no second reporter). A `guard` or `idle` ask is read the same way, from the counts and from `<slug>.idle.K.md` ("Hearing state", `owed`), so a rerun runs no author or reviewer turn past the bound before the owner sees it;
- a missing plan is nothing to resolve: `cite.py` exits 0 on a missing plan, and the round is owed to the author;
- a resumed landing owes repair while the latest `mended` file has no SOUND review after it: `onto` prints `unreviewed`, and the first iteration of the group retests and reviews that mend as a run again does, before the owner is asked (G-99). `onto` reads the checkout's tip with `git rev-parse` in the checkout (G-101).

**Which nodes skip.**

- A hearing skipped on `owed "approved"` or `"ended"` starts no second reporter and no agent: `open`, `swear-in` and `hearing` skip, `close` reads the ruling, and `enter` and `handoff` run off it.
- A skipped hearing reads its ruling: the ruling written before the loop ended is the record, so a rerun after a stop before `enter` copies from it.
- A node that must run on a resume carries `always_run: true`: the mend's `onto`, `rebase`, `test-tree`, `red`, `test-head`, `confirm` and group `repair`, and `land`'s `onto`, so a resume rebases, verifies and checks against the checkout as it then stands.
- A mend test-run file is keyed by the commits it ran on, so a rerun on the same commits reuses its file.

## Commit model

**Who commits on the tree's branch.** Writers commit their own block through the `commit` tool of `fence/files.py` (its registration: the writing design, module `fence/files.py (commit)`). Node `seal` makes the stage's final commit. The mend's menders commit through the same tool, on top of the branch's last commit. No other Gauntlet file runs `git add` or `git commit`; no writer holds Bash; `--no-verify` is never used. The checkout is written by one node, `land`'s `merge`.

**The commit tool's rules (D-68).** The tool commits only the paths that changed:

- it takes an exclusive lock on `<git rev-parse --git-dir>/gauntlet-commit.lock`, held across every command;
- of the listed paths it keeps those `git status --porcelain` lists as changed (a listed path that does not exist and was never tracked is no change); none changed: no commit, and it returns `exit=0 nothing`;
- else it runs `git add -A -- <changed>` then `git commit --only -m <message> -- <changed>`, hooks running;
- a failing commit after which a hook changed files among the changed paths is retried once, with the same two commands;
- it returns `exit=<n>`, then, when git exits non-zero, the names of the hooks that failed and never their output; exit 0 adds `commit=<full hash>`. A path outside `FENCE_WRITE` or inside `FENCE_DENY` or `FENCE_HIDE` raises `PermissionError` and stages nothing.

**What a failed or uncommitted block leaves.** A block of a wave that did not end committed (outcome `contest`, `commit-failed` or `blocked`) is handled by `stage.py result` in the tree's root, never the checkout (`git -C <tree>`). Writers run one at a time (`max_parallel: 1`), so every uncommitted change is the wave's own. `result` first writes every uncommitted change as `gauntlet/write/<slug>.leftover.<move>.patch` (`git diff --binary HEAD`, staged and unstaged, then each untracked file not ignored as a new-file diff with `--binary`, so `git apply` restores a binary file's content), and only then restores the tree to `HEAD`: `git restore --source=HEAD --staged --worktree -- :/` and `git clean -fd -- :/`, ignored files (`gauntlet/` among them) kept. The patch is named in the amicus case's files, and the block is carried.

**The mend's uncommitted edits (G-128).** The mend's menders leave a tree that is not clean when the commit tool fails, and the mend handles it the same way, in its node `pose`, in the tree's root. When `git status --porcelain` (`gauntlet/` excluded) is not empty and the owner has not ended the repair, `pose` first writes the uncommitted changes as `gauntlet/mend/<slug>.leftover.<k>.patch` (`k` the iteration's `n`, the form above) and only then restores the tree to `HEAD` the same way. The mend runs one mender at a time, so every uncommitted change is that mender's own. The case is `commit-failed`, the patch is named in the amicus case's files, and the restore resets no commit: the next mender starts on the committed tip, and its commit never carries the old edits.

**The seal.** Node `seal` runs only on `next: seal`, once per stage:

- a clean tree (`git status --porcelain` empty) writes `gauntlet/write/<slug>.seal.<move>.txt` as `exit=0`, then `nothing`, and commits nothing;
- a dirty tree runs `git add -A` then `git commit -F -` with the message on stdin, hooks running;
- the message's line 1 is the repository's `GAUNTLET_FINAL_SUBJECT` (D-78), `<slug>: final` when unset, with each `<slug>` replaced by the slug at stage 1 and by `<slug>-s<k>` at stage `k` after it, then a blank line, the plan summary file when the plan is not `""`, and each summary file of the revision rounds the owner approved, in order of N, separated by blank lines;
- only node `seal` reads `GAUNTLET_FINAL_SUBJECT`, so a repository whose `commit-msg` hook refuses `<slug>: final` sets a subject it accepts. A failed seal is the amicus's `commit-failed` case.

**The mend's commits and the merge.** Mend commits sit on top of the branch's last commit; the mend never resets, amends or drops a commit, never aborts a rebase and never writes in the checkout. The rebase belongs to the mend, in a tree, and is the only rebase in Gauntlet. Landing writes the checkout's tracked files only with `git merge --ff-only <branch>`: no squash, no merge commit, no push. A checkout that moved after the check makes `merge` print `moved`, write nothing and hand off `moved`; in the last round `merge` exits 1 naming the move.
