---
phase: 1
plan: 4
requirements:
  - REV-02
files:
  - docs/superpowers/specs/contracts.md
  - docs/superpowers/specs/gauntlet-design.md
  - docs/superpowers/specs/gauntlet-intake-design.md
  - docs/superpowers/specs/plan-review-design.md
  - docs/superpowers/specs/spec-review-design.md
  - docs/superpowers/specs/worktree-cut-design.md
  - docs/superpowers/specs/writing-design.md
  - docs/superpowers/specs/landing-design.md
  - .planning/phases/1/PROBES.md
---

# Phase 1: Design review - Plan 4: Draft the owner-control ruling into the seven designs

## Goal

The seven designs under `docs/superpowers/specs/` are made consistent with each other in one converging pass, not finding by finding. This plan drafts the owner-control ruling (D-80, D-81) into every design it names, so that Plan 5 can review the whole draft and land it as one commit.

## Must be true when done

- Each of the seven designs, read in the working tree, describes the owner-control behaviour that falls in its scope: the item file in intake, item ids, stages and escalation rules in the two review phases, the amicus and the direction file in writing and the mend, the review before landing in the tree run, and the back-to-planning exit in the run's head.
- `grep -niE 'juror|DEFECTIVE|gauntlet/failed|task-format' docs/superpowers/specs/*-design.md`, with the owner-control design excluded, prints no line.
- Each item that owner-control leaves to the builder and that is a cross-design contract (D-83) is settled in exactly one home design, and every other design names that home rather than restating the fact (D-61).
- `contracts.md` section A holds a closed verdict for each of the three owner-control Archon behaviours: the amicus wait, verbatim goal capture and the back-to-planning exit.
- `git log -1 --format=%H` prints the hash it printed before this plan began. Every edit sits uncommitted in the working tree for Plan 5.

## Context

- Sources of the ruling: `docs/superpowers/specs/2026-11-07-owner-control-design.md`, which is approved and is not edited (D-80), and CONTEXT.md D-80 to D-96. Apply each decision exactly as ruled. Do no tidying and add no second fix beside it: an edit beyond the ruling puts unreviewed text in front of the convergence pass (PLAN-3 Context).
- D-61 holds for every edit. A cross-design citation is a node id or a heading, never a line number. A fact restated in several designs is cut down to one home, and the other designs name that home.
- D-85 says which old rulings are void and which are carried. Remove the text of a void ruling where the juror or `gauntlet/failed/` was its premise. Re-anchor a carried ruling on the amicus case and the direction file. RULINGS.md, CONTEXT.md and the D-NN lines hold each ruling's text.
- No task commits. D-81 requires one commit for the whole ruling, together with `contracts.md` and the planning lines. Plan 5 adds those, reviews the draft under D-79 and makes that commit. Leave every edit uncommitted and stage nothing.
- Standing check for every task (CLAUDE.md 1.8): run from the pack root. `archon workflow list --json` shows `"errors": []`. `archon validate workflows` reports no error under the pack root beyond the 23 non-pack `No default provider` baseline errors. Testing scope for every task: the changes are documentation only, so no test applies (PLAN-2 Notes deviation). The greps in each Verify are the evidence, and testing stops there.

## Tasks

### Task 1: Close the Archon verdicts for the three owner-control behaviours

- **Files:** docs/superpowers/specs/contracts.md (section "A. Assumed Archon features"), .planning/phases/1/PROBES.md
- **Action:** Add one section A row, at the next free A id (ids are never reused), for each of the three behaviours that CONTEXT's Flagged assumptions and AC4 name:
  - A multi-turn amicus discussion run as a wait inside writing's `work` body and the mend's `repair` body. Each body already ends in a sole terminal wait (`bench`, `ask`). Read `docs/reference/archon/loop-nodes.md` around :682 first.
  - Verbatim goal capture through `$LOOP_PREV.<wait-id>.output.text` (`loop-nodes.md:122`).
  - A back-to-planning exit that ends the run cleanly and prints the next plan-review command, set against `cancel:`, which ends a run cancelled (`workflow-language.md:773`, `:2341`).

  Each row states the form the designs will assume and the verdict, using the section preamble's vocabulary (D-03):
  - `documented`, citing the `docs/reference/archon/` path:line that confirms the form.
  - `unsupported`, citing the line that refuses the form and naming the documented form that Tasks 2 to 8 write in its place. The commit hash is added in Plan 6.

  Fill the Named-by cells in Task 8's sweep, once the designs carry the forms.

  Where no file under `docs/reference/archon/` settles a behaviour, write the verdict `pending probe`. Then return a `decision` checkpoint whose Need asks the main session for the owner's explicit approval of one spiker probe per open row (CLAUDE.md 1.9, D-03). The Need states the question each probe answers and its footprint. The brief carries rule 1.9. On continuation, record each approved probe's result in PROBES.md at the next free P id, set the row to `probed` citing that id, and close it. A probe the owner refuses leaves the row `unsupported`, with the documented form that replaces the behaviour.
- **Verify:** Section A holds three new rows, one per behaviour. Each verdict cell starts with `documented`, `probed` or `unsupported`, and `grep -c 'pending probe' docs/superpowers/specs/contracts.md` counts no row added by this task. Run `sed -n '<line>p'` on each cited `docs/reference/archon/` path:line: it shows the form the row names. For a `probed` row, PROBES.md holds the cited P id. `git log -1 --format=%H` is unchanged. Plus the standing check.

### Task 2: Re-key the run's head on owner control

- **Files:** docs/superpowers/specs/gauntlet-design.md
- **Action:**
  - Start reading at these headings: Modules `gauntlet-run/gauntlet-run.yaml` (the run's head); `gauntlet-tree/gauntlet-tree.yaml` (writing's host); `land/land.yaml` (landing's signature); `intake/scripts/ground.ts` and `intake/commands/clerk.md` (failed slugs); `fence/files.py` (hidden paths); Checkout fences outside intake; Homes; Order; and the copy list "The phase designs contain these copies:".
  - Apply D-89. Remove the `gauntlet/failed/` machinery: nodes `fail` and `kill`, the failed-record Homes row, the failed-slug parts of `ground.ts` and `clerk.md`, and every `FENCE_HIDE=gauntlet/failed`. Keep `FENCE_HIDE` itself wherever another hidden path still needs it.
  - Make this design the home of the back-to-planning exit. It states the exact command the run prints for the next plan review (D-83). The exit takes the form Task 1's verdict allows. Back to planning sets aside the slug's approved plan and specs, so that D-27's `owed: approved` does not hand the rejected plan back. It hands plan review the amicus record and the owner's direction.
  - Apply D-93 to the head. A staged plan's stage sequence takes an unrolled, bounded form, as `land` to `land-4` already does, and each stage carries its own ids. State the bound once here, and state what the run does with a plan whose stages exceed it.
  - Apply D-92. The review before landing and its amicus run in the tree run and the re-mend run, never in block `land`, which holds no agent. Fix the tree's `handoff` fields, the land gate's role and "Where the owner answers" to match. Name the landing design as the home of the review.
  - Apply D-90's share here: node `paths` takes the checkout root from the item file in place of the task path, and every other task-path derivation here (the tree's `task` input and its description, the intake overview line) moves to the item file. Name the intake design as the item file's home.
  - Remove every juror, `DEFECTIVE` and `task-format` mention.
  - Mark each copy-list bullet that this ruling changes as resolved, citing D-81 (D-06).
- **Verify:** `grep -nE 'id: (fail|kill)$|gauntlet/failed|juror|DEFECTIVE|task-format' docs/superpowers/specs/gauntlet-design.md` prints nothing. The design names one back-to-planning command, one stage bound and the tree `handoff` field that carries the review's result. Each of these is named once, with no second statement of it in this file. `git diff -U0 -- docs/superpowers/specs/gauntlet-design.md | grep -E '^\+.*(gauntlet|gauntlet-intake|plan-review|spec-review|worktree-cut|writing|landing)-design\.md:[0-9]'` prints nothing. Every copy-list bullet still carries a resolved mark. `git log -1 --format=%H` is unchanged. Plus the standing check.

### Task 3: Move intake to the item file

- **Files:** docs/superpowers/specs/gauntlet-intake-design.md
- **Action:**
  - Start reading at these headings: Modules `.shared/task-format.md`; `intake/commands/clerk.md`; `intake/clerk.mcp.json`; `intake/scripts/`; `intake/intake.yaml`; `intake/fixtures/`; Homes; Order.
  - Apply D-86 and owner-control section 1. Intake ends with the item file in place of the task file. This design is the item file's single home: its name, format, location and its hand-off to plan review (D-83).
  - The item file holds the fields Id, Goal, Current behavior, Desired behavior, Constraints, Out of scope and Notes.
  - A script records a goal the owner types, exactly as typed, through the form Task 1's verdict allows. Clerk cannot write that field.
  - Each item is approved on its own, never in a batch.
  - A script checks a length cap on every field Clerk writes. The cap value stays intake-internal (D-83).
  - The "none" rule applies: an empty field holds the word "none", never an empty string.
  - A script checks that every point of the opening statement is assigned to exactly one item.
  - Intake closes with the question "do everything in this run" or "defer some". Deferred items move to a second item file.
  - Remove `.shared/task-format.md`, Clerk's `{ slug, reply, draft }` output protocol and the handoff `{ task }` field.
  - The file route stays (`--input file=<path>`, node `route`, node `from-file`), and a script checks the owner's file against the item schema.
  - Re-specify the slug and every path derived from the task path on the item file (D-90).
  - D-49 and D-50 fall with this rewrite (D-85).
- **Verify:** `grep -nE 'task-format|reply, draft|draft: \{ type' docs/superpowers/specs/gauntlet-intake-design.md` prints nothing. Each of the seven field names appears in one item-schema statement. The design names the file's name, format, location and hand-off once. It names the script that records the typed goal, the length-cap check, the "none" rule, the point-assignment check, per-item approval and the defer question. Node `from-file` checks against the item schema. The D-61 diff grep from Task 2, run on this file, prints nothing. `git log -1 --format=%H` is unchanged. Plus the standing check.

### Task 4: Bind plan review to the item file, stages and escalation rules

- **Files:** docs/superpowers/specs/plan-review-design.md
- **Action:**
  - Start reading at these headings: Terms; `plan-review/scripts/cite.py`; `plan-review/commands/defense.md`; `plan-review/commands/prosecutor.md`; `plan-review/plan-review.yaml`; Homes; Order.
  - Plan review reads the item file in place of the task file (D-86, D-90).
  - Apply D-91's plan-review share and make this design its home. The defense writes plan steps in a grammar that carries item ids. A script in plan review, `cite.py` or a sibling named here, checks each step. A step that cites no id from the approved item file is marked as added scope. Name the writing design (the divvyer) and the landing design (the review before landing) as the readers of the grammar and the mark; their reads are stated in those designs, not here (D-61).
  - Apply D-90 to every task-path derivation in this design, not only those D-90 names: the slug `cite.py` takes from `INPUTS_TASK`, the block's `task` input and its description, and the script that prints `{ task, plan }`.
  - The plan's stage marker sits in the plan the defense writes, and the prosecutor reviews it with the rest of the plan (D-93).
  - The prosecutor rejects a plan that breaks an item's Constraints or Out-of-scope field to the planner, never to the owner.
  - Apply D-94. Repo-wide escalation rules reach the prosecutor verbatim, together with the item's per-item Notes rules, in standalone and included runs. They arrive through a named node or file, not through `env:`, which reaches bash nodes only. This design is the home of the repo-wide escalation key and of that carrier (D-83). The spec review design names this design.
  - On back to planning, plan review takes the amicus record and the owner's direction as inputs beside the item file. Name the gauntlet design as the home of the exit (D-89).
  - Remove `gauntlet/failed` from every fence.
  - Plan review keeps its analyst and its loops (D-75, owner-control Non-goals).
- **Verify:** `grep -nE 'gauntlet/failed|task-format' docs/superpowers/specs/plan-review-design.md` prints nothing. The design states the step grammar with item ids, the script that checks it and the added-scope mark, the stage marker the prosecutor reviews, and the escalation key with its carrier node or file. Each is stated once. `grep -n 'analyst' docs/superpowers/specs/plan-review-design.md` still finds the analyst. The D-61 diff grep from Task 2, run on this file, prints nothing. `git log -1 --format=%H` is unchanged. Plus the standing check.

### Task 5: Bind spec review to the item file and escalation rules

- **Files:** docs/superpowers/specs/spec-review-design.md
- **Action:**
  - Start reading at these headings: `spec-review/commands/speccer.md`; `spec-review/commands/arbiter.md` (amended); `spec-review/speccer.mcp.json`; `spec-review/spec-review.yaml`; Homes; Order.
  - Spec review reads the item file in place of the task file. The speccer's `FENCE_READ` covers the item file's location in place of `gauntlet/tasks` (D-86, D-90).
  - Apply D-94's spec-review share. The arbiter receives the repo-wide and per-item escalation rules verbatim, through the carrier the plan review design homes, which this design names. The `spec-review/commands/arbiter.md` (amended) section names the change to `arbiter.md` that this ruling makes.
  - Apply D-90 to every task-path derivation in this design, not only the speccer's fence: the slug taken from `INPUTS_TASK`, the `docket-in` task-file sha, the arbiter's `FENCE_READ` of `gauntlet/tasks`, the block's `task` input and its description, and the script that prints `{ task, plan }`.
  - Remove `gauntlet/failed` from every fence.
  - Spec review keeps its analyst and its loops (D-75).
- **Verify:** `grep -nE 'gauntlet/failed|task-format' docs/superpowers/specs/spec-review-design.md` prints nothing. The speccer's fence names the item file's location. The arbiter section states the escalation-rules change and names the plan review design's carrier. The D-61 diff grep from Task 2, run on this file, prints nothing. `git log -1 --format=%H` is unchanged. Plus the standing check.

### Task 6: Put the item file and stages into the worktree cut

- **Files:** docs/superpowers/specs/worktree-cut-design.md
- **Action:**
  - Start reading at these headings: Modules `.shared/pin.py`; `gauntlet-run/scripts/pin.py`; `gauntlet-run/gauntlet-run.yaml`; `gauntlet-tree/gauntlet-tree.yaml`; The repository's `.archon/config.yaml`; Homes; Order.
  - Apply D-90 here. `.shared/pin.py` derives the slug from the item file in place of `INPUTS_TASK`.
  - `copy-in` copies the item file in place of `gauntlet/tasks/<slug>.md`.
  - Every `FENCE_*` value derived from the task path moves to the item file's location.
  - Apply D-93's cut share. Nodes `pin`, `tree` and `cut` take the per-stage, unrolled form that the gauntlet design states, each stage with its own ids. Name the gauntlet design for the bound.
  - Remove every juror, `DEFECTIVE` and `gauntlet/failed` mention.
  - Touch the `.archon/config.yaml` section only where D-94's escalation key needs a pointer to its plan-review home.
- **Verify:** `grep -nE 'INPUTS_TASK|gauntlet/tasks/<slug>\.md|juror|DEFECTIVE|gauntlet/failed' docs/superpowers/specs/worktree-cut-design.md` prints nothing. Nodes `pin`, `tree` and `cut` read per stage and name the gauntlet design for the bound. The D-61 diff grep from Task 2, run on this file, prints nothing. `git log -1 --format=%H` is unchanged. Plus the standing check.

### Task 7: Replace writing's juror with the amicus

- **Files:** docs/superpowers/specs/writing-design.md
- **Action:**
  - Start reading at these headings: Terms; `write/scripts/stage.py`; Roles: `write/commands/divvyer.md`, `juror.md`, `reviser.md`, `reviewer.md`, `reporter.md`, `analyst.md`; `write-code/write-code.yaml`; Writing's fences; `write/write.yaml` (the block's nodes); Homes; Order.
  - Apply D-87. The juror goes: `write/commands/juror.md`, `write/juror.mcp.json`, `<slug>.verdict.N.txt`, the verdict table, `next: juror`, `end: defective`, the handoff `verdict` and node `juror`.
  - Every juror case goes to the amicus: a red, a writer's contest, a blocked block, a failed commit and the idle case. Writing's analyst, node `why` where it serves the analyst, and `stalled` also go.
  - `stage.py`'s verdict-keyed rules are re-keyed on the owner's direction file.
  - The revision hearing stays, and runs when the owner's direction asks for a plan or spec revision.
  - Make this design the home of the amicus role, its trigger list, its discussion as a wait in `work` (in the form Task 1's verdict allows), and the direction file: its form and how the next pass reads it (D-83).
  - Apply D-95. Pick either `write/commands/amicus.md` with `mend/commands/amicus.md`, or one shared included block as `screen` is. State the pick and its reason once.
  - Apply D-91's writing share. Writing's blocks record yields a mark when a block's diff falls outside the block's `paths`. The divvyer cuts blocks and waves within a stage, never across one (D-93). State whether each stage seals with its own subject (CONTEXT Flagged assumptions, left to this apply under D-83).
  - Apply D-91's divvyer read: `write/commands/divvyer.md` takes the plan steps' item ids and the added-scope mark, naming the plan review design as the grammar's home.
  - Apply D-90's writing share to every task-path derivation in this design: the coder's `FENCE_HIDE` and `reviewer-spec.mcp.json`'s `FENCE_READ` move from `gauntlet/tasks` to the item file's location, and the hearing's `rounds.py` calls take their slug from the item file in place of `INPUTS_TASK`.
  - Under D-85, remove the void D-76 second half and D-77. Re-anchor D-57, D-58 (`blocked` is an amicus case), D-68 (the leftover patch named in the amicus case's files) and D-78 (the seal subject) on the amicus case and the direction file.
- **Verify:** `grep -niE 'juror|DEFECTIVE|verdict\.N|stalled|write/commands/analyst|write/analyst' docs/superpowers/specs/writing-design.md` prints nothing. The design states the amicus trigger list with all five cases, the wait form, the direction file's form and how it is read, the D-95 pick, the paths mark, the divvyer's read of item ids and the added-scope mark, the within-stage rule and the per-stage seal subject, each once. The D-61 diff grep from Task 2, run on this file, prints nothing. `git log -1 --format=%H` is unchanged. Plus the standing check.

### Task 8: Rebuild the mend's repair and place the review before landing

- **Files:** docs/superpowers/specs/landing-design.md, docs/superpowers/specs/contracts.md
- **Action:**
  - Start reading at these headings: Modules `mend/mend.yaml` (the mend: rebase, verify, repair); `land/land.yaml` (landing in the checkout); `gauntlet-remend/gauntlet-remend.yaml` (the re-mend run); the mend roles heading naming `mend/commands/mend-juror.md`; Homes; Order; Decisions for the owner. In `contracts.md`, only the Named-by cells of Task 1's section A rows.
  - Apply D-88. `mend-juror` goes. Group `repair` is rebuilt around the amicus, under the amicus home Task 7 chose, and the mender is chosen by the owner's direction. Rework nodes `hear`, `changes`, `juror`, `pose`, `ask` and `gate` accordingly.
  - `leave` stays a choice at every owner stop, both in the mend and before landing. `retry` becomes "run again" with an empty direction.
  - Under D-85, remove D-59's juror half. The `mended` file for `mend-review` stays. Re-anchor D-47 and D-48 (four landing rounds) on the amicus case.
  - Apply D-92 and make this design the home of the review before landing (D-83). It runs before every landing, failed or clean. It runs in the tree run and in the re-mend run, never in block `land`. It reads each item against its fields, the plan steps with their item ids, and the two scope-check marks. Its answer reaches the owner through the amicus, with the choices land, run again with direction, back to planning, and leave.
  - Apply D-93's landing share: each stage meets the owner and lands before the next stage starts. Settle the open points CONTEXT's Flagged assumptions leave to this apply: whether each re-mend round meets the owner with a new review, and how landing rounds multiply with stages.
  - Apply D-90 here: the checkout root is derived from the item file in place of the tree run's `task` input with its trailing `/gauntlet/tasks/<slug>.md` removed.
  - Then fill the Named-by cells of Task 1's three section A rows with the designs that now assume each form.
- **Verify:** `grep -niE 'juror|DEFECTIVE|gauntlet/failed' docs/superpowers/specs/landing-design.md` prints nothing. The design states the review's placement in the tree run and the re-mend run, its inputs, its four owner choices, the re-mend review rule and the stage-by-round rule, each once. The D-61 diff grep from Task 2, run on this file, prints nothing. Across the drafted tree, `grep -niE 'juror|DEFECTIVE|gauntlet/failed|task-format' docs/superpowers/specs/{gauntlet,gauntlet-intake,plan-review,spec-review,worktree-cut,writing,landing}-design.md` prints nothing. `grep -nE 'gauntlet/tasks|INPUTS_TASK|task file' docs/superpowers/specs/{gauntlet,gauntlet-intake,plan-review,spec-review,worktree-cut,writing,landing}-design.md`: every line it prints states the item file or the location Task 3 set, never a derivation from the old task path (D-90). Each of Task 1's rows names at least one design, and each named design holds the form. `git log -1 --format=%H` is unchanged. Plus the standing check.

## Notes

- Sequential: Plans 4, 5 and 6 share the designs and `contracts.md`. Plan 5 must start in this plan's working tree, with the drafts in place.
- Deviation from CONTEXT's Plan shape directive: the directive's example gives the owner-control apply one plan. The apply needs 13 single-concern tasks against an 8-task ceiling, and D-81 requires one commit for all of it. This plan therefore drafts the designs, and Plan 5 adds the remaining contract rows, the planning lines and the RULINGS records, runs the D-79 closed review and makes the one commit. This plan lands no commit by design. `execute.md` treats a plan that lands no commits as done, with `risk_check_skipped`.
- D-95 and the homes of the D-83 items are the executor's to pick within the constraints above. Each pick is stated once in its home design. I chose the homes: the item file in intake, the exit in the gauntlet design, the escalation key and the step grammar in plan review, the amicus and the direction file in writing, and the review before landing in landing.
- Recalled memory informs Tasks 3, 7 and 2: D-86 and D-87 (phases/1/CONTEXT.md, phase 1), and D-93 (phases/1/CONTEXT.md, phase 1).
