---
phase: 1
plan: 6
requirements:
  - REV-02
  - REV-04
files:
  - docs/superpowers/specs/runtime-model-design.md
  - docs/superpowers/specs/gauntlet-design.md
  - docs/superpowers/specs/gauntlet-intake-design.md
  - docs/superpowers/specs/plan-review-design.md
  - docs/superpowers/specs/spec-review-design.md
  - docs/superpowers/specs/worktree-cut-design.md
  - docs/superpowers/specs/writing-design.md
  - docs/superpowers/specs/landing-design.md
  - docs/superpowers/specs/contracts.md
  - .planning/phases/1/reviews/homes-4.md
  - .planning/phases/1/CONTEXT.md
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
---

# Phase 1: Design review - Plan 6: Round-4 restructure into one home per fact

## Goal

The seven designs under `docs/superpowers/specs/` are made consistent with each other in one converging pass, not finding by finding. This plan drafts the D-98 restructure: the shared runtime model is written once in one new spec, every restated fact becomes a pointer to its one home, and `contracts.md` becomes an index of homes. Plan 7 checks the draft by grep and lands it in one commit.

## Must be true when done

- `docs/superpowers/specs/runtime-model-design.md` exists, with line 1 `Status: proposed.`. It holds the headings `## Hearing state`, `## Ledger`, `## Loop shape and bounds`, `## Resume and rerun` and `## Commit model`, and each is the one statement of its rules and values.
- Where a design held a copy of a model rule or value, it now holds a heading-level pointer to the model spec. Where two designs stated one contract, only its home states it, and the other place points to the home by file and heading or node id.
- `contracts.md` keeps every row id and holds no value. Each row names its contract, its one home, every design that names it and its seed. Section A also keeps its verdict. `grep -c 'Value each design states' docs/superpowers/specs/contracts.md` prints 0.
- `.planning/phases/1/reviews/homes-4.md` lists each moved fact with a value-bearing grep token and its home. It also lists, as candidates, each disagreement between copies that no ruling settles.
- CONTEXT AC3, ROADMAP Phase 1 pass 4 and success criterion 3, and REQUIREMENTS REV-05 state the D-98 round-4 shape. REQUIREMENTS REV-04, ROADMAP Phase 1 pass 1 and CONTEXT D-01 state `contracts.md` as the D-98 (2) index, naming each contract's one home rather than its value (D-02).
- Nothing is committed: `git log -1 --format=%H` is the commit this plan started from.

## Context

- D-98 binds this plan (owner-approved). It drafts D-98 (1), the one model spec with pointers, and D-98 (2), D-61 applied in one pass with `contracts.md` as an index of homes. Plan 7 runs the D-63 grep over this draft, makes the one D-98 commit (AC2, D-02), and then runs D-98 (3). No task here dispatches or needs a reviewer, and none of D-97's rejected shapes (1) to (4) appears anywhere.
- Pointer rule (D-61): a pointer names the home file and its heading or node id, never a line number. A module or node stays in its design with its signature, and the rule or value it implements becomes a pointer. The model spec adds no module and no `## Order` step. No task edits a step or a Needs clause of any `## Order` section, so `reviews/convergence-graph-4.md` stays valid. The owner-control design is not touched (D-80).
- Value rule: each home states the value the latest ruling set (CONTEXT D-NN lines, RULINGS.md). The executor never settles a disagreement between copies that no ruling settles. The home states the value of the design whose `## Homes` table names it as home, and `homes-4.md`'s `## Candidates` section records the disagreement: each copy's anchor and value, and its row id or "internal to <design>". Plan 7 puts the candidates to the owner.
- Token rule (D-63): each moved fact gets one line in `homes-4.md` with the fact, a `grep -F` token and the home (file and heading). The token carries the value (a constant with its value, a file-name form, a state with its condition), never a bare module or node name. The check runs `grep -nF -- '<token>'` over the eight specs and `contracts.md`. Every hit must lie in the home section, or its line must name the home file. If a token hits a line that only names the thing, choose a better token. Never record an exemption (CLAUDE.md 3.4).
- CLAUDE.md 1.9: answer Archon questions from `docs/reference/archon/`. Run no Archon experiment.
- Standing checks for every task (CLAUDE.md 1.8), from the pack root: `archon workflow list --json` shows `"errors": []`, and `archon validate workflows` reports no error under the pack root beyond the 23 non-pack `No default provider` baseline errors. Testing scope for every task: documentation only, so no automated test applies (PLAN-2 Notes). The greps in each Verify are the evidence, and testing stops there.

## Tasks

### Task 1: Write the ledger home

- **Files:** docs/superpowers/specs/runtime-model-design.md, .planning/phases/1/reviews/homes-4.md, docs/superpowers/specs/spec-review-design.md (section `.shared/rounds.py`, `plan-review/scripts/ledger.py (on the shared core)`, `spec-review/scripts/ledger.py`), docs/superpowers/specs/plan-review-design.md (Terms, `plan-review/scripts/ledger.py`), docs/superpowers/specs/writing-design.md (`write/scripts/ledger.py`, `write/scripts/stage.py`), docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/landing-design.md
- **Action:**
  - Create the model spec with `Status: proposed.` on line 1, a title, and a short `## Why` that cites D-98 and names the seven designs that point here.
  - Write `## Hearing state`. It covers which files make up one hearing in its folder, and its first round (D-67). It also covers what `owed` and `next` mean and when each value holds, the item-file hash and the move to `stale/`, and the `approved/` short-circuit.
  - Write `## Ledger`. It covers the modes `state`, `filing`, `docket`, `screen`, `record` and `close`, with their inputs and outputs. It also covers verdict parsing, the owner cases and their precedence, rulings and guard records, and `cite.py` as the one judge of citation state (D-74).
  - Take the content from the `.shared/rounds.py` comments, the plan review ledger's meaning of `state` (which `.shared/rounds.py` cites as "Same meaning as the plan review design's ledger"), the three profiles, and writing's ledger and `stage.py`.
  - Replace each copy in the seven designs with a pointer under the pointer rule. The module sections keep their dataclass shapes, function signatures and suites.
  - Create `homes-4.md` with its fact table and a `## Candidates` section. Add this task's facts and candidates.
- **Verify:** `grep -n '^## Hearing state\|^## Ledger' docs/superpowers/specs/runtime-model-design.md` prints 2 lines. Every token this task added to `homes-4.md` passes the token rule's check. Independent sweep, not drawn from `homes-4.md`: ``grep -nE '\bowed\b|stale/|approved/|\bdocket\b|`(next|filing|screen|record|close)`' docs/superpowers/specs/{gauntlet,gauntlet-intake,plan-review,spec-review,worktree-cut,writing,landing}-design.md``: each line it prints either names `runtime-model-design.md` or states a local fact that `homes-4.md` does not list as a model fact; a line restating a hearing-state or ledger rule fails the task until it becomes a pointer and its fact gets a token. `grep -c 'Same meaning as the plan review design' docs/superpowers/specs/spec-review-design.md` prints 0. `git diff -- docs/superpowers/specs` changes no line inside a `## Order` section. Plus the standing checks.

### Task 2: Write the loop and bounds home

- **Files:** docs/superpowers/specs/runtime-model-design.md, .planning/phases/1/reviews/homes-4.md, docs/superpowers/specs/plan-review-design.md (`plan-review/plan-review.yaml`), docs/superpowers/specs/spec-review-design.md (`.shared/rounds.py` constants, `spec-review/spec-review.yaml`), docs/superpowers/specs/writing-design.md (`write/write.yaml`), docs/superpowers/specs/landing-design.md (`mend/mend.yaml` group `repair`), docs/superpowers/specs/gauntlet-intake-design.md (`intake/intake.yaml`), docs/superpowers/specs/gauntlet-design.md (heading "Stages", `land/land.yaml`), docs/superpowers/specs/worktree-cut-design.md
- **Action:**
  - Write `## Loop shape and bounds`. It covers the shape of a hearing body: the terminal wait, `until_bash` and what it reads, `max_iterations`, and the agent nodes gated on `owed`. It covers the `vacant` exit and the `cancel:` node after the group (D-69). It covers the unrolled bounded form a repeated `workflow:` node takes, because a `loop_group` body rejects one (D-93; it covers `land` to `land-4` and the stages).
  - It also states every bound once: `SLOTS`, `STRETCH`, `CAP`, `IDLE` (D-75), the attempt and non-responsive counts, and the idle analyst's turn.
  - Take the content from the hearing bodies of plan review, spec review, writing, the mend and intake, and from the `.shared/rounds.py` constants. Cite each Archon form's `docs/reference/archon/` line, as `contracts.md` section A does.
  - The "Stages" heading of the gauntlet design keeps its own bound, node ids and order (its `## Homes` row "Stages"), and points here only for the unrolled-form rule.
  - Replace each copy with a pointer under the pointer rule. A YAML sketch's bound value becomes a pointer as well. Add this task's facts and candidates to `homes-4.md`.
- **Verify:** `grep -c '^## Loop shape and bounds' docs/superpowers/specs/runtime-model-design.md` prints 1. Every token this task added to `homes-4.md` passes the token rule's check, including one token for each named bound. `git diff -- docs/superpowers/specs` changes no line inside a `## Order` section. Plus the standing checks.

### Task 3: Write the resume and rerun home

- **Files:** docs/superpowers/specs/runtime-model-design.md, .planning/phases/1/reviews/homes-4.md, docs/superpowers/specs/landing-design.md (`mend/mend.yaml`, `land/land.yaml`, `gauntlet-remend/gauntlet-remend.yaml`), docs/superpowers/specs/spec-review-design.md (`.shared/rounds.py` `state` and `docket`), docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/writing-design.md (`write/scripts/stage.py`), docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/worktree-cut-design.md
- **Action:**
  - Write `## Resume and rerun`. It states what a failure resume does: the group restarts at iteration 1, citing the `docs/reference/archon/` lines that D-66 cites. It states what a rerun on an unchanged or a changed item file does.
  - It states the rule that everything owed is read from the files alone (D-66 (b)): the owner case from the latest tried round with no ruling or guard record after it; a missing plan, which is nothing to resolve; and a resumed landing, which owes repair while the latest `mended` file has no SOUND review after it.
  - It states which nodes skip on a resume or a rerun, and why: no second reporter, and a skipped hearing reads its ruling.
  - Take the content from every design's resume and rerun clauses (G-104, G-114, G-51, G-99, G-101).
  - Replace each copy with a pointer under the pointer rule. Add this task's facts and candidates to `homes-4.md`.
- **Verify:** `grep -c '^## Resume and rerun' docs/superpowers/specs/runtime-model-design.md` prints 1. Every token this task added to `homes-4.md` passes the token rule's check. `grep -niE 'resum|rerun' docs/superpowers/specs/{gauntlet,gauntlet-intake,plan-review,spec-review,worktree-cut,writing,landing}-design.md`: each line it prints either names `runtime-model-design.md` or states a local fact that `homes-4.md` does not list as a model fact. `git diff -- docs/superpowers/specs` changes no line inside a `## Order` section. Plus the standing checks.

### Task 4: Write the commit model home

- **Files:** docs/superpowers/specs/runtime-model-design.md, .planning/phases/1/reviews/homes-4.md, docs/superpowers/specs/writing-design.md (`fence/files.py (commit)`, `write/scripts/stage.py`, `write/write.yaml` nodes `result` and `seal`), docs/superpowers/specs/landing-design.md (`mend/mend.yaml` group `repair`, `land/land.yaml` node `merge`), docs/superpowers/specs/gauntlet-design.md (`## Homes` rows "The final commit" and "Commits on the tree's branch past the writers' commits and `seal`"), docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/worktree-cut-design.md
- **Action:**
  - Write `## Commit model`. It states who commits on the tree's branch and through which tool. It states the commit tool's rules (D-68): only changed paths are added, no change returns exit 0 "nothing", and a hook that changed files gets one retry. It states what a failed or uncommitted block leaves: the leftover patch `gauntlet/write/<slug>.leftover.<move>.patch`, and `result` restoring the tree to `HEAD`.
  - It also states the seal: made only on uncommitted changes, once per stage, its subject and `GAUNTLET_FINAL_SUBJECT` (D-78), and `git commit -F -`. It states the mend's commits past `seal`, and the fast-forward-only merge.
  - Take the content from writing and landing (G-106, G-116, G-86 to G-88, G-93).
  - The `fence/files.py` commit tool's module section stays in the writing design, with its signature.
  - Replace each copy with a pointer under the pointer rule. Add this task's facts and candidates to `homes-4.md`.
- **Verify:** `grep -c '^## Commit model' docs/superpowers/specs/runtime-model-design.md` prints 1. Every token this task added to `homes-4.md` passes the token rule's check, including tokens for the leftover patch name, the seal subject and `--ff-only`. `git diff -- docs/superpowers/specs` changes no line inside a `## Order` section. Plus the standing checks.

### Task 5: Make section H an index of homes

- **Files:** docs/superpowers/specs/contracts.md (preamble, section "H. Node references and hand-off fields"), .planning/phases/1/reviews/homes-4.md, docs/superpowers/specs/runtime-model-design.md, docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md
- **Action:**
  - Rewrite the preamble of `contracts.md` to the index form (D-98 (2); it contradicts D-01's value cells and fence value matrix, so Task 8 rewords D-01, REV-04 and ROADMAP pass 1 in the same commit under D-02). It lists the eight specs. A row names one contract, its one home (file, and heading or node id), every spec that names it, and its seed. It holds no value. Section A also holds a verdict, whose home is this file (D-03, AC4). Citations go by heading or node id (D-61), so the "Citation age" paragraph goes, and the "Seed" paragraph cites the copy list by its heading.
  - Rewrite section H's table to the columns `Id`, `Contract`, `Home`, `Named by` and `Seed`. Keep every row id, and never renumber or reuse one.
  - For each row, before its value leaves `contracts.md`, confirm that the home states it. Where only `contracts.md` held a value, or held a ruled value its home lacks, write it into the home first.
  - In every other design that restates the row's value, replace the copy with a pointer to the home. A row on a model fact gets the model spec heading as its home.
  - A fact restated in two or more designs with no row gets a new row at section H's next free id (AC1). Record moved facts and candidates in `homes-4.md`.
- **Verify:** Section H's header line is `| Id | Contract | Home | Named by | Seed |`. `grep -cE '^\| H[0-9]+ \|' docs/superpowers/specs/contracts.md` prints 51 or more, and `git diff` removes no H id. Every token this task added to `homes-4.md` passes the token rule's check. Pick eight H rows: each one's home holds the contract at the cited heading or node. Plus the standing checks.

### Task 6: Make sections P and F an index of homes

- **Files:** docs/superpowers/specs/contracts.md (sections "P. Paths", "F. Fences"), .planning/phases/1/reviews/homes-4.md, docs/superpowers/specs/runtime-model-design.md, docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md
- **Action:**
  - Apply Task 5's procedure to section P and section F.
  - A P row keeps the path family as its contract name. The writer and reader facts move to the home's `## Homes` row where it lacks them.
  - The F matrix becomes one row per fence file: the fence file, its home (the design section that declares its `FENCE_*` values), the specs that name it, and its seed. Every `FENCE_*` value and "how the fence receives its variables" lives in that home section alone.
  - Replace each restated fence value or path rule in another design with a pointer. Record moved facts and candidates in `homes-4.md`.
- **Verify:** The P and F header lines hold the index columns, and the F header line names no `FENCE_*` variable. `grep -cE '^\| P[0-9]+ \|'` prints 20 or more and `grep -cE '^\| F[0-9]+ \|'` prints 15 or more, with no id removed. Every token this task added to `homes-4.md` passes the token rule's check. For three fences, each `FENCE_*` value appears in its home section alone, or on lines that name the home. Plus the standing checks.

### Task 7: Make sections S, R and A an index of homes

- **Files:** docs/superpowers/specs/contracts.md (sections "S. Scripts", "R. Roles", "A. Assumed Archon features"), .planning/phases/1/reviews/homes-4.md, docs/superpowers/specs/runtime-model-design.md, docs/superpowers/specs/gauntlet-design.md, docs/superpowers/specs/gauntlet-intake-design.md, docs/superpowers/specs/plan-review-design.md, docs/superpowers/specs/spec-review-design.md, docs/superpowers/specs/worktree-cut-design.md, docs/superpowers/specs/writing-design.md, docs/superpowers/specs/landing-design.md
- **Action:**
  - Apply Task 5's procedure to sections S and R. Their resolution-rule preambles become pointers to the home of each rule.
  - Section A takes the columns `Id`, `Archon feature`, `Home`, `Named by`, `Verdict` and `Seed`. The "Form each design assumes" cells move to the home of each form. Each verdict cell is kept word for word, with its `docs/reference/archon/` citation or PROBES.md id, because `contracts.md` is the verdict's home. Plan 7 adds the hashes.
  - Record moved facts and candidates in `homes-4.md`.
- **Verify:** The S, R and A header lines hold the index columns. `git diff -U0 -- docs/superpowers/specs/contracts.md` changes no verdict text of any A row. The counts of `^\| S[0-9]+ \|`, `^\| R[0-9]+ \|` and `^\| A[0-9]+ \|` rows are 19, 14 and 32 or more, with no id removed. `grep -c 'Value each design states' docs/superpowers/specs/contracts.md` prints 0. Every token this task added to `homes-4.md` passes the token rule's check. Independent sweep over Tasks 5 to 7, not drawn from `homes-4.md`: take each value-bearing string (a constant with its value, a path form, a `FENCE_*` assignment, a state with its condition) from the lines `git diff -U0 -- docs/superpowers/specs/contracts.md` removes, and `grep -nF` it over the eight specs. Every hit lies in the row's home section or names the home file; a value with a hit elsewhere fails the task until that copy becomes a pointer and the fact gets a token in `homes-4.md`. Plus the standing checks.

### Task 8: Edit the planning lines D-98 contradicts

- **Files:** .planning/phases/1/CONTEXT.md (section "Acceptance criteria", AC3; decision line D-01), .planning/ROADMAP.md (Phase 1 goal pass 1 and pass 4, success criterion 3), .planning/REQUIREMENTS.md (REV-04, REV-05)
- **Action:**
  - Rewrite AC3, as D-98 directs. `REVIEW-convergence.md` records round 4 as D-98 sets it. That covers the one-home grep (D-63), the build-order graph check, the one review of `runtime-model-design.md`, and the read of the remaining local defects in the shape the owner rules, or the owner's ruling that none runs. It holds no high or medium finding not already ruled (D-60), and it is committed after the last ruling commit in `git log`.
  - Under D-02, reword in ROADMAP Phase 1 pass 4 ("A second full review over the edited designs") and success criterion 3, and in REV-05, only the phrase that names a full review over the edited designs, so that it matches the new AC3.
  - Under D-02, reword the three lines that promise values in `contracts.md`, which D-98 (2) contradicts: REV-04 ("naming every hand-off, path, fence value, script, role and assumed Archon feature"), ROADMAP Phase 1 pass 1 (*Inventory*, "every `FENCE_*` value per fence") and D-01 ("`FENCE_*` values as a fence x variable matrix"). Each comes to say that `contracts.md` names every such contract with its one home and every design that names it, holding no value, and that each value lives in its home alone. D-01's line notes "amended by D-98 (2)". Keep each line's other content, the REV-04 id and the D-01 id.
  - Touch no other line. No decision line other than D-01 is edited, because D-98 records its own supersession of D-84.
- **Verify:** `git diff -U0 -- .planning/phases/1/CONTEXT.md .planning/ROADMAP.md .planning/REQUIREMENTS.md` changes exactly AC3, D-01, the pass-1 and pass-4 lines, criterion 3, REV-04 and REV-05. `grep -n 'fence value\|FENCE_\*. value\|fence x variable matrix' .planning/phases/1/CONTEXT.md .planning/ROADMAP.md .planning/REQUIREMENTS.md` prints no line that places a value in `contracts.md`. `grep -n 'full review over the edited designs\|full review pass over the edited designs\|full pass over all seven edited designs' .planning/phases/1/CONTEXT.md .planning/ROADMAP.md .planning/REQUIREMENTS.md` prints nothing. Plus the standing checks.

## Notes

- Sequential. Plan 7 runs after this plan, in the same working tree, on this plan's uncommitted draft. Both plans share the designs, `contracts.md` and the planning lines. This plan lands no commit by design, because D-98 is one ruling and AC2 wants it in one commit. `execute.md` treats it as done with `risk_check_skipped`, as it treated Plan 4.
- This file replaces PLAN-6 as first planned (round-4 full read with per-design reviewers), which D-97 and D-98 supersede. That plan's report stopped at a decision checkpoint at 0 of 5 tasks. Its open items, seven reviewers and the D-64 run, are void under D-97. Its graph check, `reviews/convergence-graph-4.md`, is committed (3de6ddf), and Plan 7 carries its two candidates.
- Discretion choices: the spec is named `runtime-model-design.md`, so the `*-design.md` approval grep covers it (REV-03: build phases read it through the pointers). It holds rules and values and no module or Order step, so the build graph is unchanged. Hearing state and ledger share one task because they share their sources, the `rounds.py` core and its three profiles.
- Testing-policy deviation, as recorded once for the phase in PLAN-2 Notes: no task here builds the CI jobs (`tests`, `fixtures`, `lint`). ROADMAP Phase 2 owns that gate. CONTEXT's scope boundary leaves code and workflow files out of Phase 1. `.github/cadence/coverage-policy.json` is already tracked.
- Recalled memory informs Tasks 2, 7 and 8: D-93 (unrolled bounded form; phases/1/CONTEXT.md, phase 1), D-80 (owner-control stays an approved source, untouched; phases/1/CONTEXT.md, phase 1) and D-02 (planning lines in the ruling's commit; phases/1/CONTEXT.md, phase 1).
