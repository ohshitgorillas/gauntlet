Convergence pass 5, Plan 7 Task 4 (pass k+1 rule): the graph check, made by the executor on the seven designs at `43cb8a4` (the pass-4 ruling round). Four `## Order` sections changed against `0549df8`, hence this re-derivation: gauntlet, plan-review, spec-review, writing (intake, worktree-cut, landing hash identically). Input to REVIEW-pass5.md or REVIEW-convergence.md; not committed on its own.

## Changes against graph 4 (the whole delta)

Same 38 steps. Needs clauses that moved (read with `diff` of each `## Order` section, `0549df8` against `43cb8a4`):

- gauntlet: the old steps 3 and 4 swapped. New G:3 is writing in the tree run (needs WC:2, W:7); new G:4 is the stage chain and the run's end (needs G:1, G:2, G:3, WC:3). G:7 needs G:3 (was G:4) and L:3. G:8 needs G:4 (was G:3), G:7, L:6, L:5.
- plan-review: PR:4 names I:3 in its Needs (`.shared/working-folder.ts`), the edge graph 4 marked [implied].
- spec-review: SR:7 names I:3 likewise.
- writing: W:3 needs W:2, G:6 and PR:2 (`marks`, imported by `stage.py`).

All other rows stand as graph 4 lists them.

## Cycle check

None. PR:2 needs nothing, so W:3's new edge adds no cycle. G:3 needs WC:2 (needs I:3) and W:7 (needs W:3..W:6); none needs G:3 or G:4. G:4 needs G:1, G:2, G:3, WC:3, and WC:3 needs WC:1, WC:2, G:1 (G:1 needs I:3, PR:4, SR:7); none needs G:4. G:7 needs G:3 and L:3; G:8 needs G:4, G:7, L:5, L:6. The topological order of graph 4 holds with G:3 and G:4 exchanged.

## Order-in-design check

Every Needs clause inside gauntlet's `## Order` now names a lower step (step 4: "steps 1, 2 and 3"; step 7: "step 3"; step 8: "steps 4 and 7"). Graph 4's candidate 1 (step 3 needing step 4) is closed. The other three changed sections name only steps of their own design that are lower, or steps of another design.

## Missing-file check

None. `git diff ae19601 43cb8a4` of the specs adds no file-like path that sits in no Order section: every `.py .ts .md .yaml .mcp.json` the added lines name is already in an Order section (`plan-review/scripts/scope.py`, `write/scripts/stage.py`, `.shared/working-folder.ts`, `landing`'s `land/land.yaml`) or a placeholder (`<slug>.idle.K.md`, `<slug>-summary.N.md`, `gauntlet/write/<slug>.scope.rev<M>.txt` are runtime files). The new landing node `files` is a node of `land/land.yaml`, not a file.

## Candidates from the graph (not ruled; for REVIEW-pass5.md)

None. Graph 4's candidate 1 and candidate 2 are closed by the pass-4 round (G-127).
