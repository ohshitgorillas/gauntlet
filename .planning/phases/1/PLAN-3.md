---
phase: 1
plan: 3
requirements:
  - REV-02
  - REV-03
  - REV-04
  - REV-05
files:
  - docs/superpowers/specs/gauntlet-design.md
  - docs/superpowers/specs/gauntlet-intake-design.md
  - docs/superpowers/specs/plan-review-design.md
  - docs/superpowers/specs/spec-review-design.md
  - docs/superpowers/specs/worktree-cut-design.md
  - docs/superpowers/specs/writing-design.md
  - docs/superpowers/specs/landing-design.md
  - docs/superpowers/specs/contracts.md
  - .planning/phases/1/
  - .planning/PROJECT.md
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
---

# Phase 1: Design review - Plan 3: Rulings and convergence

## Goal

Every finding group carries one owner ruling applied to every design it names, a full review of the edited designs returns no unruled finding, and only then are all seven designs `Status: approved`, with `contracts.md` the closed reference later phases are reviewed against.

## Must be true when done

- Every `G-NN` group in the review record carries exactly one owner ruling, and load-bearing groups carry a D-NN line in CONTEXT.md that `/cad-decision-review` ruled on.
- For each ruling, `git log` shows one commit editing every design it names, plus `contracts.md` when it changed a contract and any PROJECT, ROADMAP or REQUIREMENTS line it contradicts.
- `.planning/phases/1/REVIEW-convergence.md` records a full pass over the seven edited designs with zero findings not already ruled, committed after the last ruling commit.
- Every section A row of `contracts.md` carries a closed verdict: `documented` or `probed` with its citation, or `unsupported` citing the commit that changed the design.
- `grep -l '^Status: approved' docs/superpowers/specs/*-design.md` lists all seven designs, and each of the 12 copy-list bullets is marked resolved with the design line or ruling that resolved it.
- `archon workflow list --json` shows `"errors": []` and `archon validate workflows` reports no error under the pack root.

## Context

- Runs after Plan 2; reads `REVIEW-pass1.md` groups and `contracts.md` row ids.
- D-05: a load-bearing ruling is written as a D-NN line in CONTEXT.md before `/cad-decision-review` runs on it; every other ruling goes through the ask-user seam and is recorded against its group. D-02: a ruling contradicting PROJECT, ROADMAP or REQUIREMENTS edits those lines in the same commit as the designs it names (first known case: `PROJECT.md` "usable standalone", ROADMAP Phase 4 criterion 1, against `gauntlet-design.md:114`, `spec-review-design.md:298`). D-06: each copy-list bullet ends marked resolved. D-10: the landing open decision is ruled like any group.
- A ruling is applied exactly as ruled: no rewording, tidying or second fix beside it in any design. Edits beyond the rulings would put unreviewed text in front of the convergence pass.
- The executor cannot dispatch agents or ask the owner; Tasks 1 and 3 stop for the main session by checkpoint, as Plan 2's Task 4 does.
- Standing checks and testing scope: as Plan 1's Context states.

## Tasks

### Task 1: Owner rulings on the pass-1 groups

- **Files:** .planning/phases/1/CONTEXT.md, .planning/phases/1/REVIEW-pass1.md
- **Action:** Propose each group's route in its group entry: load-bearing when its ruling changes a `contracts.md` row a later phase builds against (a hand-off field, node id, path, fence value, script or role resolution, or feature verdict) or contradicts a PROJECT, ROADMAP or REQUIREMENTS line (D-02); the ask-user seam otherwise (a stale count, a citation, wording inside one design). The split is planner's discretion, recorded here; the owner sees it in the asks. Write each load-bearing group as a D-NN line in CONTEXT.md's Decisions, numbered from D-11, stating the group id, the disagreement and the cited options (D-05). Then return a `decision` checkpoint whose Need asks the main session to run `/cad-decision-review` on those D-NN lines and to ask the owner through the ask-user seam for one ruling on every other group. On continuation, record each ruling verbatim under its group in `REVIEW-pass1.md`, with the route it took.
- **Verify:** Every `G-NN` group in `REVIEW-pass1.md` holds exactly one ruling line (a grep counts one per group, groups without one: 0); every group routed load-bearing has a D-NN line in CONTEXT.md naming its group id. Plus the standing checks.

### Task 2: Apply the pass-1 rulings

- **Files:** docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md, docs/superpowers/specs/contracts.md, .planning/PROJECT.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md
- **Action:** Apply every ruling to every design it names, at every occurrence its group lists. A ruling that changes a contract updates its `contracts.md` row, citations included; a ruling on an `unsupported` feature changes each assuming design to the form the ruling chose. A ruling that contradicts a PROJECT, ROADMAP or REQUIREMENTS line edits that line (D-02). Mark each copy-list bullet in `gauntlet-design.md` resolved, citing the design line or the group whose ruling resolved it (D-06). All of it lands in one commit, so no ruling is split across commits; the message lists every group id applied. Touch a planning file only for a line a ruling contradicts.
- **Verify:** `git show --stat HEAD` lists every design, `contracts.md` and planning file the rulings name; for each group, the ruled value reads at each listed occurrence (`grep -n` in each named design) and the overruled value is gone from them; each of the 12 copy-list bullets carries a resolved mark naming a line or group. Plus the standing checks.

### Task 3: Convergence review until no unruled finding

- **Files:** .planning/phases/1/, docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md, docs/superpowers/specs/contracts.md, .planning/PROJECT.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md
- **Action:** Run a full review of the edited designs, as Plan 2 ran pass 1: re-derive the build-order graph over all seven `## Order` sections, re-check the verdict of every section A row a ruling changed (an unchanged row's form and docs are unchanged), and return a `decision` checkpoint whose Need asks the main session to dispatch `cad-reviewer` at opus once per design with Plan 2 Task 4's brief plus the ruled groups, so each returned finding is marked as matching a ruled group or new. If the pass returns no new finding, write `REVIEW-convergence.md`, dated, listing each returned finding with the group and ruling it matches, and commit it. If it returns a new finding, write the pass as `REVIEW-pass<k>.md` (k from 2) with the new findings anchored, cited and grouped as Plan 2 Task 5 does, take the rulings as Task 1 does, apply them in one commit as Task 2 does, and run the pass again. This task commits once per ruling round and once for the convergence record, because the roadmap sends a new finding back to the rulings pass and AC2 needs each round's rulings in its own commit before the convergence record.
- **Verify:** `REVIEW-convergence.md` exists, holds one section per design dispatch and the graph check, and lists no finding without a ruled group (count 0); `git log -1 --format=%ct -- .planning/phases/1/REVIEW-convergence.md` is later than `git log -1 --format=%ct -- docs/superpowers/specs/*-design.md` at the time of its commit; each `REVIEW-pass<k>.md` group carries one ruling and its round's commit edits every design its rulings name. Plus the standing checks.

### Task 4: Close the inventory's feature verdicts

- **Files:** docs/superpowers/specs/contracts.md
- **Action:** For each section A row whose verdict is `unsupported`, cite the hash of the ruling commit that changed each assuming design to a documented form; a commit cannot name its own hash, so this follows the ruling commits. Leave every other row as Plans 2 and 3 set it. No row stays open.
- **Verify:** Every section A row holds `documented` or `probed` with a `docs/reference/archon/` or probe citation, or `unsupported` with a hash; for each hash, `git cat-file -t <hash>` prints `commit` and `git show --stat <hash>` lists each design the row cites. Plus the standing checks.

### Task 5: Approve the seven designs

- **Files:** docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md
- **Action:** Change line 1 of each design from `Status: proposed.` to `Status: approved.` and nothing else. Approval follows the convergence record (REV-05), so a design approved before `REVIEW-convergence.md` is committed is a defect.
- **Verify:** `grep -l '^Status: approved' docs/superpowers/specs/*-design.md | wc -l` prints 7 and `grep -l '^Status: proposed' docs/superpowers/specs/*-design.md` prints nothing; `git diff HEAD~1 --stat -- docs/superpowers/specs/` shows one changed line per design; `REVIEW-convergence.md`'s commit precedes this one. From the pack root `archon workflow list --json` shows `"errors": []` and `archon validate workflows` reports no error under the pack root beyond the 23-error non-pack baseline. Plus pre-commit.

## Notes

- Runs after Plans 1 and 2 and shares `contracts.md` with both, so execution is sequential.
- Task 3 is the one task that commits more than once, by design: each ruling round's commit must precede the convergence record (AC2, AC3). Its lease is the `.planning/phases/1/` directory because the number of `REVIEW-pass<k>.md` files is unknown until the passes run.
- Tasks 1 and 3 stop for the main session: Task 1 for `/cad-decision-review` and the ask-user seam, Task 3 for the `cad-reviewer` dispatches and, on a new finding, for its rulings.
