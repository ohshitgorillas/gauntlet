Convergence pass 4, Plan 6 Task 1: the graph check, made by the executor on the seven designs as committed at 0549df8 (the D-81 owner-control apply). Input to REVIEW-pass4.md or REVIEW-convergence.md; not committed on its own. Owner-control rewrote every `## Order` section, so the pass-3 graph (`convergence-graph-3.md`) no longer holds and is re-derived whole.

## Build orders as one graph

Key `<design>:N`. 38 steps: intake 3 (I), gauntlet 8 (G), plan-review 4 (PR), spec-review 7 (SR), worktree-cut 3 (WC), writing 7 (W), landing 6 (L). Against pass 3 (40 steps): gauntlet 10 to 8 (the `fail`/`kill` step and the `Task` step went; back to planning and the stage chain came), intake keeps 3, landing keeps 6. `[implied]` is an edge the step needs and its text does not state.

```
I:1  | needs -                                  | nothing in this tree
I:2  | needs -                                  | intake/scripts/items.py, intake/commands/clerk.md
I:3  | needs I:2, WC:1                          | .shared/working-folder.ts, intake scripts, intake.yaml, clerk.mcp.json
G:1  | needs I:3, PR:4, SR:7                    | gauntlet-run.yaml head, scripts/guard.ts, dirty fixtures
G:2  | needs WC:1                               | gauntlet-run/scripts/back.py
G:3  | needs G:1, G:2, G:4, WC:3                | gauntlet-run.yaml (cut fields, done, back, stage nodes), cut/planning/staged fixtures
G:4  | needs WC:2, W:7                          | gauntlet-tree.yaml (paths, write, handoff)
G:5  | needs PR:1                               | fence/files.py (FENCE_HIDE)
G:6  | needs -                                  | .shared/red.py
G:7  | needs G:4, L:3                           | gauntlet-tree.yaml (mend, handoff)
G:8  | needs G:3, G:7, L:6, L:5                 | gauntlet-run.yaml (land..land-4), landed/left/mend-left/moved/moved-twice/moved-thrice fixtures
PR:1 | needs -                                  | fence/files.py (name patterns)
PR:2 | needs -                                  | plan-review/scripts/cite.py, scope.py
PR:3 | needs PR:1                               | defense/prosecutor/reporter/analyst roles and fences
PR:4 | needs PR:2, PR:3, SR:2, SR:5 [implied: I:3] | plan-review.yaml, scripts/guard.ts, fixtures
SR:1 | needs WC:1                               | .shared/rounds.py
SR:2 | needs SR:1                               | plan-review/scripts/ledger.py
SR:3 | needs SR:1                               | spec-review/scripts/ledger.py
SR:4 | needs -                                  | screener, speccer, reporter, arbiter, analyst roles
SR:5 | needs SR:4, PR:1                         | screen/screen.yaml, screener.mcp.json
SR:6 | needs -                                  | fence/spike.py
SR:7 | needs SR:3, SR:4, SR:5, SR:6 [implied: I:3] | spec-review.yaml, guard.ts, handoff.ts, fences, fixtures
WC:1 | needs -                                  | .shared/pin.py, gauntlet-run/scripts/pin.py, tests
WC:2 | needs I:3                                | gauntlet-tree.yaml, guard.ts, tree/conflict/branch fixtures
WC:3 | needs WC:1, WC:2, G:1                    | gauntlet-run.yaml (pin, tree, cut of stage 1), cut/staged/tree-failed fixtures
W:1  | needs G:5, G:6                           | fence/files.py (commit, @base), fence/checks.py (settings, FENCE_CUT)
W:2  | needs SR:1                               | write/scripts/ledger.py
W:3  | needs W:2, G:6                           | write/scripts/stage.py
W:4  | needs -                                  | writing roles, amicus/commands/amicus.md
W:5  | needs SR:5, W:4                          | screen/screener.mcp.json, screen.yaml, amicus block
W:6  | needs W:1, W:4                           | write-tests, write-code blocks
W:7  | needs W:3, W:4, W:5, W:6                 | write/write.yaml, fences, fixtures
L:1  | needs G:6                                | mend/scripts/verify.py
L:2  | needs -                                  | mend roles (mend-code, mend-tests, mend-review, final-review)
L:3  | needs L:1, L:2, W:6, W:5                 | mend/mend.yaml, fences, fixtures
L:4  | needs WC:1                               | land/scripts/pin.py
L:5  | needs L:3, I:3                           | gauntlet-remend.yaml, guard.ts, fixtures
L:6  | needs L:4, L:5                           | land/land.yaml, fixtures
```

## Cycle check

None. A topological order exists: I:1, I:2, PR:1, PR:2, SR:4, SR:6, WC:1, G:6, W:4, L:2; then I:3, SR:1, G:5, PR:3, L:1, L:4; then SR:2, SR:3, SR:5, W:1, W:2, W:3; then PR:4, SR:7, W:5, W:6, WC:2; then W:7, G:1, L:3; then WC:3, G:4, L:5; then L:6, G:3, G:7; then G:8. No step is revisited on a depth-first walk from G:8. Longest chain: G:8, G:3, G:4, W:7, W:6, W:1, G:5, PR:1 (8 steps).

## Missing-file check

None. Every file-like path (a known pack folder prefix and a `.py .ts .md .yaml .mcp.json .stubs.yaml` ending) named in the body of the seven designs sits in an Order section (189 body paths, 162 Order paths; the only body paths not in an Order are placeholders `<route>.stubs.yaml`, `<role>.md` and `fence/test_*.py`). Files that two steps write are chained by a "Needs":

- `fence/files.py`: PR:1, G:5 (needs PR:1), W:1 (needs G:5).
- `gauntlet-run/gauntlet-run.yaml`: G:1, WC:3 (needs G:1), G:3 (needs WC:3), G:8 (needs G:3); fixtures `cut.stubs.yaml` and `staged.stubs.yaml`: WC:3, G:3.
- `gauntlet-tree/gauntlet-tree.yaml` and its `tree.stubs.yaml`: WC:2, G:4 (needs WC:2), G:7 (needs G:4); `planning.stubs.yaml`: G:4, G:7.
- `screen/screen.yaml`, `screen/screener.mcp.json`: SR:5, W:5 (needs SR:5).
- `mend/scripts/verify.py`, `write/scripts/stage.py` appear in G:6 as readers of `.shared/red.py`, not writers.

Cross-design step references name existing steps: landing "`gauntlet-design.md`'s step 6" (red) and "step 8" (landing in the run; gauntlet has 8 steps), plan-review "spec review design's steps 2 and 5", writing "gauntlet-design.md's steps 5 and 6", "spec review design's step 1 and step 5", landing "(its step 5)" and "(its step 1)", gauntlet "worktree cut design's step 3", "plan review design's step 1".

## Candidates from the graph (not ruled; for REVIEW-pass4.md)

1. `gauntlet-design.md`, heading `## Order`, step 3: "Needs steps 1, 2 and 4". Step 4 is ordered after step 3, so a builder taking the steps in number order meets an unmet Need. Not a cycle: G:4 needs WC:2 and W:7 and does not need G:3. New with the owner-control apply (pass 3 had no forward need). Row: none (a build order is internal to gauntlet-design.md). Severity: medium under D-60 (a step whose stated Need is built after it; pass 2 and 3 checked "a step needing a step ordered after it, within a design" as a defect class). Smallest edit: renumber so the stage chain follows the tree run's step, or reword step 3 to "needs steps 1 and 2 and the worktree cut design's step 3" and move the `G:4` clause to the step that builds `gauntlet-tree.yaml`; the gauntlet design's own text decides which.
2. `plan-review-design.md` `## Order` step 4 and `spec-review-design.md` `## Order` step 7 build `plan-review/scripts/guard.ts` and `spec-review/scripts/guard.ts`, which import `requireIgnored` from `.shared/working-folder.ts` (plan-review-design.md Homes row "Working-folder check", spec-review-design.md Homes row "Working-folder check", both naming the intake design). Neither step lists the intake design's `.shared/working-folder.ts` (I:3) in its Needs, whereas WC:2, L:5 and G:1 do. Not a cycle and no missing file in the whole graph (G:1 needs I:3 and both blocks), but the two steps have an unstated Need on a file no step of their own design builds. Row: internal to plan-review (step 4) and spec-review (step 7). Severity: low (the pass-2 and pass-3 graphs carried the same omission and G:1 orders both blocks behind I:3; a builder meets it at the first run of `archon validate workflows`, which Step 4 and Step 7 both run).

No Needs clause changed in a way that creates a cycle or a missing file.
