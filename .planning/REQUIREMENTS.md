# Requirements: Gauntlet

**Defined:** 2026-11-05
**Core Value:** One command lands one task on the checkout with tests that bite, and no agent ever writes outside the folders its phase allows.

## Active

Committed scope. Each maps to exactly one roadmap phase.

### Design review

- [ ] **REV-01**: Owner can read one adversarial review of the seven designs that names every cross-design inconsistency and snag, each finding anchored to a design file and line
- [ ] **REV-02**: Owner can rule on each finding and see the ruling recorded in the design it concerns
- [ ] **REV-03**: Owner can see every design at `Status: approved` before a build phase reads it
- [ ] **REV-04**: Owner can read one contract inventory, `docs/superpowers/specs/contracts.md`, naming every hand-off, path, fence, script, role and assumed Archon feature with its one home and every design that names it, holding no value (each value lives in its home alone, D-98 (2)), so a finding is judged against one reference and a ruling closes every occurrence at once
- [ ] **REV-05**: Owner can see that round 4 as D-98 sets it (the one-home grep, the build-order graph check, the one review of `runtime-model-design.md` and the read of the remaining local defects in the shape the owner rules) ended, by a read returning no unruled finding or by the owner's ruling ending the reads (D-108), with every finding ruled before any design is approved

### Roles

- [ ] **ROLE-01**: Owner can read every role file the designs name (clerk, defense, prosecutor, reporter, screener, speccer, divvyer, reviser, reviewer, test-writer, coder, amicus, mend-code, mend-tests, mend-review, final-review) under its workflow's `commands/`, each stating the turn protocol its design gives
- [ ] **ROLE-02**: Owner can read the item schema in `intake/scripts/items.py`, the item file format Clerk works to and the file route is checked against

### Shared layer

- [ ] **CORE-01**: A fenced agent can be confined by name patterns in `FENCE_*` entries, proven by `fence/test_files_patterns.py`
- [ ] **CORE-02**: A fenced agent cannot read, list, search or write a path under `FENCE_HIDE`, inside a readable folder included, proven by `fence/test_files_hide.py`
- [ ] **CORE-03**: A fenced writer can commit through the fence's `commit` tool under `FENCE_COMMIT`, proven by `fence/test_files_commit.py`
- [ ] **CORE-04**: A ledger can read rounds, parse verdicts and the owner's cases through `.shared/rounds.py`, proven by `.shared/tests/test_rounds.py`
- [ ] **CORE-05**: A script can decide whether a test run is red against the brief baseline through `.shared/red.py`, proven by `.shared/tests/test_red.py`
- [ ] **CORE-06**: A run in a working folder that is not ignored stops at `.shared/working-folder.ts` before any phase

### Checkout phases

- [ ] **RUN-01**: Owner can run `archon workflow run intake` with an item file or a message and get `gauntlet/items/<slug>.md` after approving each item, one at a time
- [ ] **RUN-02**: Owner can run plan review on a task and approve a plain-English summary after the prosecutor's rounds, or get `plan` as `""` when no plan is needed
- [ ] **RUN-03**: Owner can run spec review on a task and plan and approve the specs the arbiter admitted, or confirm that nothing is testable
- [ ] **RUN-04**: Owner can start `gauntlet-run` once and have intake, plan review and spec review run in order as included blocks, each handing off through its `handoff` node
- [ ] **RUN-05**: A steering attempt in any review round is screened by the shared `screen` workflow before a reviewer reads it

### Tree phases

- [ ] **RUN-06**: After spec review, the run cuts one worktree per stage of the plan (one when the plan names no stage) from the checkout's `HEAD`, copies the approved files in and records the test baseline, and the owner can inspect them in the tree
- [ ] **RUN-07**: The owner's back to planning ends the run completed, not cancelled, copies the amicus record and the owner's direction into the checkout's `gauntlet/back/`, and prints the one command that starts the next plan review with both
- [ ] **RUN-08**: In the tree, test writers write the tests from the approved specs and code writers make them pass, with the amicus briefing the owner on each contested round, red or failed commit and the owner's direction binding the next pass
- [ ] **RUN-09**: When the owner's direction asks for a plan or spec revision, writing tries it and an approved revision becomes `<slug>.rev<N>.txt` without leaving the tree run
- [ ] **RUN-10**: When the tree holds uncommitted changes at the end of writing, writing ends with a commit whose first line is `<slug>: final`, or the repository's `GAUNTLET_FINAL_SUBJECT` when set (`<slug>-s<k>` in place of `<slug>` at stage `k` after the first, each stage sealing on its own), and whose body is the approved summaries, made with `git commit -F -`; a clean tree gets no final commit
- [ ] **RUN-11**: After writing, the mend rebases the tree's branch onto the checkout's `HEAD`, reruns the brief test command when the checkout moved, and repairs a red through the mend whose mender the owner's direction names, read by a reviewer
- [ ] **RUN-12**: Owner is briefed by the amicus at every mend case (a red, a mender's contest or failed commit, an unsound mend) and can discuss it, run again with a direction, go back to planning or leave
- [ ] **RUN-13**: Owner can read the review before landing, with the mend's test line, the diff stat and the commit messages, before every landing, and choose land, a rework, back to planning or leave
- [ ] **RUN-14**: On land, the checkout is fast-forwarded to the tree's branch, the tree's records are copied into the checkout's `gauntlet/`, and the tree and its branch are removed

### Pack health

- [ ] **PACK-01**: Every workflow fixture passes `archon workflow test`, one route per fixture, and `archon workflow list --json` and `archon validate workflows` are clean from the pack root

## v2 Requirements

Deferred. Tracked, not in the current roadmap.

### Landing

- **LAND-01**: When the checkout has moved past the branch the mend rebased, landing re-mends (a second tree run of block `mend` only, on a branch pinned at the first tree's tip) and meets the owner again with a new review before landing, at most 2 times; a third move stops the run, naming the move (G-45, the landing design's former open decision 1)

## Out of Scope

Explicit exclusions. The reason prevents scope creep later.

| Feature | Reason |
|---------|--------|
| Gauntlet pushing, opening a PR or touching a remote | Forbidden by landing's home and by `CLAUDE.md` 4.4; the owner publishes |
| A phase re-running an earlier phase | The gauntlet design forbids it; revisions happen inside writing when the owner's direction asks for one, and the owner's back to planning ends the run cleanly and prints the command that starts the next plan review |
| Gauntlet removing the tree or branch on leave, back to planning or any stop | The owner inspects and removes with `archon complete <branch> --force` |
| Scaffolding that replaces an Archon feature | `CLAUDE.md` 1.1 and 1.2: a missing feature is reported to the owner |
| A phase run as a `workflow:` child (the cut's `tree` excepted) | A child run cannot reach the existing tree; phases enter by `include:` |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REV-04 | Phase 1 | Complete |
| REV-01 | Phase 1 | Complete |
| REV-02 | Phase 1 | Complete |
| REV-03 | Phase 1 | Complete |
| REV-05 | Phase 1 | Complete |
| CORE-05 | Phase 2 | Pending |
| CORE-06 | Phase 4 | Pending |
| CORE-01 | Phase 2 | Pending |
| CORE-02 | Phase 2 | Pending |
| CORE-03 | Phase 2 | Pending |
| CORE-04 | Phase 2 | Pending |

Bare headers - `/cad-plan` seeds a row per requirement when its phase is
planned (`references/req-traceability.md`).

---
*Last updated: 2026-11-05 after /cad-adopt*
