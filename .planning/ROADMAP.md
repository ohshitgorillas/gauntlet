# Roadmap: Gauntlet

## Overview

Nothing is built past the fence and the arbiter, and every design is still proposed, so the journey starts with the review the owner asked for: the seven designs tried adversarially against each other, every finding ruled on, every design approved. Only then does code follow, in dependency order: the test gate and the shared Python and TypeScript layer every phase imports; the role files, which depend on nothing but the approved designs; the three checkout phases joined under `gauntlet-run`'s head; the worktree cut and the tree run; writing in the tree; and last the mend and the landing, which close the loop from idea to landed commit. Each phase past the first leaves the pack loadable by Archon and its fixtures green.

## Phases

- [ ] **Phase 1: Design review** - the seven designs reviewed adversarially for cross-design consistency and snags, findings ruled on, designs approved
- [ ] **Phase 2: Test gate and shared layer** - the CI gate the policy requires, plus the fence extensions and `.shared/` cores every phase imports
- [ ] **Phase 3: Roles** - every role file the designs name, and the task format
- [ ] **Phase 4: Checkout phases** - intake, plan review, spec review and the shared screen, standalone and as blocks of `gauntlet-run`
- [ ] **Phase 5: Worktree cut and tree run** - the task reaches a worktree with its approved files and baseline; a defective plan ends the run
- [ ] **Phase 6: Writing** - tests then code in the tree, juror rulings, approved revisions, the sealed final commit
- [ ] **Phase 7: Mend and landing** - rebase and repair in the tree, the owner's gate, ff-only merge, record copy, tree removal

## Phase Details

### Phase 1: Design review
**Goal:** The seven designs under `docs/superpowers/specs/` are made consistent with each other in one converging pass, not finding by finding. Four passes, in order, none skipped:

1. *Inventory.* One table of every cross-design contract: each phase's hand-off fields, every node id another design depends on, every file path one design writes and another reads, every `FENCE_*` value per fence, every script and role and the folder it must resolve from, every Archon feature a design assumes (`include:` with `fan_out:` inside a `loop_group`, `sandbox:` on a `file` node, `isolation:`, `env:` reaching an MCP server, `$INPUTS` in `when:`, `returns:`). Each entry cites every design that names it. The gauntlet design's own copy list seeds it.
2. *Review.* `cad-reviewer` (opus) over each design against the inventory and the other six, plus one pass over the seven build orders for dependency cycles and steps that need an unbuilt file, plus each assumed Archon feature checked against `docs/reference/archon/` or a `/cad-spike` probe where the docs do not settle it. Findings are deduplicated and grouped by inventory entry, so one ruling closes every occurrence of one disagreement.
3. *Rulings.* The owner rules per group through `/cad-decision-review` where a group is a load-bearing decision and the ask-user seam otherwise. Each ruling is applied to every design it names in one commit, and a ruling that changes a contract updates the inventory in the same commit.
4. *Convergence.* A second full review over the edited designs. The phase ends only when a pass returns no finding that is not already ruled; a new finding goes back to pass 3. Then every design is set `Status: approved`, and the inventory is committed as `docs/superpowers/specs/contracts.md`, the reference later phases are reviewed against.
**Depends on:** Nothing (first phase)
**Requirements:** REV-01, REV-02, REV-03, REV-04, REV-05
**Success Criteria:**
1. `docs/superpowers/specs/contracts.md` lists every cross-design contract with every design that names it, and every finding in the phase's review record cites an entry there, adds one, or is marked internal to the one design it concerns
2. Every finding group carries one owner ruling, and `git log` shows each ruling applied to every design it names in a single commit
3. The review record holds a final pass over the edited designs with zero findings not already ruled, dated after the last ruling commit
4. Every Archon feature the inventory lists as assumed carries a verdict (documented, probed, or unsupported with the design changed), none left open
5. `grep -l '^Status: approved' docs/superpowers/specs/*.md` lists all seven designs, and the gauntlet design's copy list names nothing unresolved

### Phase 2: Test gate and shared layer
**Goal:** The accepted testing policy is enforced in GitHub Actions and the shared code every later phase imports exists with its suites: fence name patterns, `FENCE_HIDE`, the fence `commit` tool, `.shared/rounds.py`, `.shared/red.py` and `.shared/working-folder.ts`. Coverage reads unknown today; the gate's first run gives the real figure and this phase closes any shortfall against 85/85 without lowering a threshold.
**Depends on:** Phase 1
**Requirements:** CORE-01, CORE-02, CORE-03, CORE-04, CORE-05, CORE-06
**Success Criteria:**
1. `planning.mjs test-policy check --root .` returns `ok: true` with `.github/cadence/coverage-policy.json` tracked and the jobs `tests`, `fixtures` and `lint` present in a workflow file
2. The required jobs pass on the commit that closes this phase, with lines and branches at or above 85 over the included scope
3. A fenced tool call on a path under `FENCE_HIDE` raises `PermissionError` naming `FENCE_HIDE`, and `list_directory` over its parent omits it
4. `.shared/red.py`'s `red()` returns True for a test failing in the run and in neither baseline, and False for a failure the brief baseline already carries
5. Every new suite goes red against a null stub before the code is written, and the suites run as `docs/testing.md` states

### Phase 3: Roles
**Goal:** Every role file the designs name exists under its workflow's `commands/` with the turn protocol its approved design gives, plus `.shared/task-format.md`.
**Depends on:** Phase 1
**Requirements:** ROLE-01, ROLE-02
**Success Criteria:**
1. For each of the sixteen role names in ROLE-01, a `commands/<role>.md` exists in the workflow folder its design assigns
2. Each role file's opening prompt, first turn and per-turn input match the clauses its approved design states, checked clause by clause in review
3. `.shared/task-format.md` states the task format, and `arbiter.md` is unchanged except where a Phase 1 ruling changed it
4. `archon workflow list --json` and `archon validate workflows` are clean from the pack root after the files land

### Phase 4: Checkout phases
**Goal:** Intake, plan review and spec review run standalone and as included blocks of `gauntlet-run`, with their ledgers, citations, fences and fixtures, and the shared `screen` workflow in front of every reviewer.
**Depends on:** Phase 2, Phase 3
**Requirements:** RUN-01, RUN-02, RUN-03, RUN-04, RUN-05
**Success Criteria:**
1. `archon workflow run intake --input file=<path>` in a repository whose working folder is ignored writes `gauntlet/tasks/<slug>.md` matching the file verbatim
2. `archon workflow run gauntlet-run` with a message pauses at intake's approval, then at plan review's and spec review's, each answered on the run's own id
3. Every fixture under `intake/`, `plan-review/`, `spec-review/` and `screen/` passes `archon workflow test`, and a fixture with its deciding edge rewired fails
4. A round file carrying a steering phrase reaches the screener and never the reviewer, in `screen/fixtures/steering.stubs.yaml`
5. Every fence outside `intake/` whose `FENCE_READ` covers `gauntlet/failed/` sets `FENCE_HIDE=gauntlet/failed`, and the speccer's fence lists no folder that holds it

### Phase 5: Worktree cut and tree run
**Goal:** After spec review the run pins a branch, cuts one worktree from the checkout's `HEAD`, copies the approved files in, records the test baseline and hands off to the tree run; a defective plan is recorded in `gauntlet/failed/` and cancels the run at `kill`.
**Depends on:** Phase 4
**Requirements:** RUN-06, RUN-07
**Success Criteria:**
1. After the cut, `gauntlet/tasks/<slug>.md`, the approved plan and specs are present in the worktree at the paths the cut design names, and the baseline file holds the brief command's output
2. `gauntlet-run/fixtures/cut.stubs.yaml`, `tree-failed.stubs.yaml` and `defective.stubs.yaml` pass, and the defective route reaches `fail` then `kill` and never `land`
3. `gauntlet/failed/<slug>.txt` in the checkout holds the juror's ruling verbatim, and a second defective run on the same slug exits non-zero at `fail` naming the file
4. `gauntlet-run/scripts/pin.py`'s suite goes red against a null stub before the code is written

### Phase 6: Writing
**Goal:** Writing runs as block `write` of the tree run: test writers write the tests from the approved specs, code writers make them pass, a juror rules each contested round, a wrong plan or spec becomes an approved revision, and the phase ends with the sealed commit `<slug>: final`.
**Depends on:** Phase 5
**Requirements:** RUN-08, RUN-09, RUN-10
**Success Criteria:**
1. A run on a task with one approved spec leaves a test file under `tests/` committed by the test writer before any code commit on the branch
2. `write/fixtures/written.stubs.yaml` reaches `seal`, and, when the tree holds uncommitted changes, the final commit's message starts `<slug>: final` (`GAUNTLET_FINAL_SUBJECT` unset) with the approved summaries in its body, read back with `git log -1 --format=%B`; a clean tree gets no final commit
3. An approved revision lands as `gauntlet/<plans|specs>/approved/<slug>.rev<N>.txt` with N one above the highest present, and a second `enter` on the same N exits non-zero
4. Writing's `stage.py red` and the mend's `verify.py` import `.shared/red.py` and hold no comparison of their own
5. A juror verdict `defective` hands off `outcome: defective` and `write/fixtures/defective.stubs.yaml` passes

### Phase 7: Mend and landing
**Goal:** The mend rebases the tree's branch onto the checkout's `HEAD`, reruns the brief command when the checkout moved, repairs a red through a juror-ruled mend read by a reviewer, and hands `ready` or `left`; landing shows the owner the test line, diff stat and messages, fast-forwards on land, copies the records and removes the tree. The full run lands a task end to end.
**Depends on:** Phase 6
**Requirements:** RUN-11, RUN-12, RUN-13, RUN-14, PACK-01
**Success Criteria:**
1. With the checkout moved past base by one commit, the mend's rebase puts the tree's branch on the new `HEAD` and the brief command reruns; with the checkout unmoved, no rerun happens
2. A red on the rebased tree reaches node `juror` (command `mend-juror`), and the owner is asked only on a `defective` ruling or a stall, in `mend/fixtures/repair*.stubs.yaml`
3. On land, `git -C <checkout> rev-parse HEAD` equals the tree branch's tip, the tree's `gauntlet/` records exist in the checkout, and `git worktree list` no longer shows the tree
4. On leave, the tree, its branch and the checkout's `HEAD` are unchanged
5. Every fixture in the pack passes `archon workflow test`, and `archon workflow list --json` and `archon validate workflows` are clean from the pack root
