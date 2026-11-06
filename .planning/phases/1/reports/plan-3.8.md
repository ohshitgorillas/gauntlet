PLAN CHECKPOINT: decision
Plan: .planning/phases/1/PLAN-3.md
Tasks: 2 of 5 (Task 3, round 3: rulings recorded and drafted into the designs, uncommitted for the D-79 closed review)
| Task | Commit | Note |
|---|---|---|
| 1 (routes, D-11..D-37) | 0d08176 | earlier dispatch: 50 groups routed, 27 load-bearing |
| 1 (rulings) | 14f5985 | 50 `Ruling:` lines, one per group |
| 2 (apply rulings, G-01..G-44, G-46..G-50) | e9d81de | designs, contracts.md, ROADMAP.md, REQUIREMENTS.md, PROJECT.md; copy list resolved |
| 2 (G-45) | e01ea0b | owner's option A, K = 2 |
| 3 round 2 (record) | dfd1158 | `REVIEW-pass2.md`, `reviews/conv-*.md`, `reviews/convergence-graph.md`, CONTEXT.md D-38..D-59 |
| 3 round 2 (decision reviews) | 47a356a | `DECISION-REVIEW.md` D-38..D-59, `RULINGS.md` pass-2 table, `reviews/dr2/` |
| 3 round 2 (apply, cross-design) | 9901135 | nine cross-design groups and all contracts rows |
| 3 round 2 (apply, per design) | af2e0ae | the seven designs and contracts.md |
| 3 round 2 (rulings after application, recorded) | 1035d43 | planning files only |
| 3 round 2 (apply the three, record rulings, graph) | 87e0734 | plan-review, spec-review, writing designs, contracts.md, `REVIEW-pass2.md` section 10, `reviews/convergence-graph-3.md` |
| 3 round 3 (record) | 060107b | `REVIEW-pass3.md`, `reviews/conv3-*.md`, CONTEXT.md D-60..D-78 |
| 3 round 3 (D-79) | 60247c2 | orchestrator: CONTEXT.md D-79 |
| 3 round 3 (rulings, drafted) | uncommitted | G-104..G-119 recorded and drafted; held for the D-79 closed review |

Round 3 rulings (this dispatch, uncommitted under D-79):
- Recorded: `REVIEW-pass3.md` section 9 (one row per group, route, D-NN, letter, source); `RULINGS.md` "Pass 3 rulings" (authority paragraph and table); CONTEXT.md D-66..D-78 each end with "Ruling (<source>, 2026-11-05, RULINGS.md): (<letter>)." as earlier passes' D-lines do. Source verbatim: G-104 owner; G-106 owner delegated, no option named, orchestrator took (c) because the restore discards an agent's edits; the other 14 owner delegated to the recommended option ("fine whatever").
- Rulings: G-104 (b), G-105 (b), G-106 (c), G-107 (c), G-108 (b), G-109 (b), G-110 (c), G-111 (b), G-112 (b), G-113 (b), G-114 (b), G-115 (b), G-116 (b), G-117 (b), G-118 (b), G-119 (b).
- Drafted files (uncommitted): the seven designs, `contracts.md`, `.planning/PROJECT.md` (Key Decisions, landing row), `.planning/ROADMAP.md` (Phase 6 criterion 2), `.planning/REQUIREMENTS.md` (RUN-10), `.planning/phases/1/CONTEXT.md`, `REVIEW-pass3.md`, `RULINGS.md`. `git diff --shortstat` over them: 14 files, 397 insertions, 257 deletions.
- H38 (noted at G-107): its first column named `vacate` in writing too; writing has none. Column 1 now reads "node `vacate` of plan review and spec review, a `cancel:` node; writing has none", and the `writing-design.md:353-356` citation is gone.

Mechanisms taken where a (proposal) option left one open (smallest that closes the group's scenario):
- G-104 hearings: `rounds.state` gains `owed` `owner` (the latest tried round's review opens an asking case with no ruling or guard record after it), so on a resume or rerun no defense, speccer or prosecutor turn runs before `docket` asks again; writing's `stage.py state` maps it to `next` `none`. `guard` and `cap` always take state's untried round, so their answer is always a guard record (the "new review" distinction is gone). `docket`'s `summary` is true only while the round's summary file is absent, and plan review's `report` gates on `summary` as spec review's does, so a re-read case starts no second reporter.
- G-104 `cite.py`: absent plan file exits 0 with `{ "unresolved": [] }` and appends nothing; exit 2 stays only for a present file that is unreadable or unwritable.
- G-104 landing: `onto` prints `unreviewed` (latest `mended` file with no review of its n or higher whose line 1 is `Verdict: SOUND`) and counts it as `moved`; `test-head` also runs on `unreviewed`; `confirm` depends on `[red, test-head]` with `none_failed_min_one_success` and `head` bound `if_skipped: ""`, so it runs whenever `red` ran; `repair` runs `when` confirm is red or `unreviewed`; `hear` makes the group's first iteration a retry when `unreviewed`, so that mend is retested and reviewed before any juror (no juror on a green tree); `handoff` exits 1 naming an unreviewed latest mend before any "no new failure" line, and its "Rerun" line now reads "repair not run"; `mend-review` writes line 1 `Verdict: SOUND|UNSOUND`. Fixture `repair-resumed` added to the list and Order step 3.
- G-105: `rounds.state(..., first=1)` and `rounds.docket(..., first=1)`; script modes hear from 1; `stage.py` passes the round after the latest closed one.
- G-106: commit tool lists changed paths with `git status --porcelain -- <paths>`, "nothing" returns `exit=0 nothing`, one retry after a hook changed files among them; writers report "nothing" as outcome committed, commit `""`. `result` writes the patch (`git diff HEAD` plus each untracked non-ignored file as a new-file diff), then `git restore --source=HEAD --staged --worktree -- :/` and `git clean -fd -- :/` in the tree only, ignored files kept; no `git reset`, which landing's Homes forbid. New Files row and Homes row "A block's uncommitted changes".
- G-107: `vacate` sits after the group, `depends_on: [close]`, `when: "$close.output.outcome == 'vacant'"`; `close` takes `start` and prints outcome `vacant` when no ruling ends the case and `next` is vacant (an outer node cannot gate on a field of `$hearing.output`, the group's raw text, workflow-language.md:497). `until_bash` reads `$docket.output.case` into `held` and ends on `vacant`.
- G-109: `slug(path)` in `.shared/pin.py` takes the file route's old rule (lowercase, runs outside `[a-z0-9]` to `-`, trimmed), which leaves a kebab-case name unchanged. Intake's `from-file` becomes a `runtime: uv` script node, `intake/scripts/from-file.py`, so it can import it. `rounds.state` prints `slug`; plan and spec review's `open` prompts and `handoff`s read `$docket-in.output.slug` instead of deriving it (the Homes row now forbids any other derivation). `fail` also binds `$cut.output.slug`. Order: intake step 3 and spec review step 1 now need the cut design's step 1.
- G-110: the limit sentence sits in plan review's Terms "Slug"; spec review's `plan` takes `default: ""`.
- G-111: `env-check` uses `git remote get-url origin`, `git rev-parse --verify -q refs/remotes/origin/HEAD` and the config's `worktree.baseBranch`; the guard's `committed` rule reads `.git/info/exclude`, the global excludes file or the `.gitignore` files as `HEAD` commits them.
- G-113: prompts build the paths from `$docket-in.output.slug` (plan, spec review) or `$INPUTS.slug` (writing) and `$case.output.round`; spec review's adds the review file. New row R13.
- G-114: each `cite.py` run appends one JSON line `{ "unresolved": [...] }` (`[]` when resolved); a marker with no " | " has reason "no separator"; `Profile.filed` becomes `(folder, slug, round)`, the plans profile passing `rounds.cited`; `repairs` and the guard entry's count count lines listing a marker. New row S17 holds both missing rows the record named for `cite.py` (exit contract, G-104; grammar, G-114).
- G-115: each `<slug>.iter.txt` line holds the latest tried round and guard-record count; `idle` is the trailing lines matching the current pair; `IDLE = 5`. The missing "bound" row is folded into H28 and P20.
- G-116: `FENCE_CUT=1` on the coder's `fence-checks` (and so `mend-code`'s, verbatim); `.shared/red.py` gains `cut(text)`, used by `listing` and imported by `checks.py`; writing Order step 1 now needs gauntlet step 8.
- G-117: the divvy cause is newline-separated, oldest first.
- G-118: `GAUNTLET_FINAL_SUBJECT` appears in writing's config example only; only bash node `seal` reads it.
- G-108: copy-list bullets each name group and heading or node id (B07 names G-12 and G-108); new row H41 (head node list); A3 notes the deleted reason.
- G-112: the "source of the reply `show` displays" contract is one design's, so under D-01 it is a clause in A14, not a row.

D-63 grep (each ruling's fact at every place, after the edits; `grep -n` over `docs/superpowers/specs/*.md`):
- 0 hits: "written in this iteration", "unresolved <n>", "ended blocked", "git add -A -- <paths>", "only writer of the tree", "Only Clerk", "phase block reading", "checkout unmoved", "Its head (", "cannot read the block", "file name without", "from node `pin`", "or slug \"\"", "\"[cite:\" not in", "no \"[cite:\"", "never a traceback", "<round $case".
- `$pin.output.slug`: only `worktree-cut-design.md` node `tree` and node `cut` (the cut phase's own nodes), its Homes row, and contracts H16/H17 history.
- `vacate`: plan review and spec review Terms, ledger comments, node `vacate` after `close`, fixtures; `gauntlet-design.md` Why; contracts H28, H38, A15, A18 (A18 is the `cancel:` feature row, still true). `next == 'vacant'`: only contracts H29 history; the bodies gate `defend`/`file` and `screen` on `next != 'vacant'`.
- "new review": fixtures of plan and spec review ("an ask with no new review", a cap ask, still true); contracts H28 and P20 history clauses, each followed by the G-104 clause.
- `if_skipped: ""`: no intake `show` hit; the rest are other bindings, plus landing's new `confirm` head binding.
- `<slug>: final`: writing's node `seal` (default), fixtures (default), config text; contracts H33.
- `diff --quiet HEAD`: only contracts H1 history, followed by the G-111 clause. `exit 2` for `pin`: none left (the hits are fences, `cite.py`'s unreadable file, `land/scripts/pin.py`, `verify.py`).
- `-rA`: writing's config example only (G-116 (b) keeps it and cuts the output).
- `GAUNTLET_FINAL_SUBJECT`, `FENCE_CUT`, `unreviewed`, `leftover`, `Verdict: SOUND`, `slug =`: every hit is a drafted line of this dispatch.

Gates (uncommitted tree):
- `archon workflow list --json`: `"errors": []`.
- `archon validate workflows`: `Results: 4 valid, 23 with errors` (the 23-error non-pack baseline).
- Pre-commit: `filepawl check....Passed`.
- Lease-check and commit: not run (D-79: commit after the closed review's fixes).

Deviations:
- [deviation] PLAN-3 Must-be-true 1 and Task 3 say load-bearing groups are "ruled on by `/cad-decision-review`" and each round's rulings land in one commit at once; D-79 (60247c2) replaces both for round 3: the owner rules every group, and the drafted edits stay uncommitted until one closed review's high and medium fixes. Followed D-79; nothing committed.
- [deviation] G-115 (b) says "in every profile"; writing's revision profile has `iterations=False` and no `<slug>.iter.txt` in `gauntlet/revisions/`, so the idle bound is drafted for the plans and specs profiles only, and writing's idle revisions stay bounded by `stage.py`'s `stalled` and `cap`. Stated in `.shared/rounds.py`'s `docket` and contracts H28. Binding it in writing too needs a decision on where its counter lives (a Profile field naming `gauntlet/write/<slug>.iter.txt` and a defined line format for `stage.py state`).
- [deviation] D-03 amended by D-64 (carried): the spiker validation of the designs' YAML is an orchestrator dispatch after apply, not run here.
- Carried unchanged: D-60 exit bar and AC3 reading, D-13 amendment, G-42, G-27 (see `reports/plan-3.7.md`).

Open items:
- Declined shape: a resumed hearing with an unanswered `guard` ask is not made `owed` `owner` (only review-born cases are), so one defense or speccer turn can run before that guard asks again; the group's scenario names review cases only.
- Declined shape: the menders (`mend-code`, `mend-tests`) get no rule for the commit tool's new "nothing" answer; their roles commit "the paths you changed", so they do not meet it in the normal course.
- Tooling: the first batch of `plan-review-design.md` edits went through a one-off `python3` string replacement (each match asserted once); later mechanical replacements used `sed -i` (the `$pin.output.slug` swap in `gauntlet-design.md`, the ledger slug sentence in both hearings, the `until_bash` variable rename, the three planning lines, the CONTEXT.md D-line suffixes). No pack file holds new code; disclosed under CLAUDE.md 1.1.
- Contract rows touched cite the new clauses by node id or heading; their older line citations stay as the prior record (D-61 applied to every new citation, not retro-fitted to untouched cells).
- Plan review's ledger comment and `.shared/rounds.py`'s comment state `docket`'s case rules twice, as before this round; both were updated identically. `owed` `owner` has one home (plan review's ledger `state`); rounds points to it.
- Carried from `reports/plan-3.7.md`: the `/tmp/tmp.xTDZRgjxE3` scratch repository (124K) left by the writing reviewer; the D-58 juror-route fixture and `juror.md` sentence; `gauntlet-design.md` not naming `bash run.sh`; ROADMAP/PROJECT Phase 2 lines, LAND-01, RUN-14 not edited; Task 4 flags for A10 and A19.
- Uncommitted by design, not mine: `.gitignore`, `.planning/STATE.md`, `.planning/config.json`, `.planning/phases/1/reports/`, `reviews/pass2-*`.
- Previous report rotated to `reports/plan-3.7.md`.
- Process: no process left running (only foreground `archon` and `pre-commit` runs, each exited). Full suite not run: the plan is not at its last task.
