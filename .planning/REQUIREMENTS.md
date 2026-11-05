# Requirements: Gauntlet

**Defined:** 2026-11-05
**Core Value:** One command lands one task on the checkout with tests that bite, and no agent ever writes outside the folders its phase allows.

## Active

Committed scope. Each maps to exactly one roadmap phase.

### Design review

- [ ] **REV-01**: Owner can read one adversarial review of the seven designs that names every cross-design inconsistency and snag, each finding anchored to a design file and line
- [ ] **REV-02**: Owner can rule on each finding and see the ruling recorded in the design it concerns
- [ ] **REV-03**: Owner can see every design at `Status: approved` before a build phase reads it
- [ ] **REV-04**: Owner can read one contract inventory, `docs/superpowers/specs/contracts.md`, naming every hand-off, path, fence value, script, role and assumed Archon feature with every design that names it, so a finding is judged against one reference and a ruling closes every occurrence at once
- [ ] **REV-05**: Owner can see that a full review pass over the edited designs returned no unruled finding before any design is approved

### Roles

- [ ] **ROLE-01**: Owner can read every role file the designs name (clerk, defense, prosecutor, reporter, screener, speccer, divvyer, juror, reviser, reviewer, test-writer, coder, mend-juror, mend-code, mend-tests, mend-review) under its workflow's `commands/`, each stating the turn protocol its design gives
- [ ] **ROLE-02**: Owner can read `.shared/task-format.md`, the task format Clerk writes to and the file route copies

### Shared layer

- [ ] **CORE-01**: A fenced agent can be confined by name patterns in `FENCE_*` entries, proven by `fence/test_files_patterns.py`
- [ ] **CORE-02**: A fenced agent cannot read, list, search or write a path under `FENCE_HIDE`, inside a readable folder included, proven by `fence/test_files_hide.py`
- [ ] **CORE-03**: A fenced writer can commit through the fence's `commit` tool under `FENCE_COMMIT`, proven by `fence/test_files_commit.py`
- [ ] **CORE-04**: A ledger can read rounds, parse verdicts and the owner's cases through `.shared/rounds.py`, proven by `.shared/tests/test_rounds.py`
- [ ] **CORE-05**: A script can decide whether a test run is red against the brief baseline through `.shared/red.py`, proven by `.shared/tests/test_red.py`
- [ ] **CORE-06**: A run in a working folder that is not ignored stops at `.shared/working-folder.ts` before any phase

### Checkout phases

- [ ] **RUN-01**: Owner can run `archon workflow run intake` with a task file or a message and get `gauntlet/tasks/<slug>.md` after approving Clerk's draft
- [ ] **RUN-02**: Owner can run plan review on a task and approve a plain-English summary after the prosecutor's rounds, or get `plan` as `""` when no plan is needed
- [ ] **RUN-03**: Owner can run spec review on a task and plan and approve the specs the arbiter admitted, or confirm that nothing is testable
- [ ] **RUN-04**: Owner can start `gauntlet-run` once and have intake, plan review and spec review run in order as included blocks, each handing off through its `handoff` node
- [ ] **RUN-05**: A steering attempt in any review round is screened by the shared `screen` workflow before a reviewer reads it

### Tree phases

- [ ] **RUN-06**: After spec review, the run cuts one worktree from the checkout's `HEAD`, copies the approved files in and records the test baseline, and the owner can inspect them in the tree
- [ ] **RUN-07**: A plan the juror rules defective ends the run at `kill`, with the ruling in the checkout's `gauntlet/failed/<slug>.txt`, readable by Clerk and hidden from every other checkout role
- [ ] **RUN-08**: In the tree, test writers write the tests from the approved specs and code writers make them pass, with a juror ruling each contested round
- [ ] **RUN-09**: A wrong plan or spec found in writing becomes an approved revision `<slug>.rev<N>.txt` without leaving the tree run
- [ ] **RUN-10**: When the tree holds uncommitted changes at the end of writing, writing ends with a commit `<slug>: final` whose body is the approved summaries, made with `git commit -F -`; a clean tree gets no final commit
- [ ] **RUN-11**: After writing, the mend rebases the tree's branch onto the checkout's `HEAD`, reruns the brief test command when the checkout moved, and repairs a red through a juror-ruled mend read by a reviewer
- [ ] **RUN-12**: Owner is asked during the mend only when the juror rules defective or the mend stalls, and can answer with guidance or leave
- [ ] **RUN-13**: Owner can see the mend's test line, the diff stat and the commit messages at landing's gate and choose land or leave
- [ ] **RUN-14**: On land, the checkout is fast-forwarded to the tree's branch, the tree's records are copied into the checkout's `gauntlet/`, and the tree and its branch are removed

### Pack health

- [ ] **PACK-01**: Every workflow fixture passes `archon workflow test`, one route per fixture, and `archon workflow list --json` and `archon validate workflows` are clean from the pack root

## v2 Requirements

Deferred. Tracked, not in the current roadmap.

### Landing

- **LAND-01**: Owner can resume a landing whose checkout moved after the mend's rebase, once the checkout is back at an ancestor of the branch (the landing design's open decision 1)

## Out of Scope

Explicit exclusions. The reason prevents scope creep later.

| Feature | Reason |
|---------|--------|
| Gauntlet pushing, opening a PR or touching a remote | Forbidden by landing's home and by `CLAUDE.md` 4.4; the owner publishes |
| A phase re-running an earlier phase | The gauntlet design forbids it; revisions happen inside writing |
| Gauntlet removing the tree or branch on fail, kill or leave | The owner inspects and removes with `archon complete <branch> --force` |
| Scaffolding that replaces an Archon feature | `CLAUDE.md` 1.1 and 1.2: a missing feature is reported to the owner |
| A phase run as a `workflow:` child (the cut's `tree` excepted) | A child run cannot reach the existing tree; phases enter by `include:` |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| REV-04 | Phase 1 | Pending |
| REV-01 | Phase 1 | Pending |
| REV-02 | Phase 1 | Pending |
| REV-03 | Phase 1 | Pending |
| REV-05 | Phase 1 | Pending |

Bare headers - `/cad-plan` seeds a row per requirement when its phase is
planned (`references/req-traceability.md`).

---
*Last updated: 2026-11-05 after /cad-adopt*
