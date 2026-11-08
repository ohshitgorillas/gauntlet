---
phase: 1
plan: 5
requirements:
  - REV-02
  - REV-04
files:
  - docs/superpowers/specs/contracts.md
  - docs/superpowers/specs/gauntlet-design.md
  - docs/superpowers/specs/gauntlet-intake-design.md
  - docs/superpowers/specs/plan-review-design.md
  - docs/superpowers/specs/spec-review-design.md
  - docs/superpowers/specs/worktree-cut-design.md
  - docs/superpowers/specs/writing-design.md
  - docs/superpowers/specs/landing-design.md
  - .planning/PROJECT.md
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
  - .planning/phases/1/RULINGS.md
  - .planning/phases/1/PROBES.md
  - .planning/phases/1/reviews/
---

# Phase 1: Design review - Plan 5: Land the owner-control ruling

## Goal

The seven designs under `docs/superpowers/specs/` are made consistent with each other in one converging pass, not finding by finding. This plan completes Plan 4's draft with the contract rows, the planning lines and the RULINGS records. It has one closed review read the whole draft (D-79), then lands the owner-control ruling in a single commit (D-81).

## Must be true when done

- `git show --stat HEAD` is one commit. It holds the seven designs, `contracts.md`, the PROJECT, ROADMAP and REQUIREMENTS lines the ruling contradicts, and `RULINGS.md`. Its message names D-81 and every decision it applies (D-80 to D-96).
- `contracts.md` holds rows for the amicus, the item file, the direction file, the review before landing, stages, the escalation-rules key, the two scope checks and the back-to-planning command, and each row cites every design that names it. Rows R7 and R8 are gone. Every other affected row states the owner-control value.
- `grep -nE 'commands/juror\.md|mend-juror|DEFECTIVE|gauntlet/failed|task-format\.md'` over the seven designs prints no line. `grep -nE 'juror|DEFECTIVE|gauntlet/failed|task-format' .planning/REQUIREMENTS.md .planning/ROADMAP.md .planning/PROJECT.md` also prints no line.
- `RULINGS.md` marks every round 1 to 3 group that the owner-control design rewrites as moot, citing owner-control. It records each ruling D-85 voids or carries against its group. It also records the closed review's answer for each decision.

## Context

- Plan 4 must have run first. Its edits sit uncommitted in the working tree, and they are this plan's input. Check them before any edit: `git log -1` must be the commit Plan 4 started from, and `git diff --stat` must list the seven designs and `contracts.md`.
- D-79 carries over (D-84). Draft every edit and leave it uncommitted. One closed review then reads the whole draft diff, and only its high and medium fixes are applied. The D-63 grep runs before that review and again before the commit. The commit holds the whole ruling (D-81, D-02). No task commits before Task 6.
- D-61 holds for every edit, as in Plan 4. A ruling is applied exactly as ruled.
- Standing checks: as Plan 4's Context states. Pre-commit (`.venv/bin/pre-commit run -c .pre-commit/config.yaml --all-files`) also runs before Task 6's commit. Testing scope: documentation only, as Plan 4 states.

## Tasks

### Task 1: Carry the drafted designs into contracts.md

- **Files:** docs/superpowers/specs/contracts.md
- **Action:**
  - Apply D-82. Remove rows R7 and R8, and never reuse their ids.
  - Rewrite H3, H13, H14, H21, H24, H25, H31, H34, P6, S8 and S12 to the drafted designs' values.
  - Rewrite every other row that the drafts change. Each one fits one of these patterns:
    - D-89's rows H24, H25, F1 to F3, P1 and P2.
    - D-90's rows H9, H16, H19, H36, P6, F4 and F9.
    - Any row that names the juror, `mend-juror`, `DEFECTIVE`, `gauntlet/failed`, `task-format`, the task path, the writing analyst or `stalled`.
  - Add new rows at each section's next free id for each contract D-82 and D-83 name: the amicus (with its D-95 home), the item file (name, format, location, hand-off), the direction file (form, and how the next pass reads it), the review before landing (its placement), the stages (the unrolled form and its bound), the repo-wide escalation key with its carrier, the plan-step grammar with item ids and its check script, the diff-against-block-`paths` mark, the stage marker, and the back-to-planning command.
  - Each row cites every design that names it, by heading or node id (D-61). A row names only what the drafted designs state, so a value no design states is a gap in Plan 4's draft. Close such a gap in its home design, in the D-61 form, and list it in the task report.
- **Verify:** `grep -nE '^\| R[78] ' docs/superpowers/specs/contracts.md` prints nothing. One row exists for each of the ten new contracts. `grep -nE 'juror|DEFECTIVE|gauntlet/failed|task-format' docs/superpowers/specs/contracts.md` prints nothing. Pick five rewritten rows and three new rows: each design they cite holds the cited heading or node and states the row's value. Plus the standing checks.

### Task 2: Edit the planning lines the ruling contradicts

- **Files:** .planning/REQUIREMENTS.md, .planning/ROADMAP.md, .planning/PROJECT.md
- **Action:**
  - Apply D-96 and D-02. Reword the following to the drafted designs: REQUIREMENTS RUN-01, RUN-07, RUN-08, RUN-09 (reworded to an owner-triggered revision), RUN-11, RUN-12, RUN-13, ROLE-01 and ROLE-02; ROADMAP's phase 3 to 7 lines that name the juror, `DEFECTIVE`, `fail`, `kill`, `gauntlet/failed/` or the task format; and `PROJECT.md`'s Active lines for the cut and writing and its Out of Scope lines on sending the run back and on `fail`/`kill`.
  - AC6's grep also covers `PROJECT.md`'s shared-layer line, which names `.shared/task-format.md`. It also covers any line that names the removed nodes `fail` and `kill`, such as the REQUIREMENTS Out of Scope row. Edit those lines too, since the same ruling contradicts them (D-02), and name each one in the report.
  - D-02 also covers every other line the drafted designs contradict, whether or not AC6's grep hits it. Known cases: ROADMAP Phase 4 criterion 1 and Phase 5 criterion 1 (`gauntlet/tasks/<slug>.md` in place of the item file, D-86, D-90); the REQUIREMENTS Out of Scope row "A phase re-running an earlier phase", twin of `PROJECT.md:40` (back to planning); and RUN-10 if Plan 4 Task 7 ruled that each stage seals with its own subject. Read the three files against the drafted designs and edit each such line. Name each one in the report with the decision that contradicts it.
  - Touch no other line.
- **Verify:** `grep -nE 'juror|DEFECTIVE|gauntlet/failed|task-format' .planning/REQUIREMENTS.md .planning/ROADMAP.md .planning/PROJECT.md` prints nothing. `grep -nE 'gauntlet/tasks|re-running an earlier phase' .planning/REQUIREMENTS.md .planning/ROADMAP.md .planning/PROJECT.md`: every line it prints agrees with the drafted designs. `git diff -U0 -- .planning/REQUIREMENTS.md .planning/ROADMAP.md .planning/PROJECT.md` changes only the lines named in this Action. Plus the standing checks.

### Task 3: Record the moot, void and carried rulings

- **Files:** .planning/phases/1/RULINGS.md
- **Action:**
  - Apply D-81. Read every group of the pass-1, pass-2 and pass-3 tables. Mark as moot each group whose subject the owner-control design rewrites. This covers at least G-05, G-14, G-16, G-19, G-36, G-45, G-51, G-52, G-67, G-73, G-75, G-87, G-93, G-106, G-112 and G-117. Each mark cites owner-control. Do not re-rule any group.
  - Apply D-85. Against each group, record which rulings are void: D-22, D-37, D-38, D-39, D-58's after-application amendment, D-59's juror half, D-76's second half, D-77, and the `gauntlet/failed/` clause of D-13 and D-43.
  - Record which rulings are carried and re-anchored: D-47 and D-48, D-57, D-58, D-68 and D-78.
  - Record that D-19 and D-23 were already superseded, that D-49 and D-50 fall with the intake rewrite, and that D-20 and D-21 stand.
  - Add one section heading for the owner-control ruling, in the form of the existing pass tables.
- **Verify:** `grep -c` for each of the 16 named group ids in the owner-control section finds each one marked moot. Each D-NN id that D-85 names appears in that section with its status. `git diff -- .planning/phases/1/RULINGS.md` adds lines and changes no ruling text of rounds 1 to 3. Plus the standing checks.

### Task 4: Grep each decision at every place its fact appears

- **Files:** docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md, docs/superpowers/specs/contracts.md
- **Action:**
  - Apply D-63 before any reviewer runs. For each decision D-86 to D-95, grep the seven designs and `contracts.md` for the names the decision removes, the names it introduces, and the home it settles.
  - Fix in its D-61 form each place where a removed name survives, or where a design restates a fact that has another home.
  - Fix each pointer that names a home which does not hold the fact.
  - Record each grep and each fix in the task report.
- **Verify:** The report lists one grep per decision with its hit count after the fixes. `grep -nE 'commands/juror\.md|mend-juror|DEFECTIVE|gauntlet/failed|task-format\.md' docs/superpowers/specs/{gauntlet,gauntlet-intake,plan-review,spec-review,worktree-cut,writing,landing}-design.md` prints nothing. Plus the standing checks.

### Task 5: Closed review of the whole draft

- **Files:** docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md, docs/superpowers/specs/contracts.md, .planning/REQUIREMENTS.md, .planning/ROADMAP.md, .planning/PROJECT.md, .planning/phases/1/RULINGS.md, .planning/phases/1/reviews/
- **Action:**
  - Return a `decision` checkpoint whose Need asks the main session to run D-79 step (3). This is the diff half of round 4 (D-84). One closed review reads `git diff HEAD` of the whole draft.
  - Because the diff is large, it splits into parallel reviewers, one per design. `contracts.md` and the planning lines go with the designs they cite.
  - Each reviewer answers, per decision D-80 to D-96 that touches its design, two closed questions:
    - Does the edit close what the decision states? Answer yes, or no with the scenario.
    - Does it introduce a new high or medium defect? Name each one with a concrete failure scenario.
  - The reviewer writes no amendment, proposes no alternative and reports no low finding. Where a fix is needed, it names the smallest edit, a deletion before an addition.
  - The brief carries CLAUDE.md 1.9: no Archon experiment without the owner's approval of that run.
  - On continuation, apply only the high and medium fixes, in the D-61 form. Record the review under a "D-79 review of the owner-control draft" section in RULINGS.md, in the form of the existing "D-79 review of the pass-3 drafts" section: each answer, and each fix applied or why none was needed. Save each reviewer's return under `.planning/phases/1/reviews/`.
- **Verify:** RULINGS.md holds the review section, with one answer line per decision per reviewed design and no `no` answer left without an applied fix. For each fix, `grep -n` in the named design shows the smallest edit the reviewer named. `git log -1 --format=%H` is still Plan 4's starting commit. Plus the standing checks.

### Task 6: Re-grep and commit the ruling

- **Files:** docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md, docs/superpowers/specs/contracts.md, .planning/REQUIREMENTS.md, .planning/ROADMAP.md, .planning/PROJECT.md, .planning/phases/1/RULINGS.md, .planning/phases/1/PROBES.md, .planning/phases/1/reviews/
- **Action:**
  - Run Task 4's D-63 greps again over the fixed draft (D-79 step (4)). Fix any hit in the D-61 form.
  - Then make the one D-81 commit. Add each path by name, never with `-A`. Include PROBES.md only when Plan 4 Task 1 recorded a probe.
  - The message names D-81 and lists the decisions applied.
  - Leave out every path this ruling does not own, and report each one left uncommitted.
- **Verify:** `git show --stat HEAD` lists the seven designs, `contracts.md`, every planning file Task 2 edited and `RULINGS.md`. `git rev-list --count <Plan 4 start>..HEAD` prints 1. `git status --porcelain -- docs/superpowers/specs .planning/PROJECT.md .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/phases/1/RULINGS.md` prints nothing. Both greps of "Must be true when done" print nothing. Pre-commit passes, and the standing checks pass.

## Notes

- Sequential: this plan runs after Plan 4 in the same working tree, on Plan 4's uncommitted draft. Plan 6 follows this plan, and all three plans share the designs and `contracts.md`.
- Deviation from CONTEXT's Plan shape directive: see Plan 4 Notes. The one-commit rule (D-81) puts the only commit of the owner-control apply here, as Task 6.
- The D-79 closed review in Task 5 is the diff half of round 4. Plan 6's round 4 therefore adds only the full read (D-84, read with D-79's "This review is the diff half of D-65"). Reading the diff twice would spend tokens on work the sequence does not need (CLAUDE.md 1.3).
- Task 2 adds `PROJECT.md`'s shared-layer line and the REQUIREMENTS Out of Scope `fail, kill` row to D-96's list. AC6's grep and D-02 require them, though D-96's line list omits them.
