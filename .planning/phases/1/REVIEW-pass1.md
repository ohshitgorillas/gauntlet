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

(Plan 2 Task 4.)

## 4. gauntlet-intake-design.md

(Plan 2 Task 4.)

Seeded by Task 2 from the probe record, to be kept when the reviewer returns:

**1.04** `gauntlet-intake-design.md:117`, row A5.
Text: "Claude Code sets the server's `CLAUDE_PROJECT_DIR` to its own working directory, the run's checkout, and overrides any value the config gives, so the config sets none."
Finding: false as written. PROBES.md section P2: Claude Code sets `CLAUDE_PROJECT_DIR` to the cwd only when the MCP config gives no value; a config `env` value wins (`/bogus` stayed `/bogus`). The pack still works because every config sets none, but the stated reason does not hold: nothing in Claude Code stops a config from relocating the fence root of F1-F11, so "the config sets none" is a rule the pack must keep and test, not a guarantee. Same claim stands behind `plan-review-design.md:226`, `spec-review-design.md:269`, `writing-design.md:268` ("sets no `CLAUDE_PROJECT_DIR`").

## 5. plan-review-design.md

(Plan 2 Task 4.)

Seeded by Task 2, to be kept or dropped when the reviewer returns:

**1.06** `plan-review-design.md:264`, row A19 (the `allowed_tools` row naming this line; the `Bash(<pattern>)` form itself has no row of its own).
Text: `allowed_tools: [Task, "Bash(uv run --script *cite.py *)"]` (also `:301`, and `:170` "Bash for exactly the cite.py command above and no other command").
Finding: no doc under `docs/reference/archon/` shows a `Bash(<pattern>)` specifier in `allowed_tools` (`workflow-language.md:621-643` lists plain tool names). PROBES.md section P3: `archon validate` accepts the specifier, but at runtime Bash is removed entirely ("No such tool available: Bash"), not limited to matching commands. The defense can run no command, `cite.py` included, so the cite check cannot run and the confinement the design builds on it does not exist. A `Bash(...)` rule set through `settings`/permissions was not tested.

## 6. spec-review-design.md

(Plan 2 Task 4.)

Seeded by Task 2 from the probe record, to be kept when the reviewer returns:

**1.03** `spec-review-design.md:361`, row A10.
Text: "sandbox: <enabled; filesystem writes allowed only under gauntlet/scratch/ of the checkout>". Also `:482`, `:499`.
Finding: PROBES.md section P1: there is no pure write allow-list. `filesystem.allowWrite` is accepted but only adds writable paths; the checkout stays writable (a direct and a sub-agent `echo > outside.txt` both succeeded). Confinement holds only with `denyWrite` listing every other path (deny beats allow), and it does reach the Bash of a sub-agent spawned from the node. The design's form cannot confine the spiker to `gauntlet/scratch/` as written, and a new top-level file not on a `denyWrite` list stays writable. Globs in `denyWrite` were not tested. The documented keys are `workflow-language.md:250-261`. `:499` already tells the builder to stop and report if the sandbox cannot limit the writes.

## 7. worktree-cut-design.md

(Plan 2 Task 4.)

## 8. writing-design.md

(Plan 2 Task 4.)

## 9. landing-design.md

(Plan 2 Task 4.)

Withdrawn by Task 2:

**1.05** `landing-design.md:11`, row A5. Dropped: the quoted text "`fence/files.py` and `fence/checks.py` root at `CLAUDE_PROJECT_DIR`, the agent's folder" states only the part PROBES.md section P2 confirms (the variable is the cwd when the config gives none). The false clause is in `gauntlet-intake-design.md:117` (finding 1.04).

## 10. Groups

(Plan 2 Task 5.)
