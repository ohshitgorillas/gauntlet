---
phase: 1
plan: 6
requirements:
  - REV-01
  - REV-02
  - REV-03
  - REV-04
  - REV-05
files:
  - .planning/phases/1/
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
---

# Phase 1: Design review - Plan 6: Round-4 convergence and approval

## Goal

The seven designs under `docs/superpowers/specs/` are made consistent with each other in one converging pass, not finding by finding. A full read of the edited designs returns no unruled high or medium finding. After that, every section A verdict is closed and all seven designs are `Status: approved`, with `contracts.md` the closed reference later phases are reviewed against.

## Must be true when done

- `.planning/phases/1/REVIEW-convergence.md` records a full pass over the seven designs. It holds no high or medium finding that is not already ruled (D-60). It lists each low finding of that pass with its group and ruling. It is committed after the last ruling commit.
- Every finding in each `REVIEW-pass<k>.md` this plan writes cites a design anchor, plus either a `contracts.md` row or "internal to <design>". Each finding group carries one owner ruling, applied in one commit that edits every design it names.
- Every section A row of `contracts.md` holds one of three closed verdicts: `documented` with a `docs/reference/archon/` citation, `probed` with its PROBES.md id, or `unsupported` with the commit hash that changed each assuming design. No row is open. The three owner-control behaviours are among these rows.
- `grep -l '^Status: approved' docs/superpowers/specs/*-design.md` lists the seven designs and the owner-control design. The AC5 grep over the seven designs and the AC6 grep over the planning docs print no line. Every copy-list bullet is marked resolved.
- `archon workflow list --json` shows `"errors": []`, and `archon validate workflows` reports no error under the pack root.

## Context

- Runs after Plan 5's D-81 commit. Round 4 adds only the full read, because Plan 5 Task 5's closed review was its diff half (D-84, D-79). D-60's bar holds: a pass with no new high or medium finding converges. A low finding is recorded, ruled and fixed, and starts no new pass.
- D-79 governs every ruling round. The owner rules every group through the ask-user seam, and `/cad-decision-review` is not run. The executor drafts the edits uncommitted. One closed review reads the draft diff. The executor applies only its high and medium fixes, runs the D-63 grep and commits. D-61 and D-62 hold. D-02 holds: a ruling that contradicts a planning line edits that line in the same commit.
- CLAUDE.md 1.9 binds every Archon run here. D-64 is void (D-97): no validation run of the designed YAML.
- D-97 binds the round-4 review shape. No reviewer per design, in parallel or one at a time; no single reviewer over all seven designs; no reviewer over the round-3 changes only. No shape is ruled yet.
- The executor cannot dispatch agents or ask the owner. Tasks 1 and 2 stop for the main session by checkpoint, as PLAN-3 Task 3 did.
- Standing checks: as Plan 4's Context states. Pre-commit also runs before every commit. Testing scope: documentation only, as Plan 4 states.

## Tasks

### Task 1: Round-4 full read

- **Files:** .planning/phases/1/
- **Action:**
  - Re-derive the build-order graph over the seven `## Order` sections. Check it for dependency cycles and for steps that need a file no earlier step builds, as `reviews/convergence-graph-3.md` did. Write the graph as the next `reviews/convergence-graph-<n>.md`.
  - Return a `decision` checkpoint whose Need asks the main session to get the round-4 review shape from the owner (D-97). The checkpoint dispatches nothing, and offers none of D-97's rejected shapes.
  - The review this task runs is the shape the owner rules. Each finding is marked as matching a ruled group, or as new. Each finding carries a design anchor (file, heading or node, and line) and either a `contracts.md` row id or "internal to <design>" (D-04).
  - If the pass returned any new finding, write `REVIEW-pass<k>.md`, k being 4 for this pass. Group the new findings by root cause (D-62), starting from the next free G id. Each group carries its severity, its members' anchors and its row citations.
- **Verify:** The graph file exists and states its cycle check and its missing-file check. The review's return is saved under `reviews/`. Either `REVIEW-pass4.md` exists, and every finding in it has an anchor and a row id or "internal to" (a grep counting findings that lack one prints 0), or the pass returned no new finding and no pass file is written. Plus the standing checks.

### Task 2: Rule and apply each round's findings until a pass converges

- **Files:** .planning/phases/1/, docs/superpowers/specs/contracts.md, docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md, .planning/PROJECT.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md
- **Action:**
  - Run this task only when the latest pass wrote a `REVIEW-pass<k>.md`. With no new finding it does nothing and makes no commit.
  - Return a `decision` checkpoint whose Need asks the main session to put every group to the owner through the ask-user seam, with its options and evidence (D-79 (1)).
  - On continuation:
    1. Record each ruling verbatim under its group, and in a RULINGS.md table for pass k.
    2. Draft the edits under D-61, uncommitted. Update the `contracts.md` row when a ruling changes a contract. Edit a planning line when a ruling contradicts it.
    3. Run the D-63 grep.
    4. Return a second `decision` checkpoint for the D-79 closed review of the draft diff, with the closed questions and the 1.9 rule Plan 5 Task 5 gives.
    5. Apply only the high and medium fixes, run the D-63 grep again, and commit the round once.
  - If any group of this round held a high or medium finding, run Task 1's procedure again as pass k+1, then this task again.
  - A pass whose new findings are all low ends the loop after their rulings are committed (D-60).
- **Verify:** Each `REVIEW-pass<k>.md` group from 4 upward carries exactly one ruling line (groups without one: 0). For each round, one commit edits every design its rulings name, plus `contracts.md` and the planning files when a ruling changed them. `git show --stat <round commit>` lists them. The last pass run holds no high or medium finding. Plus pre-commit and the standing checks.

### Task 3: Write the convergence record

- **Files:** .planning/phases/1/REVIEW-convergence.md
- **Action:**
  - Write `REVIEW-convergence.md`, dated, for the pass that converged. It holds:
    - One section per design, covering all seven.
    - The graph check.
    - Each finding the pass returned, with the group and ruling it matches. A low finding of that pass appears with the group that fixed it (D-60).
  - Commit it alone, after the last ruling commit (AC3).
- **Verify:** The file holds the seven design sections and the graph check. A count of high or medium findings without a ruled group prints 0. `git log -1 --format=%ct -- .planning/phases/1/REVIEW-convergence.md` is later than `git log -1 --format=%ct -- docs/superpowers/specs/*-design.md` at its commit. Plus pre-commit and the standing checks.

### Task 4: Close the section A verdicts

- **Files:** docs/superpowers/specs/contracts.md (section "A. Assumed Archon features")
- **Action:** For each section A row whose verdict is `unsupported`, cite the hash of the commit that changed each assuming design to a documented form. Find it with `git log -S` on the replaced form; for an owner-control row from Plan 4 Task 1, the designs never held the replaced form, so cite the D-81 commit, which added the documented form (`git log -S '<documented form>' -- docs/superpowers/specs/*-design.md`). These rows include A11, A19 and any owner-control row that Plan 4 Task 1 set `unsupported`. A commit cannot name its own hash, so this edit follows the ruling commits. Leave every other row as it stands, and commit.
- **Verify:** Every section A row holds `documented` or `probed` with its citation, or `unsupported` with a hash. `grep -c 'pending probe'` on section A rows prints 0. For each hash, `git cat-file -t <hash>` prints `commit`, and `git show --stat <hash>` lists each design the row cites. Plus pre-commit and the standing checks.

### Task 5: Approve the seven designs

- **Files:** docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md
- **Action:** Change line 1 of each design from `Status: proposed.` to `Status: approved.` and nothing else, and commit. Approval follows the convergence record (REV-05), so a design approved before `REVIEW-convergence.md` is committed is a defect.
- **Verify:**
  - `grep -l '^Status: approved' docs/superpowers/specs/*-design.md | wc -l` prints 8, and `grep -l '^Status: proposed' docs/superpowers/specs/*-design.md` prints nothing.
  - `git diff HEAD~1 --stat -- docs/superpowers/specs/` shows one changed line per design, and the commit of `REVIEW-convergence.md` precedes this one.
  - `grep -nE 'commands/juror\.md|mend-juror|DEFECTIVE|gauntlet/failed|task-format\.md'` over the seven designs prints nothing. `grep -nE 'juror|DEFECTIVE|gauntlet/failed|task-format' .planning/REQUIREMENTS.md .planning/ROADMAP.md .planning/PROJECT.md` prints nothing.
  - Every bullet under "The phase designs contain these copies:" carries a resolved mark.
  - From the pack root, `archon workflow list --json` shows `"errors": []`, and `archon validate workflows` reports no error under the pack root beyond the 23 non-pack baseline errors.
  - Plus pre-commit.

## Notes

- Sequential after Plans 4 and 5, with which it shares the designs and `contracts.md`.
- This plan supersedes PLAN-3 Task 3's round-4 shape (D-84) and carries out PLAN-3 Tasks 4 and 5, which never ran. PLAN-3.md itself stays untouched.
- Task 2 is the one task that may commit more than once, once per ruling round. Its lease covers the `.planning/phases/1/` directory because the number of `REVIEW-pass<k>.md` files is unknown until the passes run.
- The graph re-derivation in Task 1 follows the roadmap's review pass and the precedent of rounds 2 and 3. Owner-control adds and removes modules in the `## Order` sections, so the earlier graphs no longer hold.
