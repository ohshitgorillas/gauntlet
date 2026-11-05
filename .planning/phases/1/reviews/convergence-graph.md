Convergence pass, Plan 3 Task 3: the graph check and the section A re-check, made by the executor on the designs as committed at e01ea0b (the G-45 commit, after e9d81de). Input to REVIEW-pass2.md or REVIEW-convergence.md; not committed on its own.

## Build orders as one graph (current)

Key as REVIEW-pass1.md section 2. 40 steps (intake 3, gauntlet 10, plan-review 4, spec-review 7, worktree-cut 3, writing 7, landing 6). `[implied]` is an edge the step needs and does not state.

```
gauntlet:1  | needs intake:3, plan-review:4, spec-review:7 | gauntlet-run.yaml head, scripts/guard.ts, dirty fixtures
gauntlet:2  | needs intake:3 | intake/scripts/ground.ts
gauntlet:3  | needs intake:2 | intake/commands/clerk.md
gauntlet:4  | needs worktree-cut:2, writing:7 | gauntlet-tree.yaml (paths, write, handoff)
gauntlet:5  | needs gauntlet:1, gauntlet:4, worktree-cut:3 | gauntlet-run.yaml (cut outcome/verdict, fail, kill)
gauntlet:6  | needs plan-review:1 | fence/files.py (FENCE_HIDE)
gauntlet:7  | needs gauntlet:6, plan-review:3 [file] | plan-review defense/prosecutor/reporter .mcp.json (FENCE_HIDE)
gauntlet:8  | needs - | .shared/red.py
gauntlet:9  | needs gauntlet:4, landing:3 | gauntlet-tree.yaml (mend, handoff)
gauntlet:10 | needs gauntlet:5, gauntlet:9, landing:6 | gauntlet-run.yaml (land, land-2, land-3), landed/left/mend-left/moved/moved-twice fixtures
intake:1    | needs - | nothing in this tree
intake:2    | needs - | .shared/task-format.md, intake/commands/clerk.md
intake:3    | needs intake:2 [implied: ground.ts imports task-format.md, intake.yaml names clerk] | .shared/working-folder.ts, intake scripts, intake.yaml, fixtures
plan-review:1 | needs - | fence/files.py (name patterns)
plan-review:2 | needs - | plan-review/scripts/cite.py
plan-review:3 | needs plan-review:1 | defense/prosecutor/reporter roles and fences
plan-review:4 | needs plan-review:2, plan-review:3, spec-review:2, spec-review:5 | plan-review.yaml, scripts/guard.ts, fixtures
spec-review:1 | needs - | .shared/rounds.py
spec-review:2 | needs spec-review:1 | plan-review/scripts/ledger.py
spec-review:3 | needs spec-review:1 | spec-review/scripts/ledger.py
spec-review:4 | needs - | screener, speccer, reporter, arbiter roles
spec-review:5 | needs spec-review:4, plan-review:1 | screen/screen.yaml, screener.mcp.json
spec-review:6 | needs - | fence/spike.py
spec-review:7 | needs spec-review:3, :4, :5, :6 | spec-review.yaml, guard.ts, handoff.ts, fences, fixtures
worktree-cut:1 | needs - | .shared/pin.py, .shared/tests/test_pin.py, gauntlet-run/scripts/pin.py, gauntlet-run/tests/test_pin.py
worktree-cut:2 | needs intake:3 | gauntlet-tree.yaml, guard.ts, fixtures
worktree-cut:3 | needs worktree-cut:1, worktree-cut:2, gauntlet:1 | gauntlet-run.yaml (pin, tree, cut), fixtures
writing:1 | needs gauntlet:6 | fence/files.py (commit, @base), fence/checks.py (settings)
writing:2 | needs spec-review:1 | write/scripts/ledger.py
writing:3 | needs writing:2, gauntlet:8 | write/scripts/stage.py
writing:4 | needs - | writing roles
writing:5 | needs spec-review:5 | screen/screen.yaml, screener.mcp.json
writing:6 | needs writing:1, writing:4 | write-tests, write-code blocks
writing:7 | needs writing:3, :4, :5, :6 | write/write.yaml, fences, fixtures
landing:1 | needs gauntlet:8 | mend/scripts/verify.py
landing:2 | needs - | mend roles
landing:3 | needs landing:1, landing:2, writing:6 | mend/mend.yaml, fences, fixtures
landing:4 | needs worktree-cut:1 | land/scripts/pin.py, land/tests/test_pin.py
landing:5 | needs landing:3, intake:3 | gauntlet-remend.yaml, scripts/guard.ts, fixtures
landing:6 | needs landing:4, landing:5 | land/land.yaml, 7 land fixtures
```

Graph checks.

- Cycles: none. Depth-first from gauntlet:10 ends at steps needing nothing (gauntlet:8, intake:2, plan-review:1 and 2, spec-review:1, 4 and 6, worktree-cut:1, writing:4, landing:2) without revisiting a step. Longest chain: gauntlet:10 to gauntlet:5 to gauntlet:4 to writing:7 to writing:6 to writing:1 to gauntlet:6 to plan-review:1 (8 steps, one shorter than pass 1: writing:8 and the seal step are gone).
- A step needing a step ordered after it, within a design: none. Every in-design "Needs" names a lower number (gauntlet:5, 7, 9, 10; plan-review:3, 4; spec-review:2, 3, 5, 7; worktree-cut:3; writing:3, 6, 7; landing:3, 5, 6).
- A step needing a file no step builds: none. Checked for the files G-45 added: `.shared/pin.py` and `.shared/tests/test_pin.py` (worktree-cut:1), `land/scripts/pin.py` and `land/tests/test_pin.py` (landing:4), `gauntlet-remend/gauntlet-remend.yaml`, `scripts/guard.ts` and the four `fixtures/*.stubs.yaml` (landing:5), `land/fixtures/{land,leave,moved,moved-left,waited,third,refused}.stubs.yaml` (landing:6, same seven as the fixture paragraph), `gauntlet-run/fixtures/{moved,moved-twice}.stubs.yaml` (gauntlet:10).
- Files two steps write, all chained by "Needs": `fence/files.py` (plan-review:1, gauntlet:6, writing:1); `gauntlet-run/gauntlet-run.yaml` (gauntlet:1, worktree-cut:3, gauntlet:5, gauntlet:10); `gauntlet-tree/gauntlet-tree.yaml` and its `tree.stubs.yaml`/`defective.stubs.yaml` (worktree-cut:2, gauntlet:4, gauntlet:9); `screen/screen.yaml` and `screen/screener.mcp.json` (spec-review:5, writing:5); `.shared/tests/` holds distinct files from spec-review:1, gauntlet:8, worktree-cut:1.
- Step references across designs: every "design's step N" names an existing step except one (below).

## Candidate finding from the graph

`landing-design.md:514` (Order, closing line): "`gauntlet-design.md`'s step 11 needs step 6." `gauntlet-design.md` has 10 steps; its landing step is step 10. The line read "step 11 needs step 4" at 0d08176, when gauntlet-design.md had 11 steps; G-10's drop of the seal step (applied in e9d81de) renumbered gauntlet-design.md and left this reference. G-45's edit changed "needs step 4" to "needs step 6" on the same line and left "step 11" as written. No ruled group names it (G-10 names `gauntlet-design.md` step 9 only). Rows: none; a missing contract (build-order reference). Not fixed, because a ruling is applied exactly as ruled.

## Section A rows a ruling changed, re-checked

Read each verdict cell against the designs as they now stand.

| Row | Ruling | Verdict now | Stands? |
|---|---|---|---|
| A1 | G-12 | documented :1569 plus probed P7 | yes; the phase files keep `worktree: { enabled: false }` (copy-list bullet 2) |
| A5 | G-02 | probed P2 | yes; grep for `"CLAUDE_PROJECT_DIR"` and `CLAUDE_PROJECT_DIR=` finds no value set in any design |
| A10 | G-03, D-13 | `probed`, probe P1 refuted the form; "no design assumes `sandbox:` any more" | grep: `sandbox:` appears in the designs only as a negation (`spec-review-design.md:279`, `:403`, `:520`). The cell says `probed` while the probe showed the assumed form does not work; whether that reads `probed` or `unsupported` with a hash is the closing decision of Task 4. Flagged, not changed |
| A11 | G-01, D-11 | unsupported, "hash cited at close" | yes; no `.mcp.json` value takes the repository `env:`, the only `sh -c` launch lines carry `${ARCHON_HOME:-$HOME/.archon}` |
| A12 | G-01 | documented | yes |
| A15 | G-26, D-28 | ruled plus documented | yes; the `until_bash` forms at `landing-design.md:101` and `writing-design.md:356` read `end=$x.output.end; [ -n "$end" ]` |
| A19 | G-04, D-14 | unsupported, "hash cited at close" | yes; grep finds no `allowed_tools` list holding `Task` in any design |
| A29 (new, G-45) | G-45 | documented :1588-1596, :1732-1733, :2543-2544, :1735, :2105, :2055; node-id hash unmeasured, guarded by `branch-check` | yes |

Rows G-45 relies on and did not change: A4 (isolation), A14 (`with:` with `{ from, if_skipped }` on a script node), A17 (`none_failed_min_one_success`), A21 (child run answers), A22 (resume re-drives the failed child), A23 (`archon complete --force`). Each is unchanged in form.
