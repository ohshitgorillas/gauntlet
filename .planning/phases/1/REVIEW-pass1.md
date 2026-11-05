# Phase 1 review, pass 1

Date: 2026-11-05
Plan: `.planning/phases/1/PLAN-2.md`
Reviewed: the seven designs under `docs/superpowers/specs/` against `docs/superpowers/specs/contracts.md` (rows H, P, F, S, R, A).

Ids: findings are `1.NN` (pass 1, numbered in this file); groups are `G-NN`. A finding cites `<design>.md:<line>`, the text it is about, and a `contracts.md` row id, or the mark "internal to <design>" when it touches no cross-design contract (CONTEXT AC1).

Sources: (1) Archon feature verdicts, (2) the seven build orders as one graph, (3) one `cad-reviewer` (opus) review per design, (4) groups.

## 1. Archon feature verdicts

Verdicts come from the vendored documentation (D-03) and, for the two rows no doc covers, from the probe record `.planning/phases/1/PROBES.md` (cited below as PROBES.md, section P1-P3; the main session ran the `spiker` probes). The verdict and its citations sit in the verdict column of `contracts.md` section A; this table repeats the outcome.

| Row | Verdict | Finding |
|---|---|---|
| A1-A4, A6-A9 | documented | - |
| A5 | probed (PROBES.md P2) | 1.04 (in section 4), 1.05 withdrawn (section 9) |
| A10 | probed (PROBES.md P1) | 1.03 (in section 6) |
| A11 | unsupported | 1.01, 1.02 |
| A12-A18 | documented | - |
| A19 | unsupported (PROBES.md side finding) | 1.07, 1.08 |
| A20-A28 | documented | - |

Counts: 28 rows; 24 documented, 2 unsupported (A11, A19), 2 probed (A5, A10). The features findings below cite A11 and A19: the equality "unsupported rows = distinct rows the features findings cite" holds (2 = 2). A `probed` row whose probe contradicts a design's stated form carries its finding in that design's section (1.03 in section 6, 1.04 in section 4), as 1.06 does in section 5, because the finding is about that design's text and not about whether Archon has the feature.

Notes that stay inside a documented verdict (no finding, recorded so Plan 3 does not rediscover them):

- A9: instances of `include:` with `fan_out:` share the parent's checkout and run concurrently up to `max_parallel`; instances that write must coordinate their edits (`workflow-language.md:2613-2614`). `writing-design.md:379,386` set `max_parallel: 2` on two writing blocks.
- A20: `mcp:` files found beside the YAML work for a home-scoped workflow only; project, bundled and installed workflows use only the checkout (`mcp-servers.md:95-100`). This pack lives in `~/.archon/workflows/`, so it qualifies; an installed pack (`publishing-plugins.md`) would not.
- A25: "a dry run ends a loop after one iteration" (`gauntlet-intake-design.md:225`) is documented at `cli.md:414` for a tolerated loop only.

### Findings

**1.01** `writing-design.md:268`, row A11 (fences F8, F9).
Text: "Each is launched by `sh -c`, with every `FENCE_*` built from the repository's `env:` in the launch line." Also `writing-design.md:22`: "Unmeasured: whether the repository's `.archon/config.yaml` `env:` reaches an agent node's MCP server processes."
Finding: the MCP guide expands `env` and `headers` values from Archon's process environment, with codebase-scoped env vars on Codex nodes only (`mcp-servers.md:192-194`), and never touches `command` or `args` (`mcp-servers.md:211`). No doc line carries the repository `env:` to a Claude node's MCP server process. The fence launch form for F8 and F9 (`FENCE_TEST_COMMAND=$GAUNTLET_TEST_COMMAND`, `FENCE_TEST_TIMEOUT=${GAUNTLET_TEST_TIMEOUT:-900}`, `:$GAUNTLET_TEST_BASE` "when set") reads variables the documented route does not supply. The `${VAR:-default}` form does not match the expansion pattern (`mcp-servers.md:210`) and a conditional `:$GAUNTLET_TEST_BASE` cannot be written in a JSON `env` value. The design itself calls the route unmeasured.
Fence launch forms judged against `mcp-servers.md`: F1-F7 use literal `env` values plus `${ARCHON_HOME:-$HOME/.archon}` inside `args` that `sh` expands itself (`mcp-servers.md:144,211`): compatible. F8-F11 read the repository's `env:`: not covered.

**1.02** `landing-design.md:332`, row A11 (fences F10, F11).
Text: "launched by `sh -c` with every `FENCE_*` built from the repository's `env:` in the launch line". `landing-design.md:15`: "the repository's `env:` is measured to reach bash nodes only".
Finding: as 1.01 for the mend's fences. The design also contradicts itself: line 15 records the repository's `env:` as measured to reach bash nodes only, and line 332 builds the mend's `FENCE_*` from it for agent nodes' MCP servers.

**1.07** `plan-review-design.md:264`, row A19 (also `:301`, `:165`, `:170`).
Text: `allowed_tools: [Task, "Bash(uv run --script *cite.py *)"]`; `:165` "Detectives: dispatch through Task to `detective` for code reading."
Finding: `archon validate` warns "Tool 'Task' was renamed to 'Agent' in the claude SDK — the old name is silently ignored at runtime" (PROBES.md, side finding), while the vendored docs still show `Task` (`workflow-language.md:657`). With `Task` ignored, the defense node gets no sub-agent dispatch and the `detective` never runs. The probe's working form is `Agent` (PROBES.md section P1). Confidence: the warning text is the tool's own; a run with `Task` alone was not made.

**1.08** `spec-review-design.md:359`, row A19 (also `:24`, `:239`, `:243`).
Text: `allowed_tools: [Task, Bash]  # Bash for the spikers; the role forbids the speccer's own Bash`; `:239` "Spikers: dispatch through Task to `spiker`".
Finding: as 1.07, for the `spiker`. `writing-design.md:530` names `Task` as a tool a writer node must not hold: with the name renamed, the row should name both words or the new one.

Findings raised by the probes (1.03, 1.04, 1.06) are filed in their design sections because they concern that design's text: 1.03 in section 6, 1.04 in section 4, 1.06 in section 5. 1.05 is withdrawn; it is listed in section 9.

## 2. Build orders as one graph

Key: `<design>:step N`, `<design>` being the design file name without `-design.md`. An edge is the step's own "Needs" text; `[file]` marks an edge read off a file the step names in its own text without a "Needs" line, `[implied]` an edge the step needs and does not state. Writes list the step's files; a parenthesis lists the nodes or fields of a workflow file the step builds. `fence/` and `spec-review/commands/arbiter.md` exist today (`contracts.md` P14 and R4). One line per numbered step, 41 in all.

```
gauntlet:step 1 | needs intake:step 3, plan-review:step 5, spec-review:step 6 | writes gauntlet-run/gauntlet-run.yaml (name, inputs, worktree, nodes guard, intake, plan-review, spec-review), gauntlet-run/scripts/guard.ts
gauntlet:step 2 | needs intake:step 3 | writes intake/scripts/ground.ts
gauntlet:step 3 | needs intake:step 2 | writes intake/commands/clerk.md
gauntlet:step 4 | needs worktree-cut:step 2, writing:step 7 | writes gauntlet-tree/gauntlet-tree.yaml (nodes paths, write, handoff, description), gauntlet-tree/fixtures/tree.stubs.yaml, gauntlet-tree/fixtures/defective.stubs.yaml
gauntlet:step 5 | needs gauntlet:step 1, gauntlet:step 4, worktree-cut:step 3 | writes gauntlet-run/gauntlet-run.yaml (cut outcome and verdict, nodes fail, kill, description), gauntlet-run/fixtures/cut.stubs.yaml, gauntlet-run/fixtures/defective.stubs.yaml
gauntlet:step 6 | needs plan-review:step 1 | writes fence/files.py (FENCE_HIDE), fence/test_files_hide.py
gauntlet:step 7 | needs gauntlet:step 6, plan-review:step 4 [file], spec-review:step 6 [file] | writes plan-review/defense.mcp.json, plan-review/prosecutor.mcp.json, plan-review/reporter.mcp.json, spec-review/speccer.mcp.json
gauntlet:step 8 | needs - | writes .shared/red.py, .shared/tests/test_red.py
gauntlet:step 9 | needs writing:step 7 | writes write/write.yaml (node seal), write/fixtures/written.stubs.yaml
gauntlet:step 10 | needs gauntlet:step 4, writing:step 8, landing:step 3 | writes gauntlet-tree/gauntlet-tree.yaml (paths prints checkout and brief, node mend, handoff prints outcome and line, description), gauntlet-tree/fixtures/tree.stubs.yaml, gauntlet-tree/fixtures/left.stubs.yaml, gauntlet-tree/fixtures/defective.stubs.yaml
gauntlet:step 11 | needs gauntlet:step 5, gauntlet:step 10, landing:step 4 | writes gauntlet-run/gauntlet-run.yaml (cut line, node land, description), gauntlet-run/fixtures/landed.stubs.yaml, gauntlet-run/fixtures/left.stubs.yaml, gauntlet-run/fixtures/mend-left.stubs.yaml
intake:step 1 | needs - | writes nothing in this tree (removes the fence copies and a design file in archon-workflows)
intake:step 2 | needs - | writes .shared/task-format.md, intake/commands/clerk.md
intake:step 3 | needs intake:step 2 [implied: ground.ts imports task-format.md, intake.yaml names clerk] | writes .shared/working-folder.ts, intake/scripts/route.ts, intake/scripts/ground.ts, intake/intake.yaml, intake/clerk.mcp.json, intake/fixtures/file.stubs.yaml, intake/fixtures/clerk.stubs.yaml
plan-review:step 1 | needs - | writes fence/files.py (name patterns), fence/test_files_patterns.py
plan-review:step 2 | needs - | writes plan-review/scripts/cite.py, plan-review/tests/test_cite.py
plan-review:step 3 | needs - | writes plan-review/scripts/ledger.py, plan-review/tests/test_ledger.py
plan-review:step 4 | needs plan-review:step 1 | writes plan-review/commands/defense.md, prosecutor.md, reporter.md, screener.md, plan-review/defense.mcp.json, prosecutor.mcp.json, reporter.mcp.json, screener.mcp.json
plan-review:step 5 | needs plan-review:step 2, plan-review:step 3, plan-review:step 4 | writes plan-review/plan-review.yaml, plan-review/fixtures/*.stubs.yaml
spec-review:step 1 | needs - | writes .shared/rounds.py, .shared/tests/test_rounds.py
spec-review:step 2 | needs spec-review:step 1 | writes plan-review/scripts/ledger.py, plan-review/tests/test_ledger.py (replaces plan-review:step 3)
spec-review:step 3 | needs spec-review:step 1 | writes spec-review/scripts/ledger.py, spec-review/tests/test_ledger.py
spec-review:step 4 | needs - | writes screen/commands/screener.md, spec-review/commands/speccer.md, spec-review/commands/reporter.md, spec-review/commands/arbiter.md (amends the built file)
spec-review:step 5 | needs spec-review:step 4, plan-review:step 1 | writes screen/screen.yaml, screen/screener.mcp.json, screen/fixtures/steering.stubs.yaml, screen/fixtures/clean.stubs.yaml
spec-review:step 6 | needs spec-review:step 3, spec-review:step 4, spec-review:step 5 | writes spec-review/spec-review.yaml, spec-review/scripts/handoff.ts, spec-review/speccer.mcp.json, spec-review/arbiter.mcp.json, spec-review/reporter.mcp.json, spec-review/fixtures/*.stubs.yaml
spec-review:step 7 | needs spec-review:step 5, plan-review:step 5 [implied: edits plan-review.yaml] | writes plan-review/plan-review.yaml (screen as include: screen); declares plan-review/commands/screener.md and plan-review/screener.mcp.json not written
worktree-cut:step 1 | needs - | writes gauntlet-run/scripts/pin.py, gauntlet-run/tests/test_pin.py
worktree-cut:step 2 | needs intake:step 3 | writes gauntlet-tree/gauntlet-tree.yaml, gauntlet-tree/scripts/guard.ts, gauntlet-tree/fixtures/tree.stubs.yaml, gauntlet-tree/fixtures/conflict.stubs.yaml
worktree-cut:step 3 | needs worktree-cut:step 1, worktree-cut:step 2, gauntlet:step 1 | writes gauntlet-run/gauntlet-run.yaml (nodes pin, tree, cut), gauntlet-run/fixtures/cut.stubs.yaml, gauntlet-run/fixtures/tree-failed.stubs.yaml
writing:step 1 | needs gauntlet:step 6 | writes fence/files.py (commit, FENCE_COMMIT), fence/test_files_commit.py
writing:step 2 | needs spec-review:step 1 | writes write/scripts/ledger.py, write/tests/test_ledger.py
writing:step 3 | needs writing:step 2, gauntlet:step 8 | writes write/scripts/stage.py, write/tests/test_stage.py
writing:step 4 | needs - | writes write/commands/divvyer.md, juror.md, reviser.md, reviewer.md, reporter.md, write-tests/commands/test-writer.md, write-code/commands/coder.md
writing:step 5 | needs spec-review:step 5 | writes screen/screener.mcp.json, screen/screen.yaml
writing:step 6 | needs writing:step 1, writing:step 4 | writes write-tests/write-tests.yaml, write-tests/test-writer.mcp.json, write-tests/fixtures/committed.stubs.yaml, contest.stubs.yaml, write-code/write-code.yaml, write-code/coder.mcp.json, write-code/fixtures/committed.stubs.yaml, contest.stubs.yaml
writing:step 7 | needs writing:step 3, writing:step 4, writing:step 5, writing:step 6 | writes write/write.yaml, write/divvyer.mcp.json, juror.mcp.json, reviser.mcp.json, reviewer-plan.mcp.json, reviewer-spec.mcp.json, reporter.mcp.json, write/fixtures/*.stubs.yaml
writing:step 8 | needs writing:step 7, gauntlet:step 4 | writes gauntlet-tree/gauntlet-tree.yaml (nodes baseline, paths, write), gauntlet-tree/fixtures/tree.stubs.yaml
landing:step 1 | needs gauntlet:step 8 | writes mend/scripts/verify.py, mend/tests/test_verify.py
landing:step 2 | needs - | writes mend/commands/mend-juror.md, mend-code.md, mend-tests.md, mend-review.md
landing:step 3 | needs landing:step 1, landing:step 2, writing:step 6 | writes mend/mend.yaml, mend/mend-juror.mcp.json, mend-code.mcp.json, mend-tests.mcp.json, mend-review.mcp.json, ten mend/fixtures/*.stubs.yaml
landing:step 4 | needs - | writes land/land.yaml, land/fixtures/land.stubs.yaml, leave.stubs.yaml, moved.stubs.yaml, refused.stubs.yaml
```

Graph checks.

- Cycles: none. A depth-first walk of the needs above ends at steps that need nothing (gauntlet:8, intake:2, plan-review:1-3, spec-review:1, spec-review:4, worktree-cut:1, writing:4, landing:2, landing:4) without revisiting a step. The longest chain is `gauntlet:11` to `gauntlet:10` to `writing:8` to `gauntlet:4` to `writing:7` to `writing:6` to `writing:1` to `gauntlet:6` to `plan-review:1`.
- A step needing a step ordered after it: none within a design; every in-design "Needs" names a lower number. Across designs the orders are not numbered against each other, so only the cycle test applies.
- A step needing a file no step builds and the tree lacks: none. Every path the seven designs name in backticks with a pack folder prefix, every `*.mcp.json` and every `<workflow>/fixtures/*.stubs.yaml` appears in some order, except `fence/checks.py` and `fence/test_*.py` (built today, P14), the three `guard.ts` files the designs say are not written (S13), and the `<route>`/`<role>` placeholders.
- Files two steps write: `fence/files.py` (plan-review:1, gauntlet:6, writing:1), `gauntlet-run/gauntlet-run.yaml` (gauntlet:1, worktree-cut:3, gauntlet:5, gauntlet:11) and `write/write.yaml` (writing:7, gauntlet:9) are chained by "Needs" and add disjoint nodes or keys. `intake/scripts/ground.ts` and `intake/commands/clerk.md` (intake:3 then gauntlet:2; intake:2 then gauntlet:3) are chained. The cases below are not.

### Findings

**1.09** `plan-review-design.md:434`, row S9 (also P18).
Text: `plan-review-design.md:434` "3. Ledger: `plan-review/scripts/ledger.py`, `plan-review/tests/test_ledger.py`." and `:436` "Needs steps 2 to 4."; `spec-review-design.md:495` "2. Planning's ledger on the core: `plan-review/scripts/ledger.py`, `plan-review/tests/test_ledger.py`. This replaces the plan review design's ledger step."
Finding: two steps write the same two files and no "Needs" orders them (spec-review:2 needs spec-review:1 only). plan-review:5 needs plan-review:3, the step the spec review design replaces, and the plan review design's Order does not say so. A builder following `plan-review-design.md` builds the standalone ledger (`plan-review-design.md:86-140`); one following the spec review design builds the `Profile` form. Whichever step runs second overwrites the first.

**1.10** `spec-review-design.md:500`, row P16 (H4).
Text: "7. Planning on the shared screen: `plan-review/plan-review.yaml` with `screen` as `include: screen` ... Needs step 5."; `plan-review-design.md:436` "5. Workflow: `plan-review/plan-review.yaml`, `plan-review/fixtures/*.stubs.yaml`."
Finding: spec-review:7 edits a file that plan-review:5 creates and does not list plan-review:5 in its needs. Nothing orders the two steps, and plan-review:5's workflow (built with its own `screen` node, `plan-review-design.md:326-336`) is the file spec-review:7 rewrites. Also `plan-review/fixtures/*.stubs.yaml` (`plan-review-design.md:436`) holds fixtures for a `screen` node that spec-review:7 turns into an include; no step revises them.

**1.11** `spec-review-design.md:500`, rows R6, F6 (also F7).
Text: `plan-review-design.md:435` "4. Roles and fences: ... `plan-review/commands/screener.md` ... `plan-review/screener.mcp.json`."; `spec-review-design.md:500` "`plan-review/commands/screener.md` and `plan-review/screener.mcp.json` are not written."; `spec-review-design.md:497` builds `screen/commands/screener.md`.
Finding: plan-review:4 writes two files that spec-review:7 declares not written. The plan review design is not amended: `plan-review-design.md:211-235` still specifies the role and its fence, `:421` still names `plan-review/commands/screener.md`. A builder of plan-review:4 creates them, spec-review:7 then leaves them, and two screener roles exist (R6 names both).

**1.12** `gauntlet-design.md:366`, rows H19 (also H10, H18, H20, P16, P17); D-07's known case.
Text: `gauntlet-design.md:366` "4. Writing in the tree run: `gauntlet-tree/gauntlet-tree.yaml` (nodes `paths`, `write`, `handoff`, the description)"; `writing-design.md:542` "8. Brief baseline: `gauntlet-tree/gauntlet-tree.yaml` (`baseline`, `paths`, `write`) ... Needs step 7 and `gauntlet-design.md`'s step 4."; `gauntlet-design.md:372` "10. ... `paths` prints `checkout` and `brief`, node `mend`, `handoff` prints the mend's `outcome` and `line`".
Finding: not unordered (writing:8 needs gauntlet:4; gauntlet:10 needs both), and not resolved: three steps list overlapping node lists for one file. `paths` is written by gauntlet:4, writing:8 and gauntlet:10; `write` by gauntlet:4 and writing:8; `handoff` and the description by gauntlet:4 and gauntlet:10; `baseline` by worktree-cut:2 and writing:8. The designs give the same attribute twice: `gauntlet-design.md:146` says `paths` "also prints the slug, the checkout, and the brief baseline's path as the writing design gives it" (gauntlet:4), `writing-design.md:502` says "Node `paths` also prints `brief`" and "Node `write` passes `brief: $paths.output.brief`" (writing:8), and gauntlet:10 lists `checkout` and `brief` for `paths` again. With the steps ordered gauntlet:4, writing:8, gauntlet:10, each later step rewrites fields the earlier one built unless the builder is told which step owns which field. The options a ruling chooses between: gauntlet:4 owns `paths` and `write`'s `brief` input and writing:8 adds only the `baseline` brief file; writing:8 owns the `brief` field and gauntlet:4 prints it without the baseline; or each step lists only the fields it adds.

## 3. gauntlet-design.md

Source: opus `cad-reviewer` dispatch saved as `.planning/phases/1/reviews/pass2-gauntlet.json` (9 findings). Anchors checked with `sed -n`: 9 of 9 hold the quoted text; no line corrected, none dropped. Severities are the reviewer's.

**1.13** `gauntlet-design.md:121`, rows A3, A14; missing contract: where `$INPUTS` may appear inside a phase block (also `:123`, `:341`). High.
Text: "`$INPUTS.<name>` appears only in prompts and `bash:` bodies." `:341` "`$INPUTS.<name>` in prompts and `bash:`; `INPUTS_<NAME>` in scripts".
Finding: the rule binds `write/` and `mend/` through `:123` ("follow the same rules"), yet `writing-design.md:492` ("`<slug>`, plan files and spec files in prompts and `with:` come from `$INPUTS.slug`", used at `:434`, `:441`) and `landing-design.md:73`, `:91`, `:155` (`brief: $INPUTS.brief`) put `$INPUTS.<name>` in `with:` bindings. A builder who follows this design rewrites the `screen`, `flag`, `red`, `confirm` and `recheck` bindings the phase designs give verbatim; one who follows the phase designs breaks this home rule.

**1.14** `gauntlet-design.md:290`, row S4 (internal to the red rule). Medium.
Text: "True when run timed out; or a test FAILED or ERROR in run is failing in neither brief nor head"; `:292` "A failure in brief or head that passes in run is not red."
Finding: a timeout is red unconditionally, while failures already present in brief or head are exempt. A timeout already present in the brief baseline or on the checkout's HEAD still counts as red. Case 1: the brief baseline timed out at the cut, so every writing test run is red, the juror is called on every cut, and the run can reach `stalled` or DEFECTIVE over a condition the writers did not cause. Case 2: new checkout commits make the suite hang; the mend's `confirm` is red though `test-head` timed out the same way, so `repair` opens and the owner is asked about a red the tree did not cause (CLAUDE.md 1.4).

**1.15** `gauntlet-design.md:348`, row F4 (also P10). Medium.
Text: "hidden from every other checkout role by `FENCE_HIDE=gauntlet/failed`"; `:355` "Refusing a read inside a readable folder | `FENCE_HIDE`".
Finding: does not hold for spec review. Node `file` holds `allowed_tools: [Task, Bash]` (`spec-review-design.md:359`) and its `spiker` holds `Bash` (`:370`); their sandbox limits writes only (`:361`), and `FENCE_HIDE` covers fence tools only. During spec review the speccer, or a spiker it dispatches, can `cat gauntlet/failed/<slug>.txt` through Bash: the "no other role reads it" home is breached while `speccer.mcp.json`'s `FENCE_HIDE` gives the appearance of confinement.

**1.16** `gauntlet-design.md:247`, row H33 (also `:350`). Medium.
Text: "then each `gauntlet/revisions/<slug>-summary.<N>.md` in order of N"; `:350` "each revision summary in order of N".
Finding: every revision summary goes into the final commit message, but the reporter writes a summary for every SOUND round (`writing-design.md:89`, `:219`), including rounds the owner sends back with `revise` (`writing-design.md:494`). Round 1 SOUND writes `<slug>-summary.1.md`; the owner revises; round 2 is approved and only round 2 becomes `.rev1.txt`; `seal` still lists summary 1 and 2, so the landing gate shows a commit message describing a revision that was never entered.

**1.17** `gauntlet-design.md:19`, rows H25, A18 (also H18; `:98`). Medium.
Text: "The run ends at block `land` ..., after `cut` ..., and at node `kill`, cancelled".
Finding: `:19` and `:98` omit the `vacate` cancel inside writing (`writing-design.md:353-356`, `cancel: "... The run stops."`), which cancels the tree run, not gauntlet-run, and the `vacate` nodes of plan review and spec review. The design does not say what node `tree`, `cut`, `fail` or `kill` do when the child run ends cancelled. After twelve `OBJECTION: LEADING` verdicts `vacate` cancels gauntlet-tree, its `handoff` never runs, `cut` has no `$tree.output`, and the route is undefined: `:98` treats a failed `tree` as a resumable failed phase, which reruns writing straight back into `vacate`.

**1.18** `gauntlet-design.md:26`, rows H13, H14, H15, A1, H1, S13, H4, H5, H6, A2, H8, R12, S4, H12; copy-list bullets at `:23-34` (D-06). Medium.
Text: `:26` "Plan review's and spec review's declare none"; `:23` "Each description invites direct use"; `:24` "`worktree: enabled: false`: 4"; `:25` "Working-folder guard nodes in the checkout: 3"; `:27` "`$INPUTS` left of a `when:` comparison: 2"; `:28` "Inline `script:` handoffs that print an input: 2".
Finding: the copy list states as current fact copies the other designs no longer hold. `:23` against `gauntlet-intake-design.md:137`, `plan-review-design.md:244`, `spec-review-design.md:298` ("Not for direct use"); `:24` against `gauntlet-intake-design.md:221`, `plan-review-design.md:239`, `spec-review-design.md:293` (no `worktree:`); `:25` against `plan-review-design.md:12`, `spec-review-design.md:293`; `:26` against `plan-review-design.md:406`, `spec-review-design.md:460-463` (both declare an `output_format`); `:27` against `gauntlet-intake-design.md:157`, `:164`; `:28` against `spec-review-design.md:456`; `:29`, `:32`, `:33`, `:34` name needs this design's own `:228`, `writing-design.md:19`, `:279` and `landing-design.md:256` now meet. About 10 of 12 bullets are false for the current designs; a reader checking them spends tokens on claims already settled (CLAUDE.md 1.3). Task 5 maps each bullet to a group.

**1.19** `gauntlet-design.md:371`, row H33 (also `:247`). Low (CLAUDE.md 1.3).
Text: "9. The final commit's message: `write/write.yaml` (node `seal`), `write/fixtures/written.stubs.yaml`." `:247` "Node `seal` is the writing design's, with one change: it commits with `git commit -F -`".
Finding: `writing-design.md:408-410` already commits with `git commit -F -` and the same message, and `writing-design.md:494`, `:541` already build the sealed `written` fixture. Step 9 (after writing:7) finds `seal` and the fixture as specified and spends a `workflow-builder` dispatch and a validate cycle to change nothing, or rewrites a correct node.

**1.20** `gauntlet-design.md:243`, row P3. Low.
Text: "Each holds only its revision: the clauses it changes, each as it now reads"; `:229` `enter` does `cp -n` of the approved round file.
Finding: `writing-design.md:31` gives the round file the lines `Revises: plan|spec` and `Answers: <tree path>` before the clauses, and `writing-design.md:344` confirms `enter` copies `$record.output.enter`. `.rev1.txt` therefore carries those header lines, and the rule "the approved plan is `<slug>.txt` with every revision applied" hands agents a header that is not plan text, pointing at a tree file the mend's agents and the checkout record may not carry.

**1.21** `gauntlet-design.md:184`, row H34. Low.
Text: "Its only agent nodes are `mend-juror`, `mend-code`, `mend-tests` and `mend-review`".
Finding: the landing design's nodes are `juror` and `review` with `command: mend-juror` and `command: mend-review` (`landing-design.md:109-112`, `:157-159`). A builder or fixture author who keys the gauntlet-tree mend stubs, or a check of "only these agent nodes", on this design's ids finds no `mend-juror` or `mend-review` node in `mend/mend.yaml`.

## 4. gauntlet-intake-design.md

Source: opus `cad-reviewer` dispatch saved as `.planning/phases/1/reviews/pass2-gauntlet-intake.json` (6 findings). Anchors checked with `sed -n`: 6 of 6 hold the quoted text; none dropped. 1.25 is anchored in `gauntlet-design.md`, the line the reviewer gave, because the finding is about that copy list's claims on the intake design. 1.26 quotes a script spanning lines; the tracked-file sentence is at `:54`, the message at `:56`.

Seeded by Task 2 from the probe record, kept:

**1.04** `gauntlet-intake-design.md:117`, row A5.
Text: "Claude Code sets the server's `CLAUDE_PROJECT_DIR` to its own working directory, the run's checkout, and overrides any value the config gives, so the config sets none."
Finding: false as written. PROBES.md section P2: Claude Code sets `CLAUDE_PROJECT_DIR` to the cwd only when the MCP config gives no value; a config `env` value wins (`/bogus` stayed `/bogus`). The pack still works because every config sets none, but the stated reason does not hold: nothing in Claude Code stops a config from relocating the fence root of F1-F11, so "the config sets none" is a rule the pack must keep and test, not a guarantee. Same claim stands behind `plan-review-design.md:226`, `spec-review-design.md:269`, `writing-design.md:268` ("sets no `CLAUDE_PROJECT_DIR`").

From the reviewer:

**1.22** `gauntlet-intake-design.md:238`, row P10. Medium.
Text: the Homes row "Where Gauntlet writes" forbids "Any Gauntlet node writing outside `gauntlet/`".
Finding: other designs place core writes outside `gauntlet/`: `gauntlet-design.md:352` makes landing's `git merge --ff-only` the home for writing the checkout's tracked files, `gauntlet-design.md:275` says tracked files change only by that merge, `landing-design.md:252` runs the merge, and the coder fence writes `.` in the tree (`writing-design.md:294`, F9). Applied pack-wide as its wording says, the intake Homes table forbids landing's merge, the coder's and the mend's writes to tracked files, and seal's commit. Either the Homes rule is false or the pack cannot land any work; two designs rule opposite ways and nothing decides.

**1.23** `gauntlet-intake-design.md:110`, rows F5, R5. Medium.
Text: `"FENCE_WRITE": "gauntlet/tasks"`; `:94` "Never: writes outside gauntlet/tasks/<slug>.md, copies or deletes a file".
Finding: the fence gives Clerk write, edit, copy_file and delete_file on every task file; only the role's prose confines it to its own `<slug>.md`. That is what the Homes row `:245` forbids ("a hook or prompt rule standing in for" file confinement). Nothing checks the chosen slug is free (`:86` "pick a kebab-case slug not among the taken ones"). `gauntlet-design.md:307` tells Clerk to read `gauntlet/tasks/<failed-slug>.md`; Clerk can then edit or delete another run's task. If Clerk picks a taken slug, `until_bash` at `:182` (`[ -s "gauntlet/tasks/$slug.md" ]`) passes at once on the old file, so an approve on the opening turn hands off a previous run's task.

**1.24** `gauntlet-intake-design.md:56`, rows S3 (also H1, H2). Medium.
Text: "Gauntlet failed because its working folder, <root>/gauntlet/, sits in the main repo. Add it to .gitignore and restart the run."; `:54` "A file under gauntlet/ that git tracks fails it."
Finding: the single failure message cannot clear the tracked-file case. If the checkout already tracks `gauntlet/notes.md`, the owner adds `gauntlet/` to `.gitignore`, restarts, and git still tracks the file, so the guard fails again with the same line (in gauntlet-run's guard and gauntlet-tree's alike) until the owner works out `git rm --cached` alone.

**1.25** `gauntlet-design.md:24`, rows H1, H6, H13, S13 (copy-list bullets `:21-27`; seeds B01, B03, B05). Low.
Text: `:24` "`worktree: enabled: false`: 4, in `intake/intake.yaml`, ..."; `:23` "Each description invites direct use".
Finding: the gauntlet design says in the present tense that the intake design holds copies it does not hold: no `worktree:` key (`gauntlet-intake-design.md:221`), no `intake/scripts/guard.ts` (`:239` forbids one), no `$INPUTS` in a `when:` (`:157`, `:164` read `$route.output.file`), and a description "Not for direct use" (`:137`). A builder at gauntlet step 1 searches for a guard node, a `worktree:` key and `$INPUTS` `when:` lines the intake design never had (same copy-list disagreement as 1.18).

**1.26** `gauntlet-intake-design.md:158`, internal to gauntlet-intake-design.md (CLAUDE.md 1.4). Medium.
Text: "else (target taken, or empty slug) exit non-zero ... nothing renamed, suffixed or overwritten".
Finding: `from-file` fails on any occupied target; the only exemption is the handed-in path being the target itself. A target holding byte-identical content also stops the run: `--input file=~/notes/fix-login.md` run twice finds `gauntlet/tasks/fix-login.md` with the same bytes and exits non-zero, though no copy is needed.

**1.27** `gauntlet-intake-design.md:86`, rows P6, H16. Low.
Text: "Opening turn (node `clerk`): read the idea; pick a kebab-case slug ..."; `:173` requires `slug`; `:221` "may be empty".
Finding: the opening turn must output `slug` before any conversation, and it stays fixed for the whole talk group (`:181`, `:199`, `:217`), while the idea may be empty (`:7`, `:221`). With a blank message Clerk emits a meaningless slug, and the hand-off path, pin's branch (`worktree-cut-design.md:61`) and `gauntlet/failed/<slug>.txt` carry it ten turns later when the task is about something else.

## 5. plan-review-design.md

Source: opus `cad-reviewer` dispatch saved as `.planning/phases/1/reviews/pass2-plan-review.md` (10 findings). Anchors checked with `sed -n`: 10 of 10 hold the quoted text after two line corrections: 1.31 (reviewer `:93-94`, text at `:94`), 1.32 (reviewer `:323-326`, the `when:` at `:325`). 1.37 is anchored in `gauntlet-design.md` (the reviewer's line). None dropped.

Seeded by Task 2, kept (the reviewer did not return it):

**1.06** `plan-review-design.md:264`, row A19 (the `allowed_tools` row naming this line; the `Bash(<pattern>)` form itself has no row of its own).
Text: `allowed_tools: [Task, "Bash(uv run --script *cite.py *)"]` (also `:301`, and `:170` "Bash for exactly the cite.py command above and no other command").
Finding: no doc under `docs/reference/archon/` shows a `Bash(<pattern>)` specifier in `allowed_tools` (`workflow-language.md:621-643` lists plain tool names). PROBES.md section P3: `archon validate` accepts the specifier, but at runtime Bash is removed entirely ("No such tool available: Bash"), not limited to matching commands. The defense can run no command, `cite.py` included, so the cite check cannot run and the confinement the design builds on it does not exist. A `Bash(...)` rule set through `settings`/permissions was not tested.

From the reviewer:

**1.28** `plan-review-design.md:294`, rows H29, S9 (also `:321`; `spec-review-design.md:351`, `:378`). High.
Text: `:91-92` "mode "state" inside the loop also passes INPUTS_START, the latest tried round when the run began ($docket-in.output.start)"; but `:294` and `:321` pass only `with: { mode: state, slug: <slug> }`.
Finding: without START the ledger cannot compute "next" (`:106`) or "run_rounds" (`:111`). If START defaults to 0, a rerun counts LEADING reviews and rounds from earlier runs: slots start past p1, `vacate` can cancel a fresh run on its first round, and the cap fires early. If START is recomputed on each call, the slot never moves after LEADING and the cap and vacancy never fire. Spec review copies the omission (`spec-review-design.md:351`, `:378`; same finding as 1.41).

**1.29** `plan-review-design.md:409`, row P1 (also `:150-151`, `:397-398`). High.
Text: "A rerun on the same task starts the sessions afresh and continues the rounds from the files."
Finding: intake's file route reuses an existing `gauntlet/tasks/<slug>.md` (`gauntlet-intake-design.md:159`, "task is that path, nothing copied"), so a fresh run can reach plan review for a slug whose plan is already approved. `state` returns latest+1 owed to the defense, the run pays for a full new hearing, then `enter`'s `cp -n` finds `approved/<slug>.txt` and exits non-zero, failing the run. No node reads "already approved" from the ledger (CLAUDE.md 1.3, 1.4). Same shape as 1.44 for spec review.

**1.30** `plan-review-design.md:95`, row S9 (also `:71-76`, `:26`, `:126`). Medium.
Text: "A plan is cited when it holds no "[cite:" marker."
Finding: a substring test, while `cite.py` uses a marker grammar `[cite: <path> | <quote>]` and does not say how it treats text that does not fit it. A malformed marker (`[cite: a.py]` with no `|`) or a resolved quote copied from a code line containing `[cite:` leaves `cite.py` exiting 0 while the ledger still says owed `defense`. `screen` and every prosecutor are skipped, `case` is "none", nobody asks the owner, and each iteration spends a fresh Opus `defend` turn until `max_iterations: 200` fails the run, against `:26` "the loop never ends on max_iterations".

**1.31** `plan-review-design.md:94`, rows S9, S7. Medium (CLAUDE.md 1.4).
Text: "read from the first line of <slug>.review.N.txt, "Verdict: <verdict>". Any other first line: exit 1 naming the file."
Finding: the shared core matches leniently, "by the longest known name the text after `Verdict: ` starts with" (`spec-review-design.md:31`). Plan review's exact match fails the whole run on a prosecutor formatting slip such as `Verdict: REJECTED - three flaws` or a bold first line, where the round could go back to the prosecutor. The two ledger forms parse the same file differently.

**1.32** `plan-review-design.md:325`, row H29 (also `:323`, `:104-106`, `:419`, `:28`). Medium (CLAUDE.md 1.3, 1.4).
Text: `vacate` ... `when: "$ready.output.next == 'vacant'"`; `:419` forbids "any other bound on the hearing but `max_iterations: 200`".
Finding: `filing` returns `next: "defense"` whenever the defense owes, so a vacancy shows only in `ready`, after `defend` and `cite`. After the twelfth LEADING review the next iteration still runs a full Opus defense repair turn with detectives that nothing reads before the cancel; if that LEADING also reached the stretch guard the owner is asked first and the answer is discarded. The vacancy cancels the run without asking the owner, which contradicts the Homes row at `:419`.

**1.33** `plan-review-design.md:310`, internal to plan-review-design.md (CLAUDE.md 1.4). Medium.
Text: "`cite` # the plan reaches the prosecutor only resolved; an error fails here".
Finding: the ledger already returns an uncited plan to the defense ("owed": defense, `:103`) and the defense role already handles "Plan N already there and unresolved: fix it" (`:155`), so the loop would correct an unresolved marker itself. Failing the whole run on one is a stop on a technicality. With 1.06 in force (the defense has no Bash) every unresolved marker reaches this node.

**1.34** `plan-review-design.md:137`, row H27 (also `:397`). Medium.
Text: `{ "plan": "<slug>.N.txt", "summary": "<slug>-summary.N.md" }` "for the latest round N with a summary"; `enter` reads `$close.output.plan`.
Finding: the spec review design gives `{ outcome, file, summary }`, "for the latest ruling whose decision is an OwnerCase "ends"" (`spec-review-design.md:113-115`, `:124`), and states "`enter` and `handoff` read `$close.output.file`" (`:470`). The plan review design is not amended: its YAML reads a field the shared core never prints, and the two designs pick the closing round by different rules.

**1.35** `plan-review-design.md:259`, missing contract: where a phase block gets its slug (also H29; `:287`, `:294`, `:314`, `:321`, `:345`, `:363`, `:379`, `:393`). Medium.
Text: `with: { mode: state, slug: <slug> }`; the block's only input is `task` (`:250-252`).
Finding: only the `open` prompt names the slug ("slug = its file name without .md", `:266`) and no node outputs it. `docket-in`, the entry node, needs the slug before any agent runs, and a `with:` binding cannot take a basename. Every ledger node and `cite`'s path binds a value nothing produces. Spec review avoids the gap only for `handoff.ts`, which derives the slug from `INPUTS_TASK` (`spec-review-design.md:285`); same finding as 1.42.

**1.36** `plan-review-design.md:178`, rows R2, R4 (no row holds what a sworn-in reviewer reads; also `:179`, `:189`). Low.
Text: "read the task file, every ruling and every earlier review except OBJECTION: LEADING and SCREENED ones; read no earlier plan."
Finding: the spec review's amended arbiter reads "the latest block and review only when the latest verdict is neither `OBJECTION: LEADING` nor `SCREENED`" (`spec-review-design.md:263`). In plan review a slot forked after a retirement, or any slot on a rerun, never read the plan an earlier review demanded clarification of, so it cannot tell whether the new plan "drops or changes a part to avoid a demand" (`:189`) and the two-NON-RESPONSIVE owner call cannot fire there.

**1.37** `gauntlet-design.md:23`, rows H4, H14, A1, S13 (copy-list bullets `:23-28`). Low.
Text: "Each description invites direct use" (`:23`); "`worktree: enabled: false` ... in ... `plan-review/plan-review.yaml`" (`:24`); "`plan-review/scripts/guard.ts`" (`:25`); "Plan review's and spec review's declare none" (`:26`); "Inline `script:` handoffs that print an input: 2, plan review's" (`:28`).
Finding: the plan review design already contradicts each: `:244` "Not for direct use", `:239` "declares no `worktree:` and holds no guard node", `:12` "plan review holds none", `:406` `output_format` on `handoff`, `:404` reading `INPUTS_TASK`. The gauntlet design's "changes" at `:110-121` are no-ops on plan review, and the two designs disagree on what this file holds (same copy-list disagreement as 1.18).

## 6. spec-review-design.md

Source: opus `cad-reviewer` dispatch saved as `.planning/phases/1/reviews/pass2-spec-review.json` (10 findings; 3 marked blocker). Anchors checked with `sed -n`: 10 of 10 hold the quoted text; none corrected, none dropped. For 1.40 the ledger write is node `record` at `:340-341`.

Seeded by Task 2 from the probe record, kept (the reviewer did not return it):

**1.03** `spec-review-design.md:361`, row A10.
Text: "sandbox: <enabled; filesystem writes allowed only under gauntlet/scratch/ of the checkout>". Also `:482`, `:499`.
Finding: PROBES.md section P1: there is no pure write allow-list. `filesystem.allowWrite` is accepted but only adds writable paths; the checkout stays writable (a direct and a sub-agent `echo > outside.txt` both succeeded). Confinement holds only with `denyWrite` listing every other path (deny beats allow), and it does reach the Bash of a sub-agent spawned from the node. The design's form cannot confine the spiker to `gauntlet/scratch/` as written, and a new top-level file not on a `denyWrite` list stays writable. Globs in `denyWrite` were not tested. The documented keys are `workflow-language.md:250-261`. `:499` already tells the builder to stop and report if the sandbox cannot limit the writes.

From the reviewer:

**1.38** `spec-review-design.md:338`, row A15 (also `plan-review-design.md:281`). Blocker.
Text: `until_bash: '[ "$bench.output.decision" = "approve" ] || [ "$bench.output.decision" = "confirm" ]'` over a wait whose own `when: "$docket.output.ask == true"` (`:434`) skips it on most rounds.
Finding: `loop-nodes.md:695-697` "A skipped wait has no output, so an `until_bash` that reads a wait its own `when:` can skip fails the group." Round 1 with ANOTHER PASS and attempts < 5 gives case none and ask false, `bench` is skipped, `until_bash` reads a skipped wait, and the hearing group fails: spec-review and gauntlet-run fail on an ordinary revise round. `plan-review-design.md:281` has the same form.

**1.39** `spec-review-design.md:338`, row A15 (also `plan-review-design.md:281`). Blocker.
Text: the same `until_bash` wraps the substituted reference in double quotes.
Finding: `loop-nodes.md:667-670` "Archon already single-quotes a substituted value, so `"$review.output.decision"` compares `'approve'` with the quotes included and never matches". When the owner picks approve on a READY round, or confirm on an INVALID round, the test compares `'approve'` with `approve` and is false; the loop never ends on approval, each answer allows one more iteration (`workflow-language.md:773`), and the speccer files another round after every approval.

**1.40** `spec-review-design.md:115`, row H27 (also `:341`, `:448`; `plan-review-design.md:137`). Blocker.
Text: `close` returns its result "for the latest ruling whose decision is an OwnerCase "ends"".
Finding: a ruling is written only by node `record` (`:341`, `when: "$LOOP_PREV.bench.output.decision != ''"`) at the start of the NEXT iteration. When the owner approves or confirms, `until_bash` ends the loop, no next iteration runs and the ending ruling is never written. `close` finds no ending ruling, `enter` (`:448`) does not copy, and `handoff` reports outcome "" with spec "" for an approved spec. The core also replaces plan review's working close rule ("latest round N with a summary", `plan-review-design.md:137`), so plan review breaks the same way once it runs on `rounds.py` (`:124`).

**1.41** `spec-review-design.md:351`, row H29 (also `:378`, `:90`, `:98`, `:23`). High.
Text: `:90` "mode "state" inside the loop also passes INPUTS_START"; `:351` and `:378` pass only `with: { mode: state, slug: <slug> }`.
Finding: no `start: $docket-in.output.start`. On a rerun of a slug with 12 earlier LEADING reviews, if start is None and read as 0, `ready` says next = vacant and `vacate` cancels the new run at once, against "A rerun starts again at arbitrate-1" (`:23`); old rounds also fill run_rounds so the cap fires early. If None means "latest tried round", each call resets start: slot stays a1 after a LEADING and run_rounds stays 0. Same finding as 1.28.

**1.42** `spec-review-design.md:390`, rows H26, H29 (also `plan-review-design.md:314`, `:337`). Medium.
Text: `with: { file: gauntlet/specs/<slug>.$ready.output.round.txt }`; `:293` bars `$INPUTS` outside prompts and `bash:`.
Finding: every ledger `with:` passes `slug: <slug>` and `screen` builds a round-file name, but no node of the block outputs the slug (the state output at `:95-97` has none) and the Homes row at `:476` assigns round-file names to `rounds.py` only. The YAML cannot be built without a new state field or a node outside the design. Same finding as 1.35.

**1.43** `spec-review-design.md:359`, internal to spec-review-design.md (also `:482`, `:483`). Medium.
Text: `allowed_tools: [Task, Bash]  # Bash for the spikers; the role forbids the speccer's own Bash`.
Finding: the speccer itself holds Bash and only its prompt keeps it from using it, against the Homes rows "the speccer or any other agent running Bash" (`:482`) and "any role reaching files by a built-in tool other than the spiker's Bash" (`:483`). The speccer can `cat src/...` or write under `tests/` through its own Bash and bypass `speccer.mcp.json`; per 1.03 the `file` sandbox does not limit writes to `gauntlet/scratch/`.

**1.44** `spec-review-design.md:449`, row P2 (CLAUDE.md 1.3, 1.4; also `:59`, `:215`). Medium.
Text: `enter`: "cp -n gauntlet/specs/$close.output.file to gauntlet/specs/approved/<slug>.txt ... either target present: exit non-zero naming it"; `:215` "Spec files already there: needed is true".
Finding: a fresh run on a task whose spec was already approved hears the whole spec again, then fails at `enter`. The speccer's opening rule and the ledger (round = latest tried + 1) have no branch for an existing `approved/<slug>.txt`. After an earlier run approved the spec and stopped in a later phase, gauntlet-run on the same task spends Opus rounds, the owner approves again, `enter` exits "target present", `handoff` is skipped and the run stops over a file that already holds the approved spec. Same shape as 1.29.

**1.45** `spec-review-design.md:277`, row F4 (also `:273`, `:53`, `:370`). Low.
Text: "No agent can reach `gauntlet/specs/approved/` or `gauntlet/scratch/` through the fence"; `:273` gives `speccer.mcp.json` `FENCE_READ` `.`.
Finding: the speccer, and a spiker holding the same server's read tools, can call `mcp__fence-files__read_file` on `gauntlet/scratch/<slug>/...` or `gauntlet/specs/approved/<slug>.txt` and the fence allows it. A builder or fence test that pins the stated rule finds it false. (`:53` "No other agent reads it" has the same exposure.)

**1.46** `spec-review-design.md:423`, internal to spec-review-design.md (also `:161-162`, `:251`). Low.
Text: `prompt: <round $case.output.round; verdict $case.output.case>`.
Finding: `$case.output.case` takes the values "review" or "invalid" (`:161-162`), while the reporter role (`:251`) takes "its verdict, READY or INVALID" and branches on READY. On a READY round the reporter gets "review", a value its role does not name.

**1.47** `spec-review-design.md:470`, row H27 (also `plan-review-design.md:400-405`). Low.
Text: "`enter` and `handoff` read `$close.output.file`. The plan review design is otherwise unchanged."
Finding: plan review's `handoff` (`plan-review-design.md:400-405`) depends on [open, enter], reads no close output and builds the plan path itself. The builder of spec-review step 7 cannot make it read `$close.output.file` without changing its `depends_on` and script body; the design specifies no such change while claiming nothing else changes.

## 7. worktree-cut-design.md

Source: opus `cad-reviewer` dispatch saved as `.planning/phases/1/reviews/pass2-worktree-cut.json` (9 findings). Anchors checked with `sed -n`: 9 of 9 hold the quoted text; none corrected, none dropped. Where a quote wraps (1.48 at `:117-118`, 1.51 at `:159-160`, 1.55 at `:152-153`) the anchor is the line holding its first words.

**1.48** `worktree-cut-design.md:117`, rows H16, H17, H18. High.
Text: node `cut` prints "branch, base and uncommitted from $pin.output, the rest from $tree.output"; `:168-169` the tree's `handoff` takes "branch from git branch --show-current"; Homes `:194` "the tree run reads it from git".
Finding: `cut` takes `branch` from pin's predicted name and drops the tree's real branch, and no node checks the two match (also `gauntlet-design.md:155`). If Archon's naming differs from pin's `norm`, Archon finds no local branch with that name and cuts the tree from `origin/<baseBranch>`, a start point `:195` forbids. Writing and the mend commit on the real branch; landing gets pin's empty branch at base (`gauntlet-design.md:82`), `onto` sees an ancestor, `merge --ff-only` does nothing and the run reports `landed`; `archon complete <pin branch>` then targets the wrong branch and the work never reaches the checkout.

**1.49** `worktree-cut-design.md:161`, rows H20, P8. Medium (CLAUDE.md 1.3).
Text: node `baseline` runs the full `GAUNTLET_TEST_COMMAND` into `gauntlet/baseline/<slug>.txt`.
Finding: no node in any design reads that file. Red uses only the brief baseline (`writing-design.md:30`, `:145`; `landing-design.md:16`); `writing-design.md:14` calls the full file "unparsed, with no per-test listing" and `:526` forbids the test writer from reaching it. It travels only as a required pass-through field (`gauntlet-design.md:163`, `:222`). Every run pays a full test-suite run of up to 15 minutes on the production host for output never compared, shown or parsed.

**1.50** `worktree-cut-design.md:158`, row A27 (design text; also `writing-design.md:399`, `landing-design.md:61`, `:79`, `:146`). Medium (CLAUDE.md 1.4).
Text: "timeout: <GAUNTLET_TEST_TIMEOUT plus 60 s, in ms; 960000 when unset>".
Finding: the documented `timeout` is a fixed ms value in YAML (`workflow-language.md:93`) with no env expansion, so the builder can only write a literal, in practice 960000. A repository setting `GAUNTLET_TEST_TIMEOUT: "1800"` with a 1200 s suite has `baseline` killed at 960 s and the tree run fails though the repository's own limit was not reached. The bash body already bounds the command with `timeout -k 10 "${GAUNTLET_TEST_TIMEOUT:-900}"`, so omitting the node timeout loses nothing.

**1.51** `worktree-cut-design.md:159`, rows P11, H20 (also `writing-design.md:512`, `:107`, `:502`; `landing-design.md:62`). Medium (CLAUDE.md 1.3).
Text: "GAUNTLET_TEST_COMMAND unset or blank: write the file with the one line "no test command"".
Finding: the cut carries on without a test command, but `writing-design.md:512` says "Writing needs `GAUNTLET_TEST_COMMAND` and `GAUNTLET_TEST_BRIEF_COMMAND` to be set" and `:107` says "blank: every mode exits 1 naming it". `landing-design.md:62` also exits 1 on a blank brief command while `writing-design.md:502` writes "no test command" for it. A repository with no test command pays for intake, plan review, spec review and the cut before `stage.py` exits 1. Same finding as 1.63.

**1.52** `worktree-cut-design.md:200`, row H20 (also P8). Medium.
Text: the Homes row "The test baseline | gauntlet/baseline/<slug>.txt of the tree, written once by node baseline" forbids "any other baseline file".
Finding: `writing-design.md:502` makes the same node also write `gauntlet/baseline/<slug>.brief.txt`, the file red is judged against (`writing-design.md:30`; `landing-design.md:40`, `:64`; `gauntlet-design.md:156`, `:194`). A checker enforcing this Homes table rejects writing:step 8's brief file, the only baseline any red check reads; the design never gives the brief file a home.

**1.53** `worktree-cut-design.md:23`, rows H16, H17. Medium.
Text: "Node pin lists the changed tracked paths in uncommitted, the cut hands them off, and the run goes on." `:9` "because the plan and spec were reviewed against that code".
Finding: `uncommitted` (and `base`) reach no reader: the readers of `$cut.output` (`gauntlet-design.md:80-88`) take outcome, worktree, branch, line and verdict. `:9`'s reason is false when uncommitted edits exist, because plan and spec agents read the live working tree (`gauntlet-design.md:31`, `FENCE_READ=.`), and untracked new files are not listed at all (`:69` "tracked paths"). Writing builds against code the plan was not reviewed on, with no owner gate.

**1.54** `worktree-cut-design.md:111`, rows H9, H16 (also `gauntlet-design.md:156`, `:169`). Low.
Text: the `tree` node's `with: { checkout: <the checkout's absolute root>, ...`.
Finding: `checkout` has no source: pin's output (`:66-69`, `:105`) carries no checkout field and the documented standard variables include no checkout path. `workflow-builder` at step 3 has no expression to bind; a guessed literal or missing binding gives `copy-in` (`:153`) and the mend's `git -C $INPUTS.checkout` a wrong or empty root. The fix is for pin to print the checkout root.

**1.55** `worktree-cut-design.md:152`, internal to worktree-cut-design.md; row H7. Low.
Text: copy-in copies "each present in the checkout ... target absent: cp -n" (`:152-153`; also `:48` "each only when present there").
Finding: a plan or spec that is named by the input but missing in the checkout is skipped silently, and `handoff` (`:168-170`) still prints a tree path for any non-empty input. If `gauntlet/plans/approved/<slug>.txt` was moved after plan review, copy-in exits 0 and writing is handed a path to a file that does not exist, with no plan, instead of the run failing at the cut.

**1.56** `worktree-cut-design.md:197`, row H23 (also `gauntlet-design.md:354` which has no contracts row; `:343`; the reviewer cited `landing-design.md:262` for the `archon complete` line, it is at `:265`). Low.
Text: Homes row forbids "any write in the tree by a `gauntlet-run` node".
Finding: landing, a gauntlet-run block, removes the tree with `archon complete $INPUTS.branch --force` (`landing-design.md:265`; `gauntlet-design.md:354`). `gauntlet-design.md:343` forbids only "a rebase, test run or commit in the tree from gauntlet-run", the narrower rule. A checker applying this Homes table to `land/land.yaml` flags `remove`, the documented home for removing the tree.

## 8. writing-design.md

Source: opus `cad-reviewer` dispatch saved as `.planning/phases/1/reviews/pass2-writing.json` (12 findings). Anchors checked with `sed -n`: 12 of 12 hold the quoted text after one correction: 1.58 (reviewer `:127`, the quoted opening is at `:126`, the text continues at `:127`). None dropped. Where the reviewer cites a range, the anchor is the line holding the quote.

**1.57** `writing-design.md:356`, row H29 (also A18; `:353-355`, `:96`). High (CLAUDE.md 1.4).
Text: `cancel: "Twelve OBJECTION: LEADING verdicts passed the screener on revisions in this run; no reviewer is left. The run stops."`
Finding: writing keeps the hearing's slot retirement and its vacancy cancel, but its reviewer is one `context: fresh` node (`review-plan`/`review-spec`, `:443-452`; "tried by a fresh reviewer", `:9`). There are no slot sessions to contaminate; nothing is retired, yet the counter still cancels the whole tree run. Over a long run the reviser draws 12 LEADING reviews, each fixed by the next round; `rounds.state` returns `vacant`, `vacate` cancels gauntlet-tree, and every committed block is thrown away.

**1.58** `writing-design.md:126`, row S5 (write/scripts/stage.py; also `:127`, `:164`). High.
Text: "a case for the juror: the latest blocks file holds a contest or commit-failed; the latest run is red; the latest seal exit is not 0; a writing ruling newer than the latest verdict."
Finding: only the last trigger is bounded by "newer than the latest verdict", and the rule takes precedence over `divvy` and over "the latest cut has an unrun wave". After the juror rules TESTS or CODE the same older contest, red run or seal still matches, so `state` returns `juror` again and never reaches `divvy`. The suite "pins each rule of `state` in its precedence" (`:164`), so the as-written rule gets built and tested. Each iteration spends an opus juror call writing a fresh verdict until `stalled` asks the owner, whose reply sends it to the juror again.

**1.59** `writing-design.md:28`, internal to writing-design.md; missing contract: coverage of the approved spec and plan across cuts (also `:130`, `:138`, `:175-176`). High.
Text: "A later cut covers only what its cause affects."
Finding: `state` reads only the latest cut's first unrun wave (`:130`), so a cut that answers a verdict or a revision drops every unrun wave of the cut it replaces. The only coverage check is "a step of an uncommitted earlier block missing from a code cut" (`:138`); no check exists for spec ids of unwritten test blocks, and a missing test never turns a run red. Cut 1 has test waves W1, W2 and code wave W3; a contest in W1 ruled TESTS yields a cut 2 of the contested tests only; W2 and W3 never run, and the run seals as `written` with approved specs untested.

**1.60** `writing-design.md:407`, row H33. High.
Text: "`git status --porcelain` empty: write ... "exit=0", "nothing"."
Finding: every writer commits its own block through `commit`, which refuses any recorded path left out of `paths` (`:71-72`), so the tree is normally clean at `seal` and no `<slug>: final` commit is made. This contradicts `gauntlet-design.md:247` (`seal` "commits with `git commit -F -`", message carrying the plan summary and the revision summaries; home `:350`) and `landing-design.md:205` ("Mend commits sit on top of `<slug>: final`"). Landing's gate shows commit messages (`landing-design.md:9`, `:373`), so the owner never sees the summaries. Related to 1.19.

**1.61** `writing-design.md:151`, internal to writing-design.md (S5; also `:127`). Medium (CLAUDE.md 1.3, 1.4).
Text: "stalled (verdicts and rejected cuts since the latest writing ruling >= 5); cap (moves since start >= rounds.CAP)" and juror case "a writing ruling newer than the latest verdict".
Finding: the owner's reply to `stalled` or `cap` is written as a writing ruling, which always opens a juror case even when nothing is red or contested, and the juror has no "carry on" verdict: it must pick TESTS, CODE, SPEC, PLAN or DEFECTIVE. `stalled` also counts verdicts that each fixed their red, so a healthy run with 5 rulings pauses for the owner. After `cap` every iteration asks and then calls the juror. The opus juror invents a verdict and triggers a needless cut.

**1.62** `writing-design.md:330`, internal to writing-design.md (rounds.CAP; S7, S5; also `:29`). Medium.
Text: "max_iterations: 200  # rounds.py CAP; from 200 moves every iteration asks, so this never fails the run".
Finding: revise and review iterations write no move (moves are only `gauntlet/write/` files, `:29`; rounds go to `gauntlet/revisions/`), and `cap` counts moves while rounds' own cap counts run rounds. Iterations equal moves plus about two per revision round, so 200 iterations can pass with neither count at 200. `loop-nodes.md:203-205` says the node then fails: a run with 150 moves and 25 revision rounds reaches iteration 200 with no ask pending, and loop `work` fails gauntlet-tree and gauntlet-run after all the work is done.

**1.63** `writing-design.md:107`, rows P11, H20 (also `:512`, `:502`). Medium (CLAUDE.md 1.3).
Text: "`GAUNTLET_TEST_COMMAND` or `GAUNTLET_TEST_BRIEF_COMMAND` blank: every mode exits 1 naming it."
Finding: the cut design treats a blank command as supported ("write the file with the one line "no test command"", `worktree-cut-design.md:159-160`) and writing's own brief baseline does too (`:502`). Writing then fails at `open`, the first node of phase 5, after intake, plan review and spec review spent their tokens; nothing earlier, such as the run's guard, checks the variable. Same finding as 1.51.

**1.64** `writing-design.md:152`, row H28 (docket output read by bench; also `:148-151`, `:331`, `:479`). Medium (CLAUDE.md 1.4).
Text: "stalled and cap offer one option, reply. end follows the first rule of state."
Finding: `docket` can return `ask` true together with a non-empty `end`, but `bench` waits before `until_bash` ends the loop, and the reply is then discarded. If the 5th verdict since the last ruling is DEFECTIVE, `docket` returns case stalled, ask true and end defective: the owner is asked to reply to a stall of a run that has ended. The same happens when `cap` is reached on the iteration where `seal` succeeds.

**1.65** `writing-design.md:272`, rows F8, P12 (also `:256`). Medium.
Text: `FENCE_READ=tests:gauntlet/specs/approved plus :$GAUNTLET_TEST_BASE when set`; `:256` test-writer.md "Write a test for each spec of the block, in the block's paths, as docs/testing.md or the repository's testing policy".
Finding: the test writer's fence does not cover `docs/testing.md`, so it cannot read the policy it is told to follow, while the arbiter's fence (`spec-review-design.md:274`) and writing's reviewer-spec fence (`:309`) both list `docs/testing.md`. The writer gets a PermissionError, writes tests without the policy's rules, and the reviewer and juror judge against a policy it never saw.

**1.66** `writing-design.md:295`, rows F9, P14 (also `:13`, `:18`, `:187`, `:529`). Medium.
Text: `fence-checks | FENCE_TEST_COMMAND=$GAUNTLET_TEST_COMMAND`; `:13` "`fence/checks.py`, which runs `FENCE_TEST_COMMAND` and returns its last 200 lines, tracebacks included".
Finding: the coder's blindness to `tests/` is the design's stated goal (`FENCE_HIDE`, `:18`; Homes `:529`; the juror "quotes no spec text or test source", `:187`), yet the coder's own check tool returns full tracebacks, which print the failing test's source lines and assertion values. The coder runs `fence-checks` after a pytest failure and sees test source `FENCE_HIDE=tests` was meant to hide.

**1.67** `writing-design.md:337`, internal to writing-design.md (S5; also `:154-155`). Low.
Text: `with: { mode: record, start: $open.output.start, round: ..., case: ..., decision: ..., text: ... }` against `:154` `record(move: int, round: int, case: str, ...)` and `:155` "stalled and cap: writes <slug>.ruling.<move>.txt".
Finding: node `record` passes no `move`. On the owner's reply to a `stalled` ask `record` runs with `INPUTS_MOVE` unset, so it has no N for `<slug>.ruling.<move>.txt`; it fails or writes a misnamed file that `state`'s "ruling newer than the latest verdict" cannot order.

**1.68** `writing-design.md:428`, internal to writing-design.md (R12 reviser.md; also `:197-198`, `:117`). Low.
Text: `prompt: <round $state.output.round; kind $state.output.kind; plan files; spec files>` against reviser.md "Inputs: round N, kind (plan or spec), the tree path the round answers, ... the latest review (may be "")".
Finding: `state` gives no answers path for `revise` (`cause` is defined for divvy and juror only, `:117`), so the reviser must find for itself the path it writes on its `Answers:` line. After a PLAN verdict it cannot tell whether it answers verdict N or `approved/<slug>.revK.txt`; a wrong `Answers:` line breaks `state`'s "no spec round answering it closed" test and the revision stays owed.

## 9. landing-design.md

Source: opus `cad-reviewer` dispatch saved as `.planning/phases/1/reviews/pass2-landing.md` (7 findings; 1 blocker). Anchors checked with `sed -n`: 7 of 7 hold the quoted text; none corrected, none dropped. The reviewer listed what it dropped itself (skip cascade on the `still` route, `land`'s branch-absent route, record-copy collisions, the brief-versus-full test command in the mend's fence-checks, multi-iteration fixtures, anything covered by 1.01-1.12); those are not findings and are not recorded here.

**1.69** `landing-design.md:47`, rows H22 (also H17; `:30`, `:55`, `:195`, `:205`, `:368`). Blocker.
Text: "moved = not (git merge-base --is-ancestor head tip)"; `:30` "a resume rebases, verifies and mends against the checkout as it then stands".
Finding: once the first pass has rebased the branch, the checkout's head is an ancestor of tip, so on any resume `onto` (always_run) prints `moved` false. `test-tree` is skipped, and the skip passes on to `red`, `test-head`, `confirm` and `repair` (`workflow-language.md:83`, `:324-332`). (a) After a rebase conflict (`:55`) the owner runs `git rebase --continue` and resumes: the resolved rebase is never tested and `handoff` prints "Checkout not moved past the tree's base: not rerun." (b) If any repair node fails and the owner resumes, the confirmed red is never mended and `handoff` hands off `ready` with the same false line. In both cases `land` shows that line at `gate` and the owner lands an untested or still-red branch. The claim at `:205` that "a resumed `repair` starts at iteration 1" never comes true because `repair`'s `when:` reads a skipped `confirm`. The Homes rule at `:368` forbids "a test run when the checkout's HEAD is in the branch's history", writing the same mistake into the rules.

**1.70** `landing-design.md:172`, row H34 (also H22; `:143-147`, `:326-327`, `:55`). High.
Text: "First that holds. hear left: end "left". recheck not red and review SOUND: end "done"."
Finding: `pose` ends the repair without checking that the mender committed. `mend-code` returns `commit-failed` with its edits left uncommitted; `retest` (`:143-147`, `none_failed_min_one_success`) tests the dirty tree and `recheck` finds it not red. `mend-review`'s UNSOUND list (`:326-327`) does not cover a mend that was never committed, so the reviewer can rule SOUND, `pose` ends "done", `handoff` prints "Mended on <head>: no new failure.", and `land` fast-forwards a branch lacking the tested fix. On a later resume `rebase` meets the dirty tree and git refuses ("cannot rebase: You have unstaged changes"), while the stop message at `:55` tells the owner to run `git rebase --continue` with no rebase in progress.

**1.71** `landing-design.md:147`, row P9 (also `:63`, `:30`, `:116`). Medium.
Text: "as test-tree, unconditionally, into gauntlet/mend/$INPUTS.slug.run.$onto.output.head.<tip>.txt".
Finding: when the mender does not commit (`contest` or `commit-failed`) tip is unchanged, so `retest` writes to the same path as `test-tree`'s file (`:63`) and overwrites it, possibly with a run on a dirty tree. That breaks the promise at `:30` that files are "keyed by the commits they ran on, so a rerun on the same commits reuses its file", and changes what the juror's fallback `$test-tree.output.file` (`:116`) shows from then on.

**1.72** `landing-design.md:143`, internal to landing-design.md (CLAUDE.md 1.3; also `:157`, `:327`). Medium.
Text: `:143` "retest ... skipped when no mender ran"; `:157` "review # every mend read before it can end the repair"; `:327` "UNSOUND when ... leaves the tree red".
Finding: after a `contest` nothing was mended, yet `retest` runs a full brief-suite run (up to 900 s) on the same commit and `review` spends an agent session. When `recheck` is red the review's verdict is fixed in advance (UNSOUND by its own role) and `pose` ends on `recheck` alone, so that agent call buys nothing the sequence needs. The reviewer's fix: gate `retest` and `recheck` on `outcome == committed`, and `review` on `recheck` not being red.

**1.73** `landing-design.md:172`, internal to landing-design.md (also `:116`, `:129`, `:173-174`). Medium.
Text: "case = newline-separated tree paths the next juror reads: the latest run file when red ..." (`:172-173`) and `:116` "the case: $LOOP_PREV.pose.output.case, or $test-tree.output.file when empty".
Finding: in an iteration where the juror rules DEFECTIVE, `retest` and `recheck` are skipped, so `pose` has no "latest run file" and no red to test, and the case comes out empty or undefined. After the owner's reply the next juror falls back to `$test-tree.output.file`, the run from before any mend, even when an earlier iteration already committed a mend; the same happens at iteration 1 after a resume. The juror and the mender (`:129` "the latest run file") work from a red that no longer matches the branch.

**1.74** `landing-design.md:178`, row H31. Medium (CLAUDE.md 1.4).
Text: "options [ { id: reply, label: "Guide the juror (your guidance in the text)" }, { id: leave, label: Leave } ]".
Finding: the owner cannot accept the rebased tree or ask for a rerun. A flaky or environment-only failure on the rebased tree is red by `.shared/red.py`; the juror cannot mend it and rules DEFECTIVE; the owner can only send guidance into a loop that cannot reach "not red and SOUND", or `leave`, which ends the run with no landing and leaves the record copy and tree removal to the owner.

**1.75** `landing-design.md:373`, row H31 (also `:175-176`, `:98`). Low.
Text: "`repair`'s `ask`, only on DEFECTIVE or 5 verdicts since the latest reply".
Finding: omits the third ask condition `pose` states at `:175-176` ("or hear.n >= 200") and `:98` relies on ("from iteration 200 every iteration asks, so the bound never fails the run"). A builder working from the Homes table drops the ask that keeps `max_iterations` from failing the run.

Withdrawn by Task 2:

**1.05** `landing-design.md:11`, row A5. Dropped: the quoted text "`fence/files.py` and `fence/checks.py` root at `CLAUDE_PROJECT_DIR`, the agent's folder" states only the part PROBES.md section P2 confirms (the variable is the cwd when the config gives none). The false clause is in `gauntlet-intake-design.md:117` (finding 1.04).

## 10. Groups

Task 5. Each group is one disagreement (or one internal snag), keyed to `contracts.md` rows; "Members" lists the findings it holds, "Where" every design line the disagreement occurs at, "Options" each value the designs give, cited, as the choices a ruling takes. Every finding id appears in exactly one group below. Rows H35 to H38 were added to `contracts.md` by this task under D-01: each is a contract two or more designs name that no row held (the `$INPUTS` positions in a phase block's `with:`, the slug a phase block gives its ledger nodes, the tree-removal node, the `vacate` nodes). Other findings that carried "missing contract" or no row (the reviewer's cross-design read sets, coverage across cuts) cite an existing row or are marked internal because one design names them alone, or because two existing rows already hold both values.

Options: option (a) is the designs' own current text unless it says otherwise; an option that cites no design line is a proposal from the finding or from this task, offered for the ruling to accept or replace, and is not a value any design gives.

Copy-list map (D-06): the 12 bullets of `gauntlet-design.md:23-34`, in order. B01, B02, B03, B04, B05, B06, B07, B10, B11 and B12 are resolved by the designs and sit in group G-12 with the resolving line quoted. B08 (places a node runs; its `CLAUDE_PROJECT_DIR` clause) is judged by G-02. B09 (fences reading `gauntlet/failed/`) is judged by G-03. The landing design's "Decisions for the owner" (`landing-design.md:388`) is group G-45 (D-10).

Rulings (Plan 3 Task 1, continuation). Each group below carries one `Ruling:` line, the ruling as RULINGS.md states it, with the route it took and who ruled. Authority: the owner ruled G-12 and G-45 through the ask-user seam. For the other 48 groups the owner answered: "This is utterly illegible to me, I have no clue what I am being asked to judge, and highly suspect that most of these are not questions but actually just asking for permission to take the obvious route." Under CLAUDE.md 3.2 the main session took the proper fix for those 48 and names each as `main session (3.2)`. The 27 load-bearing groups went through `/cad-decision-review` (DECISION-REVIEW.md, D-05). Where that review adjusted a ruling, an `Amended at decision review:` line follows the `Ruling:` line and states whether it adds to the ruling or replaces it; a replacing amendment is the ruling Task 2 applies. Probe results cited are in PROBES.md.

**G-01** The fence env route (rows A11, F8, F9, F10, F11).
Members: 1.01, 1.02.
Where: `writing-design.md:22`, `:268`; `landing-design.md:15`, `:332`; `mcp-servers.md:190-194`, `:210-211`.
Statement: two designs build the `FENCE_*` values of the test-running fences from the repository's `env:` in an `sh -c` launch line, a route the vendored MCP guide does not document and the designs themselves call unmeasured or contradict.
Options: (a) the designs' form, `FENCE_TEST_COMMAND=$GAUNTLET_TEST_COMMAND`, `FENCE_TEST_TIMEOUT=${GAUNTLET_TEST_TIMEOUT:-900}`, `:$GAUNTLET_TEST_BASE` when set, read from the repository `env:` (`writing-design.md:268`, `landing-design.md:332`), which `landing-design.md:15` says reaches bash nodes only and `writing-design.md:22` calls unmeasured; (b) the documented route, `env` values in the config expanded from Archon's own process environment with codebase env on Codex nodes only (`mcp-servers.md:192-194`) and `command` and `args` never expanded (`:211`); F1 to F7 already fit (b).
Route: load-bearing, D-11 in CONTEXT.md.
Ruling: (b) the documented route: MCP `env` values expanded from Archon's process environment (`mcp-servers.md:192-194`), never `command`/`args`; the test fences F8-F11 move to it. [route: load-bearing, D-11, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling): the fences take no test value from MCP `env` and no `sh -c` launch line. A bash node, which sees the repository `env:`, writes the resolved values (test command, brief command, timeout with its 900 default, test base) once per tree run to a fixed file under `gauntlet/`. `fence/checks.py` reads that file from a path fixed relative to its root. F8-F11 launch as plainly as F1-F7, and the repository `env:` stays the one home. This uses only documented features: bash nodes see the repository env, and fence configs use plain `command`/`args`.

**G-02** `CLAUDE_PROJECT_DIR` and the fence root (row A5; copy-list bullet B08).
Members: 1.04, 1.05 (withdrawn, kept here so its id sits in a group).
Where: `gauntlet-intake-design.md:117`; `plan-review-design.md:226`; `spec-review-design.md:269`; `writing-design.md:268`; `landing-design.md:11` (withdrawn); `gauntlet-design.md:30`.
Statement: the designs say Claude Code overrides any `CLAUDE_PROJECT_DIR` a config gives, so the fence root cannot move; the probe shows a config value wins.
Options: (a) keep the claim as written (false per PROBES.md P2); (b) restate it as a rule the pack keeps, "every config sets none", and pin it with a fence test; (c) have the fences refuse a config that sets it. B08's remaining clauses (`isolation:`, one folder per run) are documented at `workflow-language.md:2075-2083` and need no ruling.
Route: load-bearing, D-12 in CONTEXT.md.
Ruling: (b) every fence config sets no `CLAUDE_PROJECT_DIR` (PROBES.md P2: a config value wins), stated as a pack rule and pinned by a fence test; the false "overrides" clause is removed. [route: load-bearing, D-12, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling with option (c)): `fence/files.py` `_root()` (line 32) and `fence/checks.py` refuse to start, exit 2, when realpath(`CLAUDE_PROJECT_DIR`) differs from realpath(cwd). PROBES.md P2 shows the two are equal when nothing sets the variable. This is tested through the scripts' entry points with `tmp_path`, inside policy, and covers every route. The false "overrides" clause is still removed from the designs.

**G-03** What confines the speccer and the spiker (rows A10, F4; copy-list bullet B09).
Members: 1.03, 1.15, 1.43, 1.45.
Where: `spec-review-design.md:53`, `:273`, `:277`, `:359`, `:361`, `:370`, `:482`, `:483`, `:499`; `gauntlet-design.md:329`, `:348`, `:355`.
Statement: the designs state that `FENCE_HIDE`, the sandbox and the Homes rows keep the speccer and spiker out of `gauntlet/failed/`, `gauntlet/scratch/`, `gauntlet/specs/approved/` and `tests/`, but the nodes hold Bash and the speccer's fence reads `.`.
Options: (a) as written: `sandbox: <enabled; filesystem writes allowed only under gauntlet/scratch/ of the checkout>` (`spec-review-design.md:361`), which cannot confine writes (`allowWrite` only adds; `denyWrite` is needed, PROBES.md P1); (b) `denyWrite` listing every other path, globs untested; (c) take Bash from the speccer (`:359`, `:482`) and leave it to the spiker alone; reads of `failed/`, `scratch/` and `approved/` through Bash stay open under any of the three, so the Homes rows `gauntlet-design.md:348` and `spec-review-design.md:277` need rewording or the Bash reads need a fence of their own.
Route: load-bearing, D-13 in CONTEXT.md.
Ruling: (c) the speccer gets no Bash; the spiker alone holds Bash, under a sandbox whose `denyWrite` lists the paths it must not write (PROBES.md P1). The Homes rows `gauntlet-design.md:348` and `spec-review-design.md:277` are reworded to say Bash reads are not fenced. [route: load-bearing, D-13, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling; the first amendment, sandbox confinement of a shared Bash, fell to PROBES.md P4 and P6, which show `sandbox:` confines absolute literal paths only):
- Neither the speccer nor the spiker holds Bash, and neither node takes `sandbox:`.
- Both read and write through `fence/files.py`. The spiker gets `FENCE_WRITE=gauntlet/scratch/<slug>`. `FENCE_READ` lists the folders each one may read, and leaves out `gauntlet/failed`, `gauntlet/specs/approved` and `tests/`; the speccer's list also leaves out `gauntlet/scratch`. Unlisted folders cannot be read, so `FENCE_HIDE` is not needed.
- The spiker runs its experiments through a fence tool with cwd `gauntlet/scratch/<slug>`, as `checks.py` runs the test command. This replaces `spec-review-design.md:17` ("`checks.py` does not serve them").
- Homes rows `gauntlet-design.md:348` and `spec-review-design.md:277` keep their fence wording, because no Bash read is left open.
- Grounding: `mcp-servers.md:278` and `:492` document `mcp` plus `allowed_tools` with no Bash as "Sandbox to MCP only", where the agent "cannot touch the filesystem or run shell commands". `fence/test_files.py` and `fence/test_files_write.py` cover the fence's path confinement. PROBES.md P2 shows the root is the agent's cwd.

**G-04** `allowed_tools` spellings (row A19).
Members: 1.06, 1.07, 1.08.
Where: `plan-review-design.md:165`, `:170`, `:264`, `:301`; `spec-review-design.md:24`, `:239`, `:243`, `:359`; `writing-design.md:530`.
Statement: `Task` is renamed `Agent` (the old name silently ignored, per `archon validate`), and `Bash(<pattern>)` removes Bash entirely at runtime.
Options: (a) `[Task, "Bash(uv run --script *cite.py *)"]` as written (`plan-review-design.md:264`); (b) `[Agent, ...]` with the working probe form (PROBES.md P1) and some other confinement of the defense's Bash (a permissions rule, untested); (c) move the cite check to a node and give the defense no Bash. `writing-design.md:530` names `Task` as forbidden for a writer node and would name `Agent` too.
Route: load-bearing, D-14 in CONTEXT.md.
Ruling: (c) the cite check runs as a script node and the defense holds no Bash; every `Task` in `allowed_tools` becomes `Agent` in all designs. [route: load-bearing, D-14, reviewed; by main session (3.2)]
Amended at decision review (adds to the ruling):
- `defend`'s prompt carries `$LOOP_PREV.cite.output` (the unresolved markers and their reasons).
- A repair-only iteration counts toward the stretch guard, so the owner is asked after 5.
- `Task` becomes `Agent` everywhere it names the tool.

**G-05** Plan review's ledger: its own body or the shared core's (row S9; also S7).
Members: 1.09, 1.31.
Where: `plan-review-design.md:86-140`, `:94`, `:434`, `:436`; `spec-review-design.md:31`, `:495`.
Statement: `plan-review/scripts/ledger.py` is built by two steps in two forms, and the two forms read the verdict line differently.
Options: (a) plan-review step 3 builds the standalone body and parses `Verdict: <verdict>` exactly, any other first line exit 1 (`plan-review-design.md:94`, `:434`); (b) spec-review step 2 replaces it with the `Profile` form on `.shared/rounds.py`, matching "by the longest known name the text after `Verdict: ` starts with" (`spec-review-design.md:31`, `:495`), with plan-review step 5 told it needs that step, not step 3.
Route: load-bearing, D-15 in CONTEXT.md.
Ruling: (b) plan review's ledger is the shared `Profile` form on `.shared/rounds.py` with prefix verdict matching; plan-review step 5 needs spec-review step 2. [route: load-bearing, D-15, reviewed; by main session (3.2)]
Amended at decision review (adds to the ruling):
- The core matches verdicts after stripping markdown markup, case-insensitively.
- A first line that still names no known verdict is an owner case (ask), never exit 1.
- Plan-review step 3 writes no ledger body. Plan review's ledger is the Profile on the core, needing spec-review step 2.

**G-06** Spec review step 7 rewrites plan review's files (rows P16, R6, F6; also F7).
Members: 1.10, 1.11.
Where: `spec-review-design.md:497`, `:500`; `plan-review-design.md:211-235`, `:326-336`, `:421`, `:435`, `:436`.
Statement: spec-review step 7 edits `plan-review/plan-review.yaml` without needing plan-review step 5, and declares `plan-review/commands/screener.md` and `plan-review/screener.mcp.json` not written while plan-review step 4 writes them and the plan review design still specifies both.
Options: (a) plan review keeps its own `screen` node, screener role and fence (`plan-review-design.md:326-336`, `:211-235`) and spec-review step 7 is dropped; (b) spec-review step 7 stands, needs plan-review step 5 and step 4's screener files, and the plan review design is amended to include `screen` and drop its screener role and fixtures (`spec-review-design.md:500`).
Route: load-bearing, D-16 in CONTEXT.md.
Ruling: (b) spec-review step 7 stands, needs plan-review steps 4 and 5; the plan review design is amended to use the shared `screen` and drop its own screener role and fixtures. [route: load-bearing, D-16, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling): drop spec-review step 7. Plan-review step 5 builds `screen` as `include: screen` and needs spec-review step 5. Plan-review step 4 writes no screener role or fence. Plan review's fixtures are rewritten to stub the included node ids, and the SCREENED route fixture is kept.

**G-07** Four steps write `gauntlet-tree/gauntlet-tree.yaml` nodes (row H19; D-07's known case).
Members: 1.12.
Where: `gauntlet-design.md:146`, `:366`, `:372`; `writing-design.md:502`, `:542`; `worktree-cut-design.md` step 2.
Statement: gauntlet step 4, writing step 8 and gauntlet step 10 list overlapping node lists (`paths`, `write`, `handoff`, `baseline`, the description) for one file, ordered but with no owner per field.
Options: (a) gauntlet step 4 owns `paths` and `write`'s `brief` input, writing step 8 adds only the `baseline` brief file; (b) writing step 8 owns the `brief` field and gauntlet step 4 prints it without the baseline; (c) each step lists only the fields it adds.
Route: load-bearing, D-17 in CONTEXT.md.
Ruling: (c) each step that writes `gauntlet-tree.yaml` lists only the fields it adds. [route: load-bearing, D-17, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling with option (a)): gauntlet step 4 owns `paths` (including `brief`) and `write`'s `brief:` binding. Writing step 8 makes no edit to `gauntlet-tree.yaml`. Gauntlet step 10 lists only what it adds.

**G-08** `$INPUTS` in a phase block's `with:` (rows H35, A3, A14).
Members: 1.13.
Where: `gauntlet-design.md:121`, `:123`, `:341`; `writing-design.md:434`, `:441`, `:492`; `landing-design.md:73`, `:91`, `:155`.
Statement: the home rule allows `$INPUTS.<name>` only in prompts and `bash:`; writing and landing use it in `with:` bindings.
Options: (a) `gauntlet-design.md:121`/`:341` as written, and write/ and mend/ rewrite their `screen`, `flag`, `red`, `confirm` and `recheck` bindings; (b) widen the rule to prompts, `bash:` and `with:` (`writing-design.md:492`, `landing-design.md:73`).
Route: load-bearing, D-18 in CONTEXT.md.
Ruling: (b) the home rule allows `$INPUTS.<name>` in prompts, `bash:` and `with:`. [route: load-bearing, D-18, reviewed; by main session (3.2)]
Amended at decision review (narrows (b)): `$INPUTS.<name>` may appear in `with:` only on `include:` and `workflow:` nodes. Script nodes read block inputs from `INPUTS_<NAME>`, and the redundant bindings are dropped.

**G-09** A timeout counts as red unconditionally (row S4).
Members: 1.14.
Where: `gauntlet-design.md:290`, `:292`.
Statement: `.shared/red.py` exempts failures already present in brief or head but not a timeout already present there.
Options: (a) as written: run timed out is red (`:290`); (b) exempt a timeout when the brief or head run timed out too, as `:292` does for failures.
Route: ask-user seam.
Ruling: (b) a timeout already present in the brief or head run is not red. [route: ask-user seam; by main session (3.2)]

**G-10** The final commit by `seal` (row H33).
Members: 1.16, 1.19, 1.60.
Where: `gauntlet-design.md:247`, `:350`, `:371`; `writing-design.md:89`, `:219`, `:407-410`, `:494`, `:541`; `landing-design.md:205`.
Statement: the gauntlet design assigns `seal` a change (commit with `git commit -F -`, summaries of every round) that the writing design already holds, while writing's `seal` writes `nothing` when the tree is clean, which is the normal case, and lists summaries of rounds the owner sent back.
Options: (a) `gauntlet-design.md:247`, `:350`, `:371`: every `seal` makes the `<slug>: final` commit whose message lists the plan summary and each revision summary, and gauntlet step 9 restates what `writing-design.md:408-410` already does and is dropped; (b) `writing-design.md:407`: `seal` writes "exit=0", "nothing" on a clean tree, so with every block committed no final commit exists, and `landing-design.md:205` ("Mend commits sit on top of `<slug>: final`") and the Homes row `gauntlet-design.md:350` are reworded. Either way the summaries listed are those of rounds the owner approved, not of every SOUND round (`writing-design.md:89`, `:219`, `:494`).
Route: load-bearing, D-19 in CONTEXT.md.
Ruling: (a) every `seal` makes the `<slug>: final` commit (`--allow-empty` when the tree is clean), listing the plan summary and the summaries of approved revision rounds only; gauntlet step 9 is dropped as a restatement. [route: load-bearing, D-19, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling with (b)):
- `seal` makes no final commit on a clean tree.
- The landing gate shows the plan summary and the approved revision summaries. `state` lists the approved rounds.
- `landing-design.md:205` and `gauntlet-design.md:350` are reworded.
- Gauntlet step 9 is dropped.

**G-11** The twelve-LEADING vacancy cancel (rows H38, A18, H25, H29; also H18).
Members: 1.17, 1.32, 1.57.
Where: `gauntlet-design.md:19`, `:98`; `plan-review-design.md:323-326`, `:419`; `spec-review-design.md:380-383`; `writing-design.md:353-356`, `:443-452`.
Statement: three blocks cancel the run at the twelfth LEADING review; gauntlet-run defines no route when a child run ends cancelled, plan review detects vacancy only after a full defense turn, and writing cancels although its reviewer is a fresh node with no session to retire.
Options: (a) all three keep `vacate` as written and the gauntlet design adds the route for a cancelled `tree` or phase; (b) writing drops `vacate` (its reviewer is `context: fresh`, `writing-design.md:9`); (c) plan review computes the vacancy in `filing`, before `defend`, and asks the owner before cancelling (`plan-review-design.md:419` forbids any other bound than `max_iterations: 200`).
Route: load-bearing, D-20 in CONTEXT.md.
Ruling: (b)+(c) writing drops `vacate`; plan review computes vacancy in `filing`, before `defend`, and asks the owner before cancelling; the gauntlet design states the route for a cancelled child run. [route: load-bearing, D-20, reviewed; by main session (3.2)]
Amended at decision review (adjusts the ruling):
- `Profile.retire` becomes optional and writing sets none, so writing never sees `vacant`.
- In plan review and spec review, the ledger reports the vacancy in `filing` (before any repair turn). `vacate` reads `$filing.output` and cancels without asking.
- The gauntlet design states the route for a cancelled child run.

**G-12** The copy list (D-06) states as current what the designs have resolved (rows H13, H14, H15, A1, H1, H2, S13, H4, H5, H6, A2, A3, H7, H8, R12, S4, S5, S6, H12; seeds B01 to B07, B10 to B12; D-02 planning contradictions).
Members: 1.18, 1.25, 1.37.
Where: `gauntlet-design.md:23-34`.
Statement: ten of the twelve bullets describe copies, gaps or needs the phase designs no longer hold; the designs already resolve them, each at the line quoted.
Resolving lines: B01 standalone phases: `gauntlet-design.md:114` "included by gauntlet-run only. Not for direct use.", `gauntlet-intake-design.md:137`, `plan-review-design.md:12`, `:244`, `spec-review-design.md:15`, `:298`. B02 `worktree:`: `gauntlet-design.md:115` "No `worktree:` key.", `gauntlet-intake-design.md:221`, `plan-review-design.md:239`, `spec-review-design.md:293`. B03 guard nodes: `gauntlet-design.md:102`, `gauntlet-intake-design.md:239`, `plan-review-design.md:12`, `:423`, `spec-review-design.md:15`, `:487`. B04 hand-off contracts: `plan-review-design.md:406`, `spec-review-design.md:460-463`, `gauntlet-design.md:118-120`. B05 `$INPUTS` before `when:`: `gauntlet-intake-design.md:157`, `:164`. B06 inline handoff scripts: `plan-review-design.md:404`, `spec-review-design.md:456`. B07 writers of `approved/`: `gauntlet-design.md:228`, `writing-design.md:341`. B10 role files: `writing-design.md:19`, `gauntlet-design.md:359`. B11 comparisons against the brief baseline: `gauntlet-design.md:281`, `landing-design.md:345`. B12 copies of the tree's records: `landing-design.md:256`, `gauntlet-design.md:353`.
Planning contradictions (D-02): `PROJECT.md:31` "Intake, plan review and spec review usable standalone and as blocks of `gauntlet-run`" and `ROADMAP.md:61` (Phase 4 criterion 1, `archon workflow run intake --input file=<path>`; also the goal at `ROADMAP.md:57`) against `gauntlet-design.md:114` and `spec-review-design.md:298`.
Options: (a) the designs' value: each phase is included by `gauntlet-run` only (`gauntlet-design.md:114`), the copy list is spent, and the same commit edits `PROJECT.md:31` and `ROADMAP.md:57`, `:61` (D-02); whether the list is deleted or rewritten to what the designs now state is editorial; (b) the planning documents' value: phases usable standalone (`PROJECT.md:31`, `ROADMAP.md:61`), which reverses the "Not for direct use" descriptions at the lines above.
Route: load-bearing, D-21 in CONTEXT.md.
Ruling: (b) intake, plan review and spec review are usable standalone and as blocks of `gauntlet-run` (`PROJECT.md:31`, `ROADMAP.md:61`); the designs are changed to match, reversing their "Not for direct use" descriptions and giving each standalone phase what it needs to run on its own; the copy list is rewritten to what the designs then state. [route: load-bearing, D-21, reviewed; by owner]
Decision review (no amendment to the ruling; objection outcomes): a standalone approval is reused by a later `gauntlet-run` through the D-27 amendment (reuse of a fresh approval). The dropped `worktree:` key under `include:` raises no gate: PROBES.md P7 shows one stderr log line per load (`include.workflow_level_fields_dropped`) and nothing is sent to the owner. The standalone phase descriptions can name `gauntlet-run` as the whole-run pick, so the chat router does not choose a single phase for a whole-run request.

**G-13** Header lines in the revision files (row P3).
Members: 1.20.
Where: `gauntlet-design.md:229`, `:243`; `writing-design.md:31`, `:344`.
Statement: `enter` copies a round file that starts with `Revises:` and `Answers:` lines into `<slug>.rev<N>.txt`, which the gauntlet design says holds only the changed clauses.
Options: (a) `enter` strips the two header lines when copying; (b) the revision files keep the header and `gauntlet-design.md:243` says so, with the `Answers:` path stated to be a tree path the mend does not read.
Route: ask-user seam.
Ruling: (a) `enter` strips the `Revises:` and `Answers:` lines when copying. [route: ask-user seam; by main session (3.2)]

**G-14** Node ids of the mend's agent nodes (row H34).
Members: 1.21.
Where: `gauntlet-design.md:184`; `landing-design.md:109-112`, `:157-159`.
Statement: the gauntlet design names `mend-juror` and `mend-review` as node ids; the landing design uses `juror` and `review` with those names as commands.
Options: (a) node ids `juror` and `review` (`landing-design.md:109`, `:157`) and `gauntlet-design.md:184` reworded; (b) rename the nodes to `mend-juror` and `mend-review`.
Route: load-bearing, D-22 in CONTEXT.md.
Ruling: (a) node ids `juror` and `review`; `gauntlet-design.md:184` reworded. [route: load-bearing, D-22, reviewed; by main session (3.2)]
Amended at decision review (adds to the ruling): reword `ROADMAP.md:94` to "reaches node `juror` (command `mend-juror`)" in the same commit as the design edits (D-02).

**G-15** The Homes row "outside `gauntlet/`" (row P10).
Members: 1.22.
Where: `gauntlet-intake-design.md:238`; `gauntlet-design.md:275`, `:352`; `landing-design.md:252`; `writing-design.md:294`.
Statement: the intake Homes table forbids any Gauntlet node writing outside `gauntlet/`, while landing's merge, the coder, the mend and `seal` write tracked files.
Options: (a) the intake row is scoped to intake's own nodes (`gauntlet-intake-design.md:221`, "writes only in the run's checkout"); (b) the row is widened to name landing's `merge`, the coder fence and `seal`'s commit as the other homes (`gauntlet-design.md:352`).
Route: ask-user seam.
Ruling: (a) intake's Homes row is scoped to intake's own nodes. [route: ask-user seam; by main session (3.2)]

**G-16** Clerk's write fence (rows F5, R5).
Members: 1.23.
Where: `gauntlet-intake-design.md:86`, `:94`, `:95`, `:110`, `:182`, `:245`; `gauntlet-design.md:307`.
Statement: `FENCE_WRITE=gauntlet/tasks` lets Clerk write, copy and delete every task file; only the role's prose confines it to its own `<slug>.md`, which the Homes row calls a forbidden stand-in, and nothing checks that a chosen slug is free.
Options: (a) as written, prose confinement; (b) `FENCE_WRITE` narrowed to the slug's file once chosen (a per-turn fence or `FENCE_ONCE`), with a script node checking the slug is free before the first turn.
Route: load-bearing, D-23 in CONTEXT.md.
Ruling: (b) Clerk's write fence is narrowed to the chosen slug's file, and a script node checks the slug is free before the first turn. [route: load-bearing, D-23, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling): Clerk writes no file. Each turn outputs the draft text and the slug. A script node writes `gauntlet/tasks/<slug>.md`, refusing a slug taken by another run and feeding the refusal to Clerk's next turn. Clerk's fence becomes read-only. This uses documented features only.

**G-17** The guard's failure message for a tracked file (row S3; also H1, H2).
Members: 1.24.
Where: `gauntlet-intake-design.md:54`, `:56`; `gauntlet-design.md:105`.
Statement: the one message says "Add it to .gitignore and restart the run", which cannot clear a file git already tracks.
Options: (a) one message as written; (b) a second message for the tracked case naming `git rm --cached`.
Route: ask-user seam.
Ruling: (b) a second guard message for a tracked file, naming `git rm --cached`. [route: ask-user seam; by main session (3.2)]

**G-18** `from-file` on an identical occupied target (internal to gauntlet-intake-design.md).
Members: 1.26.
Where: `gauntlet-intake-design.md:158`.
Statement: any occupied target stops the run, byte-identical content included.
Options: (a) as written, exit non-zero on every occupied target but the handed-in path itself; (b) treat a byte-identical target as the task and carry on.
Route: ask-user seam.
Ruling: (b) a byte-identical occupied target is taken as the task. [route: ask-user seam; by main session (3.2)]

**G-19** The slug fixed on Clerk's opening turn (rows P6, H16).
Members: 1.27.
Where: `gauntlet-intake-design.md:7`, `:86`, `:173`, `:181`, `:199`, `:217`, `:221`; `worktree-cut-design.md:61`.
Statement: the slug must be output before any conversation and stays fixed, but the idea may be empty.
Options: (a) as written; (b) with an empty idea, Clerk asks first and picks the slug on the first reply that holds a task; (c) the slug is output on the turn the draft is written.
Route: ask-user seam.
Ruling: (c) Clerk outputs the slug on the turn it writes the draft. [route: ask-user seam; by main session (3.2)]

**G-20** The cite check (row S9; internal to plan-review-design.md).
Members: 1.30, 1.33.
Where: `plan-review-design.md:26`, `:71-76`, `:95`, `:103`, `:126`, `:155`, `:170`, `:264`, `:310`.
Statement: the ledger tests "holds no `[cite:` marker" while `cite.py` parses a grammar and fails the run on an error, so a malformed marker either loops to `max_iterations` or stops the run, where the ledger already returns an unresolved plan to the defense.
Options: (a) as written; (b) `cite.py` exits 0 and prints the unresolved markers, the ledger owes the defense until none remain; (c) the ledger tests for unresolved markers by the same grammar `cite.py` uses.
Route: ask-user seam.
Ruling: (b) `cite.py` exits 0 and prints unresolved markers; the ledger owes the defense until none remain. [route: ask-user seam; by main session (3.2)]

**G-21** The ledger's `state` mode needs `start` (row H29).
Members: 1.28, 1.41.
Where: `plan-review-design.md:91-92`, `:106`, `:111`, `:294`, `:321`; `spec-review-design.md:23`, `:90`, `:98`, `:351`, `:378`.
Statement: the design says in-loop `state` also passes `INPUTS_START`; `filing` and `ready` pass only `mode` and `slug`, so slot choice, `run_rounds` and vacancy are computed against an undefined start.
Options: (a) add `start: $docket-in.output.start` to `filing` and `ready` in both blocks; (b) the ledger derives start itself and `INPUTS_START` is dropped from the text.
Route: load-bearing, D-24 in CONTEXT.md.
Ruling: (a) `filing` and `ready` pass `start: $docket-in.output.start` in both blocks. [route: load-bearing, D-24, reviewed; by main session (3.2)]
Amended at decision review (adds to the ruling; ruling (a) stands after PROBES.md P5, owner-settled): every in-loop ledger mode (`state`, `docket`) takes `start`. The binding form is probed before this ruling is applied (PROBES.md P5). If the probe fails, `docket-in` writes the start to the ledger's own run file and every mode reads it. Probe result (PROBES.md P5): a body `with:` binds from an outer node, so the ruling (a) stands and the fallback is not needed. P5 bound the whole `$outer.output`. The field form `$docket-in.output.start` is the generic binding that `workflow-language.md:547` documents.

**G-22** Mode `close`: what it returns and from which file (row H27).
Members: 1.34, 1.40, 1.47.
Where: `plan-review-design.md:137`, `:397`, `:400-405`; `spec-review-design.md:113-115`, `:124`, `:341`, `:448`, `:470`.
Statement: plan review's `close` returns `{ plan, summary }` for the latest round with a summary; the shared core returns `{ outcome, file, summary }` for the latest ruling whose decision ends the case, a ruling the loop never writes when the owner's approval ends it, and plan review's `handoff` is not changed to read it.
Options: (a) plan review keeps its own `close` (`plan-review-design.md:137`) and the core gives the spec review its own; (b) the core's `close` (`spec-review-design.md:115`) with the final ruling written before the loop ends and plan review's `enter` and `handoff` amended to read `$close.output.file`.
Route: load-bearing, D-25 in CONTEXT.md.
Ruling: (b) the shared core's `close`; the ending ruling is written before the loop ends; plan review's `enter` and `handoff` read `$close.output.file`. [route: load-bearing, D-25, reviewed; by main session (3.2)]
Amended at decision review (narrows the ruling): only `enter` reads `$close.output.file`. `handoff` builds the approved path as spec review's `handoff.ts` does.

**G-23** Where a phase block gets its slug (rows H36, H26).
Members: 1.35, 1.42.
Where: `plan-review-design.md:250-252`, `:259`, `:266`, `:287`, `:294`, `:314`, `:321`, `:345`, `:363`, `:379`, `:393`; `spec-review-design.md:285`, `:293`, `:351`, `:378`, `:390`, `:397`, `:476`.
Statement: every ledger node and the `screen` and `cite` bindings take `<slug>`, but the block's only input is the task path and no node outputs the slug.
Options: (a) the first node prints the slug from `INPUTS_TASK` (as `spec-review-design.md:285` does for `handoff`) and later nodes bind `$<node>.output.slug`; (b) the block takes `slug` as a second input from `intake` (H3 adds it to the hand-off).
Route: load-bearing, D-26 in CONTEXT.md.
Ruling: (a) the block's first node prints the slug from `INPUTS_TASK`; later nodes bind `$<node>.output.slug`. [route: load-bearing, D-26, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling): `.shared/rounds.py` derives the slug from `INPUTS_TASK` itself, and `state` prints the round file paths. `cite` and `screen` bind `$filing.output.file` and `$ready.output.file`. No slug output or slug binding exists.

**G-24** What a sworn-in reviewer reads (rows R2, R4).
Members: 1.36.
Where: `plan-review-design.md:178`, `:179`, `:189`; `spec-review-design.md:263`.
Statement: the arbiter reads the latest block and review unless the latest verdict is LEADING or SCREENED; plan review's swear-in reads no earlier plan, so a forked slot never read the plan an earlier review demanded clarification of.
Options: (a) plan review as written (`plan-review-design.md:178-179`); (b) plan review reads the latest plan on the arbiter's rule (`spec-review-design.md:263`).
Route: ask-user seam.
Ruling: (b) plan review's sworn-in reviewer reads the latest plan on the arbiter's rule. [route: ask-user seam; by main session (3.2)]

**G-25** A rerun on a slug whose plan or spec is already approved (rows P1, P2).
Members: 1.29, 1.44.
Where: `plan-review-design.md:150-151`, `:397-398`, `:409`; `spec-review-design.md:59`, `:215`, `:449`; `gauntlet-intake-design.md:159`.
Statement: the ledger has no branch for an existing `approved/<slug>.txt`; a full new hearing runs and `enter`'s `cp -n` then exits non-zero.
Options: (a) as written, the run fails at `enter` after the hearing; (b) the ledger returns a case "already approved" and the block hands off the existing file; (c) `open` fails at once, naming the file, before any agent runs.
Route: load-bearing, D-27 in CONTEXT.md.
Ruling: (b) the ledger returns "already approved" and the block hands off the existing approved file with no hearing. [route: load-bearing, D-27, reviewed; by main session (3.2)]
Amended at decision review (adds to the ruling): an approval records the hash of the task file it was approved against. The ledger reuses an approval only while that hash matches. When `fail` writes a DEFECTIVE record, it moves the slug's approved plan and spec aside, so a rerun re-hears them.

**G-26** The `until_bash` form of the hearing loops (row A15).
Members: 1.38, 1.39.
Where: `spec-review-design.md:338`, `:434`; `plan-review-design.md:281`; `loop-nodes.md:667-670`, `:695-697`.
Statement: `until_bash` reads a wait its own `when:` can skip, and double-quotes a substituted reference that Archon already single-quotes.
Options: (a) as written (the loop fails on an ordinary round and never ends on approval); (b) assign the reference to a shell variable, test it with `[ -n ... ]` guards, and make `bench` unconditional or read it through `$LOOP_PREV` (the forms `loop-nodes.md:667-697` give).
Route: load-bearing, D-28 in CONTEXT.md.
Ruling: (b) the `until_bash` forms `loop-nodes.md:667-697` give: reference assigned unquoted, guarded, never reading a wait its own `when:` can skip. [route: load-bearing, D-28, reviewed; by main session (3.2)]
Amended at decision review (adds to the ruling):
- `bench` stays conditional. `record` writes the owner's answer from `$LOOP_PREV.bench` in the next iteration, and the ledger's `state` returns `owed: ended` once the latest ruling ends the case.
- Every agent node is already gated on `owed`, so the extra iteration runs script nodes only.
- `until_bash` tests `$filing.output.owed` (`filing` always runs), assigned unquoted per `loop-nodes.md:667-670`.

**G-27** The report prompt's verdict value (internal to spec-review-design.md).
Members: 1.46.
Where: `spec-review-design.md:161-162`, `:251`, `:423`.
Statement: the `report` node passes `$case.output.case` ("review" or "invalid") where the reporter role takes READY or INVALID.
Options: (a) pass the verdict from `$ready.output` instead; (b) the role names "review" and "invalid".
Route: ask-user seam.
Ruling: (a) `report` passes READY or INVALID. [route: ask-user seam; by main session (3.2)]

**G-28** The branch the cut hands off (rows H16, H17, H18).
Members: 1.48.
Where: `worktree-cut-design.md:117`, `:168-169`, `:194`, `:195`; `gauntlet-design.md:82`, `:155`.
Statement: `cut` takes `branch` from `pin`'s predicted name while the tree run reads the real one from git, and nothing compares them.
Options: (a) `cut` takes `branch` from `$tree.output` and `pin`'s name becomes a check; (b) keep `pin`'s name and add a node failing when the two differ.
Route: load-bearing, D-29 in CONTEXT.md.
Ruling: (a) `cut` takes `branch` from `$tree.output`; pin's predicted name is checked against it. [route: load-bearing, D-29, reviewed; by main session (3.2)]
Amended at decision review (adds to the ruling): `gauntlet-tree` takes pin's `branch` as an input. Its first node compares it with `git branch --show-current` and fails the run, naming both, before copy-in. `cut` reads `branch` from `$tree.output`.

**G-29** What node `baseline` writes (rows H20, P8, P4).
Members: 1.49, 1.52.
Where: `worktree-cut-design.md:159-161`, `:200`; `writing-design.md:14`, `:30`, `:145`, `:502`, `:526`; `landing-design.md:16`, `:40`, `:64`; `gauntlet-design.md:156`, `:163`, `:194`, `:222`.
Statement: the full-suite file `gauntlet/baseline/<slug>.txt` is written by a run of up to 15 minutes that nothing reads, and the Homes row forbids the brief file `<slug>.brief.txt` that the same node writes and every red check reads.
Options: (a) drop the full baseline file and its pass-through fields, `baseline` writes the brief file only and the Homes row names it; (b) keep both and give the full file a reader; (c) keep both and add the brief file to the Homes row.
Route: load-bearing, D-30 in CONTEXT.md.
Ruling: (a) the full baseline file and its pass-through fields are dropped; `baseline` writes the brief file only and the Homes row names it. [route: load-bearing, D-30, reviewed, no objection; by main session (3.2)]

**G-30** The node `timeout` from the repository's env (row A27).
Members: 1.50.
Where: `worktree-cut-design.md:158`; `writing-design.md:399`; `landing-design.md:61`, `:79`, `:146`; `workflow-language.md:93`.
Statement: the designs write a node timeout as `GAUNTLET_TEST_TIMEOUT` plus 60 s, but a node `timeout` is a literal in milliseconds.
Options: (a) a literal 960000 (kills a repository that raises `GAUNTLET_TEST_TIMEOUT`); (b) no node `timeout`, the inner `timeout -k` bounds the process.
Route: load-bearing, D-31 in CONTEXT.md.
Ruling: (b) no node `timeout` on test nodes; the inner `timeout -k` bounds the process. [route: load-bearing, D-31, reviewed; by main session (3.2)]
Amended at decision review (adds to the ruling): the run-start guard (D-32) refuses a `GAUNTLET_TEST_TIMEOUT` that is not a positive integer. The node `timeout` stays omitted.

**G-31** A repository with no test command (rows P11, H20).
Members: 1.51, 1.63.
Where: `worktree-cut-design.md:159-160`; `writing-design.md:107`, `:502`, `:512`; `landing-design.md:62`.
Statement: the cut and the writing baseline accept a blank command and write "no test command"; `stage.py` and the mend refuse it, after the earlier phases have been paid for.
Options: (a) a blank command is refused: `writing-design.md:107` ("every mode exits 1 naming it"), `:512`, `landing-design.md:62`; (b) a blank command is accepted and recorded: `worktree-cut-design.md:159-160` (the one line "no test command"), `writing-design.md:502`. Under (a) the refusal stands where the first paid phase begins; the designs name no node for it.
Route: load-bearing, D-32 in CONTEXT.md.
Ruling: (a) a blank test command is refused, checked by the guard at run start before any paid phase. [route: load-bearing, D-32, reviewed; by main session (3.2)]
Amended at decision review (adds to the ruling): `gauntlet-run`'s own guard, never the shared working-folder check, refuses a run when:
- either variable is blank;
- `GAUNTLET_TEST_TIMEOUT` is set but is not a positive integer;
- or `.archon/config.yaml` has uncommitted changes.

**G-32** `uncommitted` reaches no reader (rows H16, H17).
Members: 1.53.
Where: `worktree-cut-design.md:9`, `:23`, `:69`; `gauntlet-design.md:31`, `:80-88`.
Statement: the cut lists the checkout's changed tracked paths and hands them on, but no node or owner gate reads them, and untracked files are not listed.
Options: (a) as written; (b) `cut` fails or asks the owner when `uncommitted` is non-empty; (c) drop `uncommitted` and the sentence at `:9`.
Route: load-bearing, D-33 in CONTEXT.md.
Ruling: (b) the cut asks the owner when the checkout has uncommitted or untracked changes. [route: load-bearing, D-33, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling):
- The run-start `guard` prints `dirty`: the tracked paths that `git status --porcelain` reports changed, plus untracked paths that are not ignored, with `gauntlet/` excluded.
- When `dirty` is non-empty, an `ask` after `guard` names the paths and says they will not reach the tree. Its options are `go on` and `leave`.
- `pin` and `cut` drop `uncommitted`. `worktree-cut-design.md:23` is reworded to point at the guard's ask.

**G-33** The tree node's `checkout` input has no source (rows H9, H16).
Members: 1.54.
Where: `worktree-cut-design.md:66-69`, `:105`, `:111`, `:153`; `gauntlet-design.md:156`, `:169`.
Statement: `with: { checkout: <the checkout's absolute root> }` binds a value no node prints.
Options: (a) `pin` prints the checkout root; (b) a bash node before `tree` prints it.
Route: load-bearing, D-34 in CONTEXT.md.
Ruling: (a) `pin` prints the checkout root. [route: load-bearing, D-34, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling):
- Drop the tree's `checkout` input.
- `copy-in` (`worktree-cut-design.md:153`) and `paths` (`gauntlet-design.md:156`) take the checkout root as `$INPUTS.task` with its trailing `/gauntlet/tasks/$INPUTS.slug.md` removed.
- `pin`'s `output_format` stays as it is.

**G-34** `copy-in` skips a missing input silently (row H7; internal to worktree-cut-design.md).
Members: 1.55.
Where: `worktree-cut-design.md:48`, `:152-153`, `:168-170`.
Statement: a plan or spec named by the input but absent from the checkout is skipped, and `handoff` prints a tree path for it.
Options: (a) as written; (b) `copy-in` fails naming the missing file when the input is non-empty.
Route: ask-user seam.
Ruling: (b) `copy-in` fails naming a missing input. [route: ask-user seam; by main session (3.2)]

**G-35** Removing the tree (rows H37, H23).
Members: 1.56.
Where: `worktree-cut-design.md:197`; `landing-design.md:263-265`; `gauntlet-design.md:343`, `:354`.
Statement: the cut design forbids any write in the tree by a `gauntlet-run` node; landing's `remove` node, a `gauntlet-run` block, removes the tree.
Options: (a) the Homes row `worktree-cut-design.md:197` names `remove` as the exception; (b) the narrower rule `gauntlet-design.md:343` ("a rebase, test run or commit in the tree") replaces it.
Route: ask-user seam.
Ruling: (b) the narrower rule of `gauntlet-design.md:343` replaces `worktree-cut-design.md:197`. [route: ask-user seam; by main session (3.2)]

**G-36** The juror case triggers of `state` (row S5).
Members: 1.58, 1.61.
Where: `writing-design.md:126-130`, `:127`, `:150-155`, `:164`.
Statement: older contests, red runs and seal exits keep matching after a ruling, and every owner reply to `stalled` or `cap` opens a juror case with no "carry on" verdict.
Options: (a) as written; (b) each trigger is bounded by "newer than the latest verdict" and a `stalled` or `cap` reply is a ruling that opens no case; (c) the juror gets a `CONTINUE` verdict.
Route: ask-user seam.
Ruling: (b) each juror trigger is bounded by "newer than the latest verdict"; a `stalled` or `cap` reply opens no juror case. [route: ask-user seam; by main session (3.2)]

**G-37** Coverage of the approved spec and plan across cuts (internal to writing-design.md).
Members: 1.59.
Where: `writing-design.md:28`, `:130`, `:138`, `:175-176`.
Statement: a later cut covers only what its cause affects, so unrun waves of the cut it replaces are dropped and no check finds an untested spec.
Options: (a) as written; (b) `state` carries the unrun waves of the replaced cut into the next, or a coverage check on spec ids precedes `seal`.
Route: ask-user seam.
Ruling: (b) `state` carries the replaced cut's unrun waves into the next cut. [route: ask-user seam; by main session (3.2)]

**G-38** `max_iterations: 200` against moves (internal to writing-design.md; rows S5, S7).
Members: 1.62.
Where: `writing-design.md:29`, `:330`; `loop-nodes.md:203-205`.
Statement: the loop bound counts iterations while the `cap` that keeps it from failing counts moves, and revise and review iterations write no move.
Options: (a) as written; (b) `cap` counts iterations (`$LOOP_PREV` count) so the ask fires before 200.
Route: ask-user seam.
Ruling: (b) `cap` counts loop iterations, so the ask fires before 200. [route: ask-user seam; by main session (3.2)]

**G-39** `docket` returns `ask` together with `end` (row H28).
Members: 1.64.
Where: `writing-design.md:148-152`, `:331`, `:479`.
Statement: the owner is asked about a stall or cap of a run that has already ended.
Options: (a) as written; (b) `ask` is false when `end` is non-empty.
Route: ask-user seam.
Ruling: (b) `ask` is false when `end` is set. [route: ask-user seam; by main session (3.2)]

**G-40** The test writer's fence omits `docs/testing.md` (rows F8, P12).
Members: 1.65.
Where: `writing-design.md:256`, `:272`, `:309`; `spec-review-design.md:274`.
Statement: the test writer is told to follow the repository's testing policy and its fence cannot read it.
Options: (a) add `docs/testing.md` to `FENCE_READ` of `test-writer.mcp.json`; (b) the role no longer names the policy.
Route: load-bearing, D-35 in CONTEXT.md.
Ruling: (a) `docs/testing.md` added to the test writer's `FENCE_READ`. [route: load-bearing, D-35, reviewed; by main session (3.2)]
Amended at decision review (adds to the ruling): ruling (a), and the test-writer role names `docs/testing.md` alone, as the rest of the pack does.

**G-41** The coder's check tool returns tracebacks (rows F9, P14).
Members: 1.66.
Where: `writing-design.md:13`, `:18`, `:187`, `:295`, `:529`.
Statement: `fence/checks.py` returns the last 200 lines, tracebacks included, which show the test source the coder is meant not to see.
Options: (a) as written; (b) a coder-facing mode of the check tool that returns names and messages only.
Route: load-bearing, D-36 in CONTEXT.md.
Ruling: (b) a coder-facing mode of the check tool returns test names and messages only. [route: load-bearing, D-36, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling):
- The coder's and `mend-code`'s fence-checks run the brief command, with no change to `checks.py`.
- The `commit` tool returns git's exit and the names of failing hooks, never the hooks' output.

**G-42** `record` passes no `move` (internal to writing-design.md; row S5).
Members: 1.67.
Where: `writing-design.md:154-155`, `:337`.
Statement: `record` writes `<slug>.ruling.<move>.txt` for `stalled` and `cap` with no `move` input.
Options: (a) add `move: $state.output.move` to the `with:`; (b) `record` derives the move from the files.
Route: ask-user seam.
Ruling: (a) `record` passes `move: $state.output.move`. [route: ask-user seam; by main session (3.2)]

**G-43** The reviser's `Answers:` path (row R12; internal to writing-design.md).
Members: 1.68.
Where: `writing-design.md:117`, `:197-199`, `:428`.
Statement: `state` gives the reviser no answers path.
Options: (a) `state` prints `cause` for `revise` as well; (b) the reviser derives it from the folder.
Route: ask-user seam.
Ruling: (a) `state` prints `cause` for `revise` too. [route: ask-user seam; by main session (3.2)]

**G-44** Landing's resume re-tests nothing after the first pass (rows H22, H17).
Members: 1.69.
Where: `landing-design.md:30`, `:47`, `:55`, `:195`, `:205`, `:368`; `workflow-language.md:83`, `:324-332`.
Statement: after the first pass has rebased the branch, `moved` is false on resume, `test-tree`, `red`, `confirm` and `repair` are skipped, and the gate shows a false "not rerun".
Options: (a) `moved` is computed against the recorded tree base, not the checkout's head; (b) a resume always reruns `test-tree` on the rebased tip.
Route: ask-user seam.
Ruling: (b) a resume always reruns `test-tree` on the rebased tip. [route: ask-user seam; by main session (3.2)]

**G-45** Landing's decision for the owner (D-10; rows H22, H23).
Members: `landing-design.md:388` (open decision 1, no finding id).
Where: `landing-design.md:388`.
Statement: the checkout moves after the mend rebased the branch and before the merge, so the branch no longer fast-forwards.
Options: (a) landing stops at `onto` or `merge`, keeps the tree, branch and any land answer, and `archon workflow resume <run id>` lands once the checkout is back at an ancestor of the branch; cost: the owner moves the new checkout commits aside by hand and no test reruns on them; (b) landing hands off `left` with the tree kept and the owner lands by hand; cost: the run ends with no Gauntlet landing, and the record copy and tree removal fall to the owner. Option (a) depends on the ruling of G-44.
Route: ask-user seam.
Ruling: new option (c): when the checkout has moved past the branch's base, landing rebases the branch onto the checkout's new head, reruns the tests (and the repair when red) and then lands. [route: ask-user seam; by owner]
Mechanism (owner, at the plan-3 Task 2 structural checkpoint, choice 1 of 3): when `land` finds the checkout moved, it starts a second tree run that runs block `mend` only (rebase, tests, repair) on the existing tree, then asks the land-or-leave gate again; the check repeats if the checkout moves again.
Amended by the owner after the executor checkpoint of 2026-11-05 (replaces the repeat; an unbounded repeat needs a `workflow:` node in a `loop_group` body, rejected at load: `workflow-language.md:2543-2544`): landing re-mends at most 2 times, each round an `include`d block under its own id that checks the checkout, re-mends on a move (a second tree run running block `mend` only) and asks the land-or-leave gate again; a third move stops the run, naming the move. [by owner]
Applied: `landing-design.md` (Why, `land/land.yaml`, `land/scripts/pin.py`, `gauntlet-remend/gauntlet-remend.yaml`, Homes, Order, Decisions for the owner), `gauntlet-design.md` (phases 6 and 7, node `land` as `land`, `land-2`, `land-3`, Homes), `worktree-cut-design.md` (`.shared/pin.py`, Homes), `contracts.md` (H16, H23, H31, H37, H39, H40, P18, S14-S16, A29), `REQUIREMENTS.md` LAND-01.

**G-46** `pose` ends the repair without checking the commit (row H34).
Members: 1.70.
Where: `landing-design.md:55`, `:143-147`, `:172`, `:326-327`.
Statement: a `commit-failed` mend leaves edits uncommitted, `recheck` is not red, and the repair ends "done" on a dirty tree.
Options: (a) as written; (b) `pose` ends "done" only when the mender's outcome is `committed`, and the UNSOUND list names an uncommitted mend.
Route: ask-user seam.
Ruling: (b) `pose` ends "done" only on a `committed` mend; the UNSOUND list names an uncommitted mend. [route: ask-user seam; by main session (3.2)]
Amended by the D-37 decision review: `pose` also ends "done" when a `retry` rerun is not red and no mend is uncommitted (see G-50).

**G-47** `retest` overwrites `test-tree`'s run file (row P9).
Members: 1.71.
Where: `landing-design.md:30`, `:63`, `:116`, `:147`.
Statement: with the tip unchanged `retest` writes to the file `test-tree` wrote.
Options: (a) as written; (b) `retest` runs only when a mend committed, so the key differs by construction.
Route: ask-user seam.
Ruling: (b) `retest` runs only after a committed mend. [route: ask-user seam; by main session (3.2)]
Amended by the D-37 decision review: G-47 gains "or the latest decision was `retry`" (see G-50).

**G-48** `retest` and `review` run when nothing was mended (internal to landing-design.md; CLAUDE.md 1.3).
Members: 1.72.
Where: `landing-design.md:143`, `:157`, `:327`.
Statement: after a `contest`, or with `recheck` red, a full test run and an agent session are spent on a verdict fixed in advance.
Options: (a) as written; (b) `retest` and `recheck` gated on `outcome == committed` and `review` gated on `recheck` not red.
Route: ask-user seam.
Ruling: (b) `retest`/`recheck` gated on a committed mend; `review` gated on recheck not red. [route: ask-user seam; by main session (3.2)]
Amended by the D-37 decision review: G-48 gains "or the latest decision was `retry`" (see G-50).

**G-49** The case `pose` hands the next juror (internal to landing-design.md).
Members: 1.73.
Where: `landing-design.md:116`, `:129`, `:172-174`.
Statement: after a DEFECTIVE ruling or a resume the case is empty or falls back to the pre-mend run file.
Options: (a) as written; (b) `pose` always prints the latest run file and review file it holds.
Route: ask-user seam.
Ruling: (b) `pose` always prints the latest run file and review file. [route: ask-user seam; by main session (3.2)]

**G-50** What `repair`'s `ask` offers and when it fires (row H31).
Members: 1.74, 1.75.
Where: `landing-design.md:98`, `:175-176`, `:178`, `:373`.
Statement: the options are reply or leave only, so a flaky red cannot be accepted or rerun, and the Homes row omits the third ask condition (`hear.n >= 200`).
Options: (a) as written; (b) add `retry` and `accept` options and list all three ask conditions in the Homes row `landing-design.md:373`.
Route: load-bearing, D-37 in CONTEXT.md.
Ruling: (b) `repair`'s ask adds `retry` and `accept`; the Homes row `landing-design.md:373` lists all three ask conditions. [route: load-bearing, D-37, reviewed; by main session (3.2)]
Amended at decision review (replaces the ruling; `accept` is dropped):
- `repair`'s `ask` offers `reply`, `retry` and `leave`.
- On `retry`, `hear` writes `gauntlet/mend/<slug>.reply.<n>.txt` holding `retry`, which resets the stall count. The next iteration then runs `retest` with no mender. G-47 and G-48 gain "or the latest decision was `retry`".
- `pose` also ends "done" when a `retry` rerun is not red and no mend is uncommitted, which amends G-46.
- In `handoff`, a repair with no committed mend prints "Rerun on $onto.output.head after retry: no new failure."
- Homes row `landing-design.md:373` lists all three ask conditions and the three options.
- `gauntlet-design.md:16` and `landing-design.md:9` read "with guidance, a rerun or leave".
