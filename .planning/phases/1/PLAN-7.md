---
phase: 1
plan: 7
requirements:
  - REV-01
  - REV-02
  - REV-03
  - REV-04
  - REV-05
files:
  - .planning/phases/1/
  - docs/superpowers/specs/runtime-model-design.md
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

# Phase 1: Design review - Plan 7: Round-4 review, convergence and approval

## Goal

The seven designs under `docs/superpowers/specs/` are made consistent with each other in one converging pass, not finding by finding. This plan lands Plan 6's restructure behind its grep check, runs the round-4 review D-98 sets, and rules and applies its findings until a pass converges (D-60). It then closes the section A verdicts and approves every design and the runtime model spec.

## Must be true when done

- One commit lands the D-98 restructure: the runtime model spec, the seven designs, `contracts.md`, `reviews/homes-4.md` and the planning lines Plan 6 Task 8 edited. Each `homes-4.md` token's grep over the specs prints no line outside its home that fails to name the home.
- `REVIEW-pass4.md` holds every round-4 finding. Each finding has an anchor plus a `contracts.md` row id or "internal to <spec>". Each group carries one owner ruling, applied in one commit that edits every spec it names.
- `.planning/phases/1/REVIEW-convergence.md` records round 4 as the rewritten AC3 states, with no high or medium finding not already ruled (D-60). It is committed after the last ruling commit.
- Every section A row of `contracts.md` holds `documented` with a `docs/reference/archon/` citation, `probed` with its PROBES.md id, or `unsupported` with a commit hash. No row is open.
- `grep -l '^Status: approved' docs/superpowers/specs/*-design.md` lists nine files: the seven designs, the owner-control design and `runtime-model-design.md`. The AC5 and AC6 greps print no line.
- `archon workflow list --json` shows `"errors": []`, and `archon validate workflows` reports no error under the pack root.

## Context

- Plan 6 must run first. Its draft sits uncommitted in the working tree and is this plan's input. Before any edit, check that `git log -1` is the commit Plan 6 started from. Also check that `git status --porcelain` lists the runtime model spec (untracked), the seven designs, `contracts.md`, `reviews/homes-4.md`, CONTEXT.md, ROADMAP.md and REQUIREMENTS.md.
- D-98 binds the round-4 shape. The restructure is checked by grep (D-63), not by a reviewer. One reviewer then reads `runtime-model-design.md` alone. The read of the remaining local defects runs only in the shape the owner rules (D-98 open item, D-97). No task offers or dispatches any of D-97's rejected shapes (1) to (4): one reviewer per design, one reviewer over all seven designs, one reviewer over the round-3 changes only, or the D-64 spiker run.
- D-79 governs each ruling round. The owner rules every group through the ask-user seam. The executor drafts the edits uncommitted. One closed review reads the draft diff only and no whole design, and it is not split into parallel reviewers. The executor applies only its high and medium fixes, runs the D-63 grep and commits. D-60, D-61, D-62 and D-02 hold, and so does Plan 6's pointer rule: a ruling edits the fact's one home.
- The executor cannot dispatch agents or ask the owner. Tasks 3 and 4 stop for the main session by `decision` checkpoint, as PLAN-3 Task 3 did. CLAUDE.md 1.9 binds every Archon run, and every brief carries it.
- Standing checks and testing scope: as Plan 6's Context states. Pre-commit (`.venv/bin/pre-commit run -c .pre-commit/config.yaml --all-files`) also runs before every commit.

## Tasks

### Task 1: Run the one-home grep over the draft

- **Files:** .planning/phases/1/reviews/homes-4.md, docs/superpowers/specs/runtime-model-design.md, docs/superpowers/specs/contracts.md, docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md
- **Action:**
  - Apply D-63 to D-98 before any reviewer runs. For each line of `homes-4.md`, run its `grep -nF` token over the eight specs and `contracts.md`. Fix each hit outside the home that does not name the home, in the pointer form. Also fix each pointer that names a heading which does not exist in its target.
  - Add the post-fix result to each line: hits outside the home that do not name it, which must be 0.
  - Run the AC5 removed-name grep over the eight specs as well.
- **Verify:** Every `homes-4.md` fact line carries a result of 0. Re-running five tokens, picked across the five model headings and sections H, P and F, confirms it. For every pointer naming `runtime-model-design.md`, the quoted heading appears in that file's `grep -n '^## '`. `grep -nE 'commands/juror\.md|mend-juror|DEFECTIVE|gauntlet/failed|task-format\.md'` over the eight specs prints nothing. Plus the standing checks.

### Task 2: Commit the round-4 restructure

- **Files:** docs/superpowers/specs/runtime-model-design.md, docs/superpowers/specs/contracts.md, docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md, .planning/phases/1/reviews/homes-4.md, .planning/phases/1/CONTEXT.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md
- **Action:** Make the one D-98 commit (AC2, D-02). Add each path by name, never with `-A`. The message names D-98, D-61 and D-63. Leave out every path this ruling does not own, and report each one left uncommitted.
- **Verify:** `git rev-list --count <Plan 6 start>..HEAD` prints 1. `git show --stat HEAD` lists the thirteen paths in this task's Files. `git status --porcelain -- docs/superpowers/specs .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/phases/1/CONTEXT.md` prints nothing. Pre-commit passes, and the standing checks pass.

### Task 3: Round-4 review

- **Files:** .planning/phases/1/
- **Action:**
  - Graph: compare each design's `## Order` section at `0549df8` with HEAD, using `git show` and `perl -ne 'print if /^## Order/../^## [^O]/'`. If none changed, `reviews/convergence-graph-4.md` stands. If any changed, re-derive the graph into `reviews/convergence-graph-5.md` with its cycle check and missing-file check, as graph 4 did.
  - Return a `decision` checkpoint whose Need asks the main session for two things:
    - (a) Dispatch one `cad-reviewer` (opus) over `docs/superpowers/specs/runtime-model-design.md` alone, as a full read for high and medium defects (D-84, D-60), each with a concrete failure scenario. The brief carries: the ruled groups whose subject the model now holds (G-104 to G-107, G-114 to G-116, G-51, G-54 to G-56, G-86 to G-88, G-93, G-99, G-101), so that each finding is marked "matches ruled group G-nnn" or "new"; the `contracts.md` row ids whose home is the model spec; `docs/reference/archon/` as the source for Archon behaviour; and CLAUDE.md 1.9. Each finding gives its anchor (heading and line) and a row id or "internal to runtime-model-design.md".
    - (b) Ask the owner the shape of the read of the remaining local defects (the G-109 to G-113 and G-117 to G-119 classes) after the restructure, or whether it runs at all (D-98 open item). Offer none of D-97's shapes (1) to (4), and dispatch only what the owner rules.
  - On continuation, save each return under `reviews/`. Write `REVIEW-pass4.md` with every new finding from four sources: the model-spec review, the owner-ruled local read if one ran, the graph candidates (graph 4's two, or graph 5's), and the `## Candidates` section of `homes-4.md`.
  - Number findings `4.NN`, each with its severity, anchor, and row id or "internal to <spec>" (D-04). Group them by root cause from G-120 (D-62).
  - Record the owner's shape answer in `REVIEW-pass4.md`'s head.
- **Verify:** The reviewer's return is saved under `reviews/`. `REVIEW-pass4.md` exists, or the checkpoint answer and the graph and candidate sources show no new finding. `grep -E '^\*\*4\.[0-9]+\*\*' .planning/phases/1/REVIEW-pass4.md | grep -vcE 'rows? [A-Z][0-9]+|internal to'` prints 0 (`rows?` admits the multi-row form `rows F1-F4` that pass 3 uses). Every finding names a group. Plus the standing checks.

### Task 4: Rule and apply each round's findings until a pass converges

- **Files:** .planning/phases/1/, docs/superpowers/specs/runtime-model-design.md, docs/superpowers/specs/contracts.md, docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md, .planning/PROJECT.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md
- **Action:**
  - Run this task only when the latest pass wrote a `REVIEW-pass<k>.md`. With no new finding, it does nothing and makes no commit.
  - Return a `decision` checkpoint whose Need asks the main session to put every group to the owner through the ask-user seam, with its options and evidence (D-79 (1)).
  - On continuation:
    1. Record each ruling verbatim under its group, and in a RULINGS.md "Pass <k> rulings" table in the form of the pass-3 table.
    2. Draft the edits uncommitted, each in the fact's one home. Edit a pointer only when a heading moves. Edit `contracts.md` only when a home changes. Edit a planning line when a ruling contradicts it (D-02). Update the `homes-4.md` token of each fact whose value a ruling changed.
    3. Run the D-63 grep: each changed fact's token, as in Task 1.
    4. Return a second `decision` checkpoint for the D-79 closed review. One reviewer reads `git diff HEAD` of the draft and no whole design. For each group it answers two closed questions: does the edit close the members' scenario, and does it introduce a new high or medium defect? It writes no amendment, proposes no alternative and reports no low. The brief carries CLAUDE.md 1.9.
    5. Apply only the high and medium fixes, re-run the D-63 grep, and commit the round once, paths by name.
  - If any group of the round held a high or medium finding, run Task 3's procedure again as pass k+1, asking the owner nothing new. Its model-spec read (a) runs only if `git diff <pass k round commit>^..HEAD -- docs/superpowers/specs/runtime-model-design.md` is non-empty (pass k's reads ran at the parent of its one round commit, since Task 3 and steps 1-4 commit nothing), that is, only if a pass-k ruling changed the model spec; on unchanged text, a clean read already stands and step 4's closed review has checked the round's edits (CLAUDE.md 1.3, 1.4). The owner-ruled local read runs under the same rule over the files it read. A pass k+1 with no read to run and no new graph or candidate finding writes no `REVIEW-pass<k+1>.md` and ends the loop. Otherwise run this task again.
  - A pass whose new findings are all low ends the loop once their rulings are committed (D-60).
- **Verify:** Each `REVIEW-pass<k>.md` group from G-120 upward carries exactly one ruling line, so the count of groups without one is 0. For each round, `git show --stat <round commit>` lists every spec its rulings name, plus `contracts.md` and the planning files when a ruling changed them. The last pass run holds no high or medium finding. Plus pre-commit and the standing checks.

### Task 5: Write the convergence record

- **Files:** .planning/phases/1/REVIEW-convergence.md
- **Action:**
  - Write `REVIEW-convergence.md`, dated, for the pass that converged, with the sections the rewritten AC3 names:
    - the one-home grep and its result;
    - the graph check;
    - the model-spec review;
    - the local read in the owner's shape, or the owner's ruling that none ran;
    - each finding of that pass with its group and ruling, a low finding listed with the group that fixed it (D-60).
  - Commit it alone, after the last ruling commit (AC3).
- **Verify:** The file holds those sections. A count of high or medium findings without a ruled group prints 0. Run `git merge-base --is-ancestor $(git log -1 --format=%H -- docs/superpowers/specs/) $(git log -1 --format=%H -- .planning/phases/1/REVIEW-convergence.md)`: it exits 0, and the two hashes differ. Plus pre-commit and the standing checks.

### Task 6: Close the section A verdicts

- **Files:** docs/superpowers/specs/contracts.md (section "A. Assumed Archon features")
- **Action:**
  - For each section A row whose verdict is `unsupported` (today A11 and A19; re-check with grep), replace "(hash cited at close)" with the hash of the commit that changed each assuming design to the documented form. Find the hash with `git log -S` on the replaced form.
  - A commit cannot name its own hash, so this edit follows the ruling commits. Leave every other row as it stands, and commit.
- **Verify:** Every section A verdict cell holds `documented` or `probed` with its citation, or `unsupported` with a hash. `grep -c 'pending probe\|hash cited at close'` over section A rows prints 0. For each hash, `git cat-file -t <hash>` prints `commit`, and `git show --stat <hash>` lists each design the row cites. Plus pre-commit and the standing checks.

### Task 7: Approve the designs and the runtime model spec

- **Files:** docs/superpowers/specs/runtime-model-design.md, docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md
- **Action:** Change line 1 of each of the eight files from `Status: proposed.` to `Status: approved.`, change nothing else, and commit. Approval follows the convergence record (REV-05). A file approved before `REVIEW-convergence.md` is committed is a defect.
- **Verify:**
  - `grep -l '^Status: approved' docs/superpowers/specs/*-design.md | wc -l` prints 9, and `grep -l '^Status: proposed' docs/superpowers/specs/*-design.md` prints nothing.
  - `git diff HEAD~1 --stat -- docs/superpowers/specs/` shows one changed line per file, and the commit of `REVIEW-convergence.md` precedes this one.
  - `grep -nE 'commands/juror\.md|mend-juror|DEFECTIVE|gauntlet/failed|task-format\.md'` over the eight files prints nothing, and `grep -nE 'juror|DEFECTIVE|gauntlet/failed|task-format' .planning/REQUIREMENTS.md .planning/ROADMAP.md .planning/PROJECT.md` prints nothing.
  - Every bullet under the gauntlet design's copy list ("The copies the phase designs once held, each resolved") carries its resolving ruling or line.
  - From the pack root, `archon workflow list --json` shows `"errors": []`, and `archon validate workflows` reports no error under the pack root beyond the 23 non-pack baseline errors. Plus pre-commit.

## Notes

- Sequential after Plan 6, whose uncommitted draft it lands. It shares the specs, `contracts.md` and the planning lines with Plan 6.
- This plan carries out the work of PLAN-6 as first planned (its Tasks 2 to 5) under D-98's shape in place of the per-design full read, and PLAN-3 Tasks 4 and 5, which never ran. PLAN-3.md stays untouched.
- Task 4 is the only task that may commit more than once, once per ruling round. Its lease covers `.planning/phases/1/` because the number of `REVIEW-pass<k>.md` files is unknown until the passes run.
- Discretion choice: D-79 lets the closed review split into parallel reviewers by group when the diff is large. This plan always uses one reviewer over the diff, because D-97 rejects parallel reviewers as the cause of divergence.
