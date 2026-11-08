# Phase 1 convergence record (round 4 under D-98, ended by the owner's ruling D-108)

Date: 2026-11-08
Plan: `.planning/phases/1/PLAN-7.md`, Task 5
State of the designs: the runtime model spec, the seven designs and `contracts.md` as committed at `bcdd58f`, the pass-6 round commit, which is the last ruling commit.

## Why this record does not report a clean pass

The D-60 exit bar is a pass that returns no new high or medium finding. No pass met it. Passes 4, 5 and 6 each returned new findings after the round before it was committed: 11, 3 and 6, of which 2, 0 and 1 were high and 8, 3 and 5 medium. Pass 6 is the last pass that read.

The reads stopped by the owner's ruling D-108 (2026-11-08, through the ask-user seam, asked how the loop should go on given 8, 3 and 6 new high or medium findings in passes 4 to 6). The owner chose verbatim: "Rule pass 6, then stop reads". Option text: "You rule pass 6's groups. The closed review checks those edits as usual. No pass-7 model or local read runs, and the convergence record states that the reads stopped by your ruling and why. Tasks 5 to 7 then run (convergence record, section A, approval)." So no pass-7 model-spec read and no pass-7 local read ran, and the text the pass-6 round changed (`runtime-model-design.md`, `landing-design.md`, `writing-design.md`, `plan-review-design.md`, `spec-review-design.md`, `worktree-cut-design.md`, `contracts.md`) was read only by the D-79 closed review of that round's diff (`reviews/closed-6.md`), not by a full model-spec read or a row-driven local read. This record states that gap and does not close it.

## Findings per pass

| Pass | Reads and date | New findings | High | Medium | Low | Groups | Ruled |
|---|---|---|---|---|---|---|---|
| 1 | one reviewer per design, 2026-11-05 (`REVIEW-pass1.md`) | 75 | recorded per finding | | | G-01 to G-50 | all |
| 2 | seven `cad-reviewer-medium`, plus the graph check (`REVIEW-pass2.md`) | 69 | 13 | 29 | 27 | G-51 to G-103 | all |
| 3 | seven `cad-reviewer-medium` (`REVIEW-pass3.md`) | 41 | 7 | 17 | 17 | G-104 to G-119 | all |
| 4 | model-spec review (3), row-driven local read (5), graph candidates (2), `homes-4.md` candidate (1) (`REVIEW-pass4.md`) | 11 | 2 | 8 | 1 | G-120 to G-128 | all, (b) |
| 5 | model-spec review (1), local read (2) (`REVIEW-pass5.md`) | 3 | 0 | 3 | 0 | G-129 to G-131 | all, (b) |
| 6 | model-spec review (3), local read (3) (`REVIEW-pass6.md`) | 6 | 1 | 5 | 0 | G-132 to G-137 | all, (b) |

Pass 1 severities are recorded finding by finding in `REVIEW-pass1.md` and are not totalled here. The owner-ruled group ids and rulings are in `RULINGS.md`; the D-NN lines in CONTEXT.md carry the load-bearing ones.

## The one-home grep (D-63)

The check ran over the seven designs, `runtime-model-design.md` and `contracts.md` by the tokens of `reviews/homes-4.md`.
- Task 1 ran all 42 tokens that file then held: one hit outside its home failed to name it (`writing-design.md:74`), fixed; the result was 0 on every row.
- Each ruling round after it ran the tokens of the facts it changed, with neighbouring tokens, and added a row for each (G-120 to G-137): 0 hits outside the home that fail to name it. The pass-6 round ran its 7 new tokens (the 6 groups and the closed-review fix to G-134) and 8 neighbouring tokens; the last fix added `is owed until a numbered file above it exists`, which prints only its home.
- The removed-name grep (`commands/juror.md`, `mend-juror`, `DEFECTIVE`, `gauntlet/failed`, `task-format.md`) over the eight specs prints nothing.
- Not re-run after the last round: the sweep of all 62 rows of `homes-4.md` as one pass. Only the tokens each round changed ran.

## The graph check

`reviews/convergence-graph-5.md` stands. Pass 4 derived it (no cycle, no forward need, no missing file). At pass 6 the `## Order` sections at `43cb8a4` against `19d4e1b` differed in one wording change in writing's step 1. In the pass-6 round (`19d4e1b` to `bcdd58f`) the only change inside an `## Order` section is landing's step 3, which gains the file `mend/fixtures/settled.stubs.yaml` in its own file list; no step's Needs line changed. A file added to a step that already exists adds no edge and so no cycle.

## The model-spec review

One `cad-reviewer` (opus) over `runtime-model-design.md` alone, in pass 4 (`reviews/model-4.md`, at `ae19601`: M4-1 high, M4-2 and M4-3 medium), pass 5 (`reviews/model-5.md`, at `43cb8a4`: M5-1 medium) and pass 6 (`reviews/model-6.md`, at `19d4e1b`: M6-1 to M6-3 medium). No pass-7 read ran (D-108).

## The local read, in the owner's shape

The owner's answer, "3" (`REVIEW-pass4.md` head): one row-driven reviewer that reads only the producer and consumer lines each section H and P row points to, never a whole design. It ran in pass 4 (`reviews/local-4.md`: L4-1 high, L4-2 to L4-5 medium), pass 5 (`reviews/local-5.md`: L5-1 and L5-2 medium) and pass 6 (`reviews/local-6.md`: L6-1 high, L6-2 and L6-3 medium). No pass-7 read ran (D-108).

## Pass 6, the last pass that read: each finding, its group and ruling

Every finding was ruled by the owner through the ask-user seam in one question, "All as recommended" (option (b) each). The closed review of the round's diff (D-79, `reviews/closed-6.md`) answered yes to "does it close the scenario" for all six and found one medium, on G-134, fixed in the same round inside ruled option (b).

| Finding | Source | Severity | Group | Ruling | Applied in |
|---|---|---|---|---|---|
| 6.01 | model review (`reviews/model-6.md`) | medium | G-132 (D-109) | (b) `next` is `vacant` first | `runtime-model-design.md` "Hearing state"; plan-review and spec-review fixtures |
| 6.02 | model review (`reviews/model-6.md`) | medium | G-133 | (b) the commit tool reads `-z -uall -- <listed paths>` | `runtime-model-design.md` "Commit model"; `writing-design.md` |
| 6.03 | model review (`reviews/model-6.md`) | medium | G-134 (D-110) | (b) node `settle` of the mend; closed-review fix: the patch is owed until a numbered file sits above it | `runtime-model-design.md` "Commit model"; `landing-design.md` |
| 6.04 | local read (`reviews/local-6.md`) | high | G-135 | (b) node `baseline` restores the tree | `runtime-model-design.md` "Commit model"; `worktree-cut-design.md`; `writing-design.md` Homes |
| 6.05 | local read (`reviews/local-6.md`) | medium | G-136 | (b) the direction's N is one above the highest move | `writing-design.md` |
| 6.06 | local read (`reviews/local-6.md`) | medium | G-137 | (b) with no plan the first cut's cause is `INPUTS_SPEC` and its approved revisions | `writing-design.md` |

No low finding was left in pass 6. High or medium findings without a ruled group: 0.

## State at the end

- Findings of passes 1 to 6 without a ruled group: 0. Every group G-01 to G-137 carries one owner ruling.
- The pass-6 round was closed-reviewed but not read again by a model-spec or local read, by the owner's ruling D-108. A defect in the text that round changed would surface only in a later read or in the build.
