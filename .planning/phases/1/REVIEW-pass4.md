# Phase 1 review, pass 4 (convergence round 4 over the designs and the runtime model spec as committed at ae19601)

Date: 2026-11-08
Plan: `.planning/phases/1/PLAN-7.md`, Task 3 (new-finding branch), round 4 under D-98
Reviewed: the runtime model spec, the seven designs and `contracts.md` as committed at `ae19601` (the D-98 restructure, one commit), with the ruled set G-01 to G-119 (`REVIEW-pass1.md`, `REVIEW-pass2.md`, `REVIEW-pass3.md`, `RULINGS.md`; `DECISION-REVIEW.md` amendments replace a ruling where they say so).

Owner's shape answer (D-98 open item, D-97), 2026-11-08. Asked to choose the shape of the read of the remaining local defects among (1) none runs, (2) an executor hand-off check with no reviewer, (3) "One row-driven reviewer: one reviewer reads only the producer and consumer lines each section H/P row points to, never a whole design", the owner answered verbatim: "3". It ran as one `cad-reviewer` (opus) at `ae19601`.

Ids: findings are `4.NN`; groups are `G-NN` from G-120 (D-62). Mark per finding: `new`, or `matches G-NN` as the reviewer marked it. All 11 findings are open and new; none matches a ruled group (the reviewers marked each "new"; the nearest ruled groups, G-56/G-107, G-104, G-106, D-91 Q2 and D-92 Q1, are named under the finding's group).

Severity: as each reviewer gave it; the executor's own for the two candidate sources, named where it applies. 2 high, 8 medium, 1 low. Under D-60 a low finding is recorded and fixed but does not reopen a round.

Sources, four, as Task 3 names them:
- the model-spec review: one `cad-reviewer` (opus) over `runtime-model-design.md` alone, saved unchanged as `reviews/model-4.md` (M4-1 high, M4-2 medium, M4-3 medium);
- the owner-ruled local read: one row-driven `cad-reviewer` (opus), saved unchanged as `reviews/local-4.md` (L4-1 high, L4-2 to L4-5 medium);
- the graph candidates: `reviews/convergence-graph-4.md` stands (the `## Order` section of every design hashes identically at `0549df8` and at `ae19601`, no graph 5): its two candidates;
- the `## Candidates` section of `reviews/homes-4.md`: one item.

Check of anchors: every anchor was read with `sed -n` against the working tree, which equals `ae19601` for the specs (`git status --porcelain docs/superpowers/specs` prints nothing). 8 of 8 reviewer anchors hold the quoted text. The claim of each was read against its cited lines and holds: 4.01 against the docket case list at `runtime-model-design.md:58` (no clause for `owed` `ended`); 4.02 against `:36-38` (`owner` only for a case read from a review); 4.03 against `:140` (`git diff HEAD`, no `--binary`); 4.04 against `writing-design.md:442-443` and `loop-nodes.md:812-816` ("a binding directive's from: cannot read it, the loader rejects that at load"); 4.05 against `:56` (`file` is `<folder>/<slug>.<round>.txt`) and `:61` (`close` gives no form); 4.06 against `writing-design.md:437-455`; 4.07 against `plan-review-design.md:490`; 4.08 against `landing-design.md:194-218` (`pose` before `final`). Every row id cited exists in `contracts.md`. The two graph candidates were re-read against the `## Order` sections at HEAD: `gauntlet-design.md` step 3 reads "Needs steps 1, 2 and 4 and the worktree cut design's step 3" and step 4 follows it; the other holds as `convergence-graph-4.md` states.

## 1. Findings

Reviewer's note: the model-spec review (4.01 to 4.03) and the local read (4.04 to 4.08) each ran once at `ae19601`; the local reviewer read only the producer and consumer lines each section H/P row points to.

**4.01** `runtime-model-design.md:58` (also `:71-73`, `:95`, `:103`), rows H28, H52. New (G-115 ruled the idle case and G-56/G-107 put vacant ahead of every ask; no group rules what `docket` answers once owed is `ended`). High. Group G-120.
Text: "The first case that holds, in this order: `vacant` ...; each owner case ...; `unknown`; `deadlock`; `non-responsive`; `guard`; `idle`; `cap`; `none`." and "the extra iteration after an ending answer runs script nodes only".
Finding: `docket` has no rule for owed `ended`. In the iteration after an ending answer, `idle` holds (the ruling `record` wrote is already in the `<slug>.iter.txt` line `filing` writes, so round, owed, guard count and repairs equal it) or `cap` holds (iteration >= 200); `why` starts a fresh analyst and `bench` pauses on a question about a hearing that has ended. The answer is never recorded, because the loop then ends on `ended`. After every ending answer the idle case spends an agent turn and a stop on a non-issue (CLAUDE.md 1.3, 1.4), and the model spec's own line 73 is contradicted.

**4.02** `runtime-model-design.md:117` (also `:36-38`, `:58`, `:60`, `:90`), rows H53, H29. New (G-104 re-asks only the cases read from a review; this finding is about the `guard`, `idle` and `cap` asks, which are read from state). Medium. Group G-121.
Text: "`owner`: the latest tried round's review opens an asking case (an owner case, `unknown`, `deadlock` or `non-responsive`) and no ruling or guard record follows it".
Finding: an unanswered `guard` or `idle` ask that a rerun or a failure resume finds is not owed to the owner. `owed` is `owner` only for a case read from a review, so a rerun runs a fresh author and reviewer turn past the bound before the ask comes back (a guard bound overrun by one full round on every rerun; a pending `idle` ask gives the author another turn before the owner sees the analyst's reason). Tokens spent on work the sequence does not need (CLAUDE.md 1.3).

**4.03** `runtime-model-design.md:140`, row H54. New (G-106 ruled (c), save then restore, because the restore discards an agent's edits; the format of the save is not ruled). Medium. Group G-122.
Text: "`result` first writes every uncommitted change as `gauntlet/write/<slug>.leftover.<move>.patch` (`git diff HEAD`, staged and unstaged, then each untracked file not ignored as a new-file diff)".
Finding: plain `git diff HEAD` with no `--binary` emits only "Binary files a/... and b/... differ" for a binary edit, with no content. The `git restore` and `git clean -fd` that follow then delete the new binary file and revert the changed one; the patch named in the amicus case cannot restore either. The save G-106 exists to keep is lost with no error.

**4.04** `writing-design.md:442` (lines 437-443), rows H30, H28. New. High. Group G-123.
Text: "decision: { from: $LOOP_PREV.bench.output.decision, if_skipped: \"\" }" and the same for `text`, in node `record` of loop `work`.
Finding: Archon rejects a `from:` directive on `$LOOP_PREV` at load (`loop-nodes.md:812-816`: it is not a node reference, so a binding directive's `from:` cannot read it). Block `write` does not load; `gauntlet-tree` includes it, so `gauntlet-run` fails at node `tree` on every run, and `archon validate workflows` rejects it. The string form plan review uses (`decision: $LOOP_PREV.bench.output.decision`, `plan-review-design.md:327`) is the one the manual allows.

**4.05** `runtime-model-design.md:61`, rows H27, P1, P2. New (the D-98 move dropped the bare-name form that D-25/G-22 had fixed). Medium. Group G-124.
Text: "`close` (`INPUTS_START`): prints `{ outcome, file, summary }`" with no form for `file` and `summary`, against `:56` "`file` is `<folder>/<slug>.<round>.txt`"; consumers `plan-review-design.md:452-453` and `spec-review-design.md:513` (`cp -n gauntlet/plans/$close.output.file ...`).
Finding: the two `enter` nodes prefix the folder again, which works only for the bare `<slug>.N.txt` form that the restructure deleted from the plan and spec designs. A `rounds.py` built from the home gives `close` the same path form as `state`; `enter` then copies `gauntlet/plans/gauntlet/plans/my-task.3.txt`, exits non-zero, and plan review fails after the owner's approval; a resume repeats it. The ledger fixtures stub `close`, so none catches it.

**4.06** `writing-design.md:452` (lines 437-455; `write/scripts/stage.py` `record` at `:207`, `state` at `:149-152`), rows H8, H53, P3. New. Medium. Group G-121.
Text: "trigger_rule: none_failed_min_one_success   # a failed enter fails the iteration; a resume re-drives it" with `when: "$record.output.enter != ''"`.
Finding: writing's `enter` runs only off `$record.output.enter`, which `record` prints only in the iteration right after the owner's approve. A failure resume restarts the group at iteration 1, where the decision is "", so `record` prints enter "" and `enter` is skipped, though the comment says a resume re-drives it. `state` counts the round closed by its approve ruling, so no revision is owed and `approved/<slug>.rev<N>.txt` is never written: the divvyer, writers and reviewers get spec files without the revision the owner approved.

**4.07** `plan-review-design.md:490` (consumers `writing-design.md:119`, `:166-171`; `gauntlet-design.md:338-341`), rows H48, H8, P3. New (the D-91 Q2 amendment named `scope.py` over an entered plan revision in this Homes row only; no writing node or script carries it). Medium. Group G-125.
Text: "`plan-review/scripts/scope.py`, run by node `scope` and over an entered plan revision (writing design), its marks in `gauntlet/plans/<slug>.scope.N.txt`".
Finding: no node in writing or in `enter` runs `scope.py` over the entered revision, and writing reads a stage's plan steps only from `approved/<slug>.scope.txt`. A step an approved plan revision adds or moves is outside every stage: `stage.py cut` reports "a step outside the stage" and rejects the cut each iteration, each rejection writes a cut file so `idle` never holds, and paid divvyer turns run until `cap` asks the owner; if the divvyer drops the step, the stage seals without the step the owner approved.

**4.08** `landing-design.md:203` (lines 194-218; `show` at `:228-234`), rows H45, H32. New (the D-92 Q1 amendment, "`pose` lists `gauntlet/mend/<slug>.final.<k>.txt` for case `review`", placed the listing before the writer runs). Medium. Group G-126.
Text: "for case review gauntlet/mend/$INPUTS.slug.final.<k>.txt (k this iteration's n or, after a discuss, the latest final file), each when there is one" in `pose`, which `final` depends on.
Finding: `final` depends on `pose` and writes `final.<k>.txt` after `pose` has printed `files`, so in the iteration that runs the review the file does not exist when `pose` builds the list. The amicus briefs the owner without the review's findings, and `show` prints no final file, so the owner can choose `land` without seeing the review before landing, the gap D-92 Q1 was ruled to close. Only a later discuss lists the file.

**4.09** `gauntlet-design.md`, heading `## Order`, step 3 ("Needs steps 1, 2 and 4"), internal to gauntlet-design.md (graph candidate 1, `reviews/convergence-graph-4.md`). New with the owner-control apply. Medium (the executor's rating: a step whose stated Need is built after it; passes 2 and 3 checked "a step needing a step ordered after it, within a design" as a defect class). Group G-127.
Finding: step 4 is ordered after step 3, so a builder taking the steps in number order meets an unmet Need. Not a cycle: `G:4` needs `WC:2` and `W:7` and does not need `G:3`.

**4.10** `plan-review-design.md`, heading `## Order`, step 4, and `spec-review-design.md`, heading `## Order`, step 7, internal to plan-review-design.md and spec-review-design.md (graph candidate 2). New; the pass-2 and pass-3 graphs carried the same omission. Low (the executor's rating: `G:1` orders both blocks behind `I:3`, and a builder meets it at the first `archon validate workflows`, which both steps run). Group G-127.
Finding: step 4 builds `plan-review/scripts/guard.ts` and step 7 builds `spec-review/scripts/guard.ts`, which import `requireIgnored` from `.shared/working-folder.ts` (Homes row "Working-folder check", naming the intake design). Neither step lists that file's step (`I:3`) in its Needs, whereas `WC:2`, `L:5` and `G:1` do.

**4.11** `runtime-model-design.md`, heading "Commit model", What a failed or uncommitted block leaves; `landing-design.md`, module `mend/mend.yaml`, node `pose`; `writing-design.md`, `write/scripts/stage.py` `result`, rows H54, H32. New (`homes-4.md` `## Candidates` item 1, not ruled; D-68 rules writing's blocks only). Medium (the executor's rating: two homes' copies state different behaviour for the same state, an uncommitted tree after a failed commit, with no reviewer scenario and no row; put to the owner so none reaches a build as a silent split, D-60). Group G-128.
Text: writing's `result` writes the block's uncommitted changes as `gauntlet/write/<slug>.leftover.<move>.patch` and restores the tree to `HEAD`; landing's `pose` counts an uncommitted mend as case `commit-failed` ("git status --porcelain not empty, gauntlet/ excluded") and leaves the tree as it is; the mend never resets or discards a commit. The home, "Commit model", states both behaviours as they are.
Finding: the same state is handled two ways: writing saves and restores, the mend leaves the edits in the tree, so the next rework starts on a dirty tree and its commit mixes the old edits with the new. No contract row names a mend's uncommitted-edit handling.

## 2. Groups

Each group is one root cause (D-62). "Members" lists its findings, "Where" every design line the findings cite, "Statement" the cause with a scenario, "Options" each value; option (a) is the designs' current text, and an option marked (proposal) is offered for the ruling to accept or replace, not a value any design gives. Severity is the highest of the members'. "Route": load-bearing (a D-NN line in CONTEXT.md from D-99, reviewed under D-05) when the ruling changes a `contracts.md` row a later phase builds against or contradicts a PROJECT, ROADMAP or REQUIREMENTS line; the ask-user seam otherwise. Each 4.NN id is in exactly one group (11 of 11). Every ruling is applied under D-61 (the fact's one home, a pointer by heading or node id elsewhere) and grepped under D-63.

**G-120** The docket has no case for a hearing that has ended (rows H28, H52). High.
Members: 4.01.
Where: `runtime-model-design.md:58`, `:71-73`, `:95`, `:103`; `plan-review-design.md:323-334`, `:394-434`; `spec-review-design.md:472-482`.
Statement: after the owner's ending answer the loop runs one more iteration (script nodes only, `record` then `filing`), and in it `docket` reads state with owed `ended` and no clause for it. `idle` or `cap` holds, `why` starts an analyst and `bench` asks about a hearing that is already over.
Options: (a) as written; (b) (proposal) `docket` answers `none`, nothing asked, when `owed` is `ended`, listed with `vacant` ahead of every owner case and every bound; the agent nodes already skip on `ended`, so the extra iteration asks and spends nothing.
Route: load-bearing (H28 case order, H52 loop shape).
Ruling: (b) (owner, 2026-11-08, through the ask-user seam, asked once with all nine groups and answered verbatim "All as recommended"). D-99. Applied in `runtime-model-design.md` "Ledger" (`docket`).

**G-121** A pending ask or an approve ruling is not read from the files on a resume or a rerun (owner's G-104 (b) root; rows H53, H29, H8, P3). Medium.
Members: 4.02, 4.06.
Where: `runtime-model-design.md:36-38`, `:58`, `:60`, `:90`, `:111`, `:117`, `:123-124`; `plan-review-design.md:324`, `:336-338`; `writing-design.md:437-455`, `:149-152`, `:207`.
Statement: G-104 ruled that what is owed is read from the files alone, for owner cases read from a review. Two cases escaped it: an unanswered `guard`, `idle` or `cap` ask, which `owed` does not report as `owner` (4.02), and writing's `enter`, which runs only off the previous iteration's decision (4.06), so a failure resume skips it. Scenario: the owner approves round 4; `enter` fails; the resume restarts at iteration 1 and nothing writes `approved/<slug>.rev1.txt`.
Options: (a) as written; (b) (proposal) `owed` is `owner` also when `state` finds `guard`, `idle` or `cap` unanswered (a guard record is absent after the bound's untried round), so the ask is read again; and writing's `enter` runs off the ruling on file, as plan and spec review's `enter` does (an approve ruling with no revision file); (c) (proposal) only 4.06 is fixed (`enter` off the ruling on file); a rerun past a guard or idle bound accepts the one extra round.
Route: load-bearing (H29 owed values, H53 rule).
Ruling: (b) (owner, 2026-11-08, through the ask-user seam, asked once with all nine groups and answered verbatim "All as recommended"). D-100. Applied in `runtime-model-design.md` "Hearing state" (`owed`) and "Resume and rerun", and `writing-design.md` (`stage.py record`, node `enter`).

**G-122** The leftover patch does not hold binary content (row H54). Medium.
Members: 4.03.
Where: `runtime-model-design.md:140`; `RULINGS.md` G-106 (c).
Statement: `git diff HEAD` writes no content for a binary edit, and `git clean -fd` plus the restore then delete it. Scenario: a test block adds `tests/fixtures/logo.png`; the commit fails on a hook; the patch holds the stanza "Binary files differ"; the PNG is gone.
Options: (a) as written; (b) (proposal) `git diff --binary HEAD` and `--binary` on each new-file diff, so `git apply` restores the content; (c) (proposal) as (b), and `result` refuses to restore (the block ends `commit-failed` with the tree left as it is) when the patch cannot be written.
Route: ask-user seam (internal to the Commit model; H54's contract names the patch, not its format).
Ruling: (b) (owner, 2026-11-08, through the ask-user seam, asked once with all nine groups and answered verbatim "All as recommended"). Ask-user seam, no D-NN. Applied in `runtime-model-design.md` "Commit model" (`git diff --binary HEAD`).

**G-123** Writing's `record` reads `$LOOP_PREV` with a binding directive (rows H30, H28). High.
Members: 4.04.
Where: `writing-design.md:437-443`, `plan-review-design.md:327`; `loop-nodes.md:812-816`.
Statement: `from:` cannot read `$LOOP_PREV`; the loader rejects it. `write/write.yaml` fails to load, so `gauntlet-tree` and `gauntlet-run` do.
Options: (a) as written (a load error); (b) writing's `record` binds `decision` and `text` in the string form, `decision: $LOOP_PREV.bench.output.decision`, as plan review's `record` does (`''` on iteration 1, as the manual states).
Route: ask-user seam (internal to writing; H30's output fields stay).
Ruling: (b) (owner, 2026-11-08, through the ask-user seam, asked once with all nine groups and answered verbatim "All as recommended"). Ask-user seam, no D-NN. Applied in `writing-design.md` (node `record`, string form).

**G-124** The form of `close`'s `file` and `summary` dropped by the restructure (rows H27, P1, P2). Medium.
Members: 4.05.
Where: `runtime-model-design.md:56`, `:61`; `spec-review-design.md:87`, `:513`; `plan-review-design.md:452-453`.
Statement: `state`'s `file` is `<folder>/<slug>.<round>.txt`; `close` gives `file` and `summary` with no form, and the `enter` consumers prefix the folder again. Scenario: a builder gives `close` the same form as `state`; the `cp` source is missing; plan review fails after the approval.
Options: (a) as written; (b) (proposal) the home states `close`'s `file` and `summary` as the bare `<slug>.N.txt` and `<slug>-summary.N.md`, as the consumers use them; (c) (proposal) the home states them in `state`'s path form (`<folder>/...`), and both `enter` nodes drop the folder prefix.
Route: load-bearing (H27 field form).
Ruling: (b) (owner, 2026-11-08, through the ask-user seam, asked once with all nine groups and answered verbatim "All as recommended"). D-101. Applied in `runtime-model-design.md` "Ledger" (`close`).

**G-125** `scope.py` over an entered plan revision is named but not wired (rows H48, H8, P3). Medium.
Members: 4.07.
Where: `plan-review-design.md:490`; `gauntlet-design.md:338-341`; `writing-design.md:119`, `:159-171`, `:445-448`; `landing-design.md:217`; `RULINGS.md` D-91 Q2.
Statement: the Homes row says `scope.py` runs over an entered plan revision, but no node runs it, and writing's stage cut reads `approved/<slug>.scope.txt` only. Scenario: the owner approves a plan revision adding step 6 under Stage 1; no scope run; `stage.py cut` rejects the cut that carries step 6 on every divvy until `cap`.
Options: (a) as written; (b) (proposal) writing's `enter` (the gauntlet design's node) runs `scope.py` over the entered plan revision and copies its marks to `approved/<slug>.scope.txt` (or `.rev<N>.scope.txt`), and `stage.py` reads the latest; (c) (proposal) the amendment goes: no marks for an entered plan revision (the D-91 Q2 original), and a step an approved plan revision adds is not cut by the stage chain.
Route: load-bearing (H48 consumer, H8 node; a path under (b)).
Ruling: (b) (owner, 2026-11-08, through the ask-user seam, asked once with all nine groups and answered verbatim "All as recommended"). D-102. Applied in `plan-review-design.md` (`scope.py`, Homes row), `writing-design.md` (`stage.py`, Files in `gauntlet/write/`, divvyer inputs, `## Order` step 3) and `landing-design.md` (node `final`).

**G-126** `pose` lists the review before landing before `final` writes it (rows H45, H32). Medium.
Members: 4.08.
Where: `landing-design.md:194-211`, `:220-234`; `RULINGS.md` D-92 Q1.
Statement: `final` depends on `pose`; `pose` lists `final.<k>.txt` for case `review` "each when there is one", so on the first briefing the file is absent. The owner can land without seeing the review.
Options: (a) as written; (b) (proposal) node `final` stays and the file list moves to the node after it: `ask`'s amicus reads `final.<k>.txt` through a `files` that node `final`'s successor completes (or `pose` splits into `pose` before and `files` after `final`); (c) (proposal) `show` prints the final file, and the amicus's files drop the entry.
Route: load-bearing (H45 order, H32 node list).
Ruling: (b) (owner, 2026-11-08, through the ask-user seam, asked once with all nine groups and answered verbatim "All as recommended"). D-103. Applied in `landing-design.md` (new node `files` after `final`, `pose` and `amicus`) and `contracts.md` H32.

**G-127** A step names a Need ordered after it, and two blocks omit an import (build orders; internal to gauntlet-design.md, plan-review-design.md and spec-review-design.md). Medium.
Members: 4.09, 4.10 (the last low).
Where: `gauntlet-design.md` `## Order` steps 3 and 4; `plan-review-design.md` `## Order` step 4; `spec-review-design.md` `## Order` step 7; `reviews/convergence-graph-4.md`.
Statement: gauntlet step 3 needs step 4, which is ordered after it; the plan and spec review `guard.ts` steps omit the intake design's `.shared/working-folder.ts` from their Needs.
Options: (a) as written; (b) (proposal) the gauntlet design moves the `gauntlet-tree.yaml` writing step ahead of the stage chain (renumbering and the pointers to its step numbers) or rewords step 3 to name the worktree cut design's step 3 and drops the step 4 clause; the two review steps name the intake design's step 3 in their Needs.
Route: ask-user seam (build orders, internal; no `contracts.md` row).
Ruling: (b) (owner, 2026-11-08, through the ask-user seam, asked once with all nine groups and answered verbatim "All as recommended"). Ask-user seam, no D-NN. Applied in `gauntlet-design.md` `## Order` (steps 3 and 4 swapped, steps 7 and 8 renumbered in their Needs), `plan-review-design.md` `## Order` step 4 and `spec-review-design.md` `## Order` step 7 (the intake design's step 3 added).

**G-128** An uncommitted mend and writing's uncommitted block are handled two ways (rows H54, H32; missing row: a mend's uncommitted edits). Medium.
Members: 4.11.
Where: `runtime-model-design.md` "Commit model"; `writing-design.md` `write/scripts/stage.py` `result`; `landing-design.md` node `pose` (case `commit-failed`).
Statement: D-68 ruled save-then-restore for writing's blocks. The mend counts an uncommitted result as case `commit-failed` and leaves the tree. Scenario: a mender fails its commit on a hook; the owner chooses `again`; the next mender commit includes the old edits.
Options: (a) as written (two behaviours, both stated in the home); (b) (proposal) the mend's uncommitted edits are saved as `gauntlet/mend/<slug>.leftover.<k>.patch` and the tree restored to the committed tip before the next mend, as writing does, the patch named in the amicus's files; (c) (proposal) the split stands as ruled, and the home gives the reason (the mender's edits are the owner's to inspect in the tree), with a `contracts.md` row for the mend's uncommitted handling.
Route: load-bearing (H54, H32; a new row).
Ruling: (b) (owner, 2026-11-08, through the ask-user seam, asked once with all nine groups and answered verbatim "All as recommended"). D-104. Applied in `runtime-model-design.md` "Commit model", `landing-design.md` node `pose` and the re-mend `copy-in` skip list, and `contracts.md` H54 (widened, no new row).

## 3. Rulings

Date: 2026-11-08. Option letters are those of section 2. Route under D-79: the owner ruled every group through the ask-user seam, asked once with all nine groups (G-120 to G-128), each with option (b) as the recommendation; no `/cad-decision-review` ran. The owner answered verbatim: "All as recommended". The ruling is therefore (b) for every group. The D-NN lines of CONTEXT.md (D-99 to D-104) stay the record of the load-bearing groups and carry the ruling. The drafted edits get one closed review before they are committed (D-79).

| Group | Route | D-NN | Ruling | Source |
|---|---|---|---|---|
| G-120 | load-bearing | D-99 | (b) | owner, "All as recommended" |
| G-121 | load-bearing | D-100 | (b) | owner, "All as recommended" |
| G-122 | ask-user seam | - | (b) | owner, "All as recommended" |
| G-123 | ask-user seam | - | (b) | owner, "All as recommended" |
| G-124 | load-bearing | D-101 | (b) | owner, "All as recommended" |
| G-125 | load-bearing | D-102 | (b) | owner, "All as recommended" |
| G-126 | load-bearing | D-103 | (b) | owner, "All as recommended" |
| G-127 | ask-user seam | - | (b) | owner, "All as recommended" |
| G-128 | load-bearing | D-104 | (b) | owner, "All as recommended" |
