# Closed review of the pass-4 ruling draft (D-79), G-120 to G-128

Artifact: `git diff HEAD` at `ae19601` (specs under `docs/superpowers/specs/`, `CONTEXT.md` D-99 to D-104, `RULINGS.md`, `reviews/homes-4.md`), against `REVIEW-pass4.md` section 2. Q1: does the edit close the members' scenario. Q2: does it add a high or medium defect. Lows are not reported. No Archon experiment was run; Archon behaviour is cited from `docs/reference/archon/` only.

## G-120 (D-99)

Q1: yes. `runtime-model-design.md:58` puts "`none` when `owed` is `ended`" second, after `vacant` and ahead of every owner case and bound, so the iteration after an ending answer asks nothing; `:77` ends the loop on `owed = ended`.
Q2: no.

## G-121 (D-100)

Q1: yes. `runtime-model-design.md:38` makes `owed` `owner` for `guard` (`stretch` at `STRETCH` or `repairs` at `REPAIRS`, both read from files, `:56`) and for `idle` (`<slug>.idle.K.md` present for K one above the guard-record count). That matches the K the file is named with (`:24`), and the answer's guard record makes it stale (`:60`). `:117` carries it into "Resume and rerun". On a rerun, iteration 1 with `owed` `owner` writes nothing, so `docket` reads `idle` at once (`:103`) with `reason` false (the file exists): no second analyst, no author or reviewer turn. For 4.06: `writing-design.md:214-218` derives `enter` from the rulings and the approved files on every call. `record` runs every iteration with no `when:` (`writing-design.md:447`) and records nothing on decision `""` (`:211`). So iteration 1 of a failure resume runs `enter`. Counting by ordinal agrees with `enter`'s N, "one above the highest present" (`gauntlet-design.md:339-340`).
Q2: no. Tried and refuted: a cross-hearing collision of `idle.K.md` under `first` (writing's revision folder holds no idle file; plan and spec review hold one hearing per slug, and `stale/` moves the files); a double `enter` after a resume (M approvals against M files gives `""`).

## G-122

Q1: yes. `runtime-model-design.md:140` writes the patch with `git diff --binary HEAD`, and `--binary` on each new-file diff.
Q2: no.

## G-123

Q1: yes. `writing-design.md:450-451` binds `decision` and `text` in the string form. `loop-nodes.md:812-816` allows the string form in `with:`, gives `''` on iteration 1, and rejects `from:`. This is the same form as plan review's `record`.
Q2: no.

## G-124 (D-101)

Q1: yes. `runtime-model-design.md:61` states `file` and `summary` as the bare `<slug>.N.txt` and `<slug>-summary.N.md`. The consumers prefix the folder: `plan-review-design.md:454-455` and `spec-review-design.md:513`.
Q2: no.

## G-125 (D-102)

Q1: yes. `writing-design.md:128-131`: `stage.py state` writes `gauntlet/write/<slug>.scope.rev<M>.txt` for each approved plan revision through `scope.py`'s `marks`. `:120-123`: the stage's steps include them in order of M. `:237` covers the divvyer and `landing-design.md:216` covers `final`. In the pass-4 scenario, step 6 is added under Stage 1 with its `Stage 1:` line (`:123`), so it is marked and cut in stage 1. The import is no defect. `marks` is imported relative to `stage.py`'s file inside the same pack, by the same mechanism `.shared/` uses (`gauntlet-intake-design.md:326`), and packaged scripts resolve within their owning package (`global-workflows.md:62`).
Q2: yes, medium. `writing-design.md:121-123`: a step in a later marks file replaces the step with the same number, stage included. But the revision must carry its `Stage <k>:` line only when it "adds or moves a step". Three texts combine:
- The reviser writes "each clause it changes as it now reads, nothing else" (`writing-design.md:252-253`).
- An approved revision holds only its changed clauses (`gauntlet-design.md:356`).
- The plan grammar reads "a plan with no stage line is one stage" (`plan-review-design.md:47`).
So when a revision rewrites a step's text and nothing else, `marks` puts that step in stage 1. Concrete failure:
1. The approved plan has `Stage 1:` with steps 1-3 and `Stage 2:` with steps 4-6. In stage 2 the owner answers `revise-plan`.
2. The reviser writes only `Step 5 [I2]: <new text>`, which is approved and entered as `rev1`.
3. `stage.py state` writes `scope.rev1.txt` with step 5 in stage 1, and that replaces step 5 of `scope.txt`.
4. Stage 2's own steps become 4 and 6. `stage.py cut` rejects any cut carrying the revised step 5, and the divvyer is told to cut only the stage's own steps (`writing-design.md:240`).
5. Stage 1 has already landed, so the revised step 5 is never written.

## G-126 (D-103)

Q1: yes. `landing-design.md:198-203`: `pose` no longer lists the final file. Node `files` (`:219-225`) depends on `[pose, final]` and adds `final.<k>.txt` for case `review` once `final` has run (the latest one after a discuss). `amicus` binds `$files.output.files` (`:227-232`). `contracts.md:48` (H32) names `files`.
Q2: no. No other node reads `$pose.output.files`. `final` skipped (case not `review`, or a discuss) still lets `files` run under `none_failed_min_one_success`.

## G-127

Q1: yes. `gauntlet-design.md:479`: the new step 3 (the tree run's writing) needs only the worktree cut design's tree run and `W:7`. `:480`: the new step 4 (the stage chain) "Needs steps 1, 2 and 3". `:483` and `:484`: steps 7 and 8 now need steps 3, and 4 and 7. Each pointer follows the file it needs (`gauntlet-tree.yaml` is step 3; `gauntlet-run.yaml`'s stage chain is step 4). No other design points at gauntlet step 3 or 4 by number. A grep of every `## Order` found pointers to steps 5, 6 and 8 only (`writing-design.md:644`, `:646`; `landing-design.md:566`, `:573`), and those are unchanged. `plan-review-design.md:501` and `spec-review-design.md:564` add the intake design's step 3, which builds `.shared/working-folder.ts` (`gauntlet-intake-design.md:345`).
Q2: no.

## G-128 (D-104)

Q1: yes. `runtime-model-design.md:142`: when `git status --porcelain` (with `gauntlet/` excluded) is not empty, `pose` first writes `gauntlet/mend/<slug>.leftover.<k>.patch` (the `--binary` form), then restores to `HEAD`. The case is `commit-failed`, and the next mender starts on the committed tip. The case clause in `landing-design.md:200` points to it. The patch is in `pose`'s files (`:203`), and both re-mend `copy-in` lists skip `.leftover.*` (`:17`, `:430`, `:549`).
Q2: no. Tried and refuted:
- The restore during a rebase in progress: a conflict fails node `rebase` before `repair` (`landing-design.md:63-66`).
- `k` reuse after a resume: `hear`'s n does not advance until an amicus, review, direction or reply file exists, and by then the tree was already restored, so no second patch overwrites the first.
- The landing clause's "before the case is read" against the home's "The case is `commit-failed`": the clause points to the home, and the home settles the order.

## Findings (JSON)

```json
{ "findings": [
  { "file": "docs/superpowers/specs/writing-design.md",
    "line": 123,
    "severity": "medium",
    "claim": "A later marks file replaces a step whole, stage included. The Stage line is required only for a revision that adds or moves a step, and a plan with no stage line is one stage, so a text-only step revision moves that step to stage 1.",
    "failure_scenario": "Plan: Stage 1 has steps 1-3, Stage 2 has steps 4-6. In stage 2 the owner revises step 5's text. The reviser writes only 'Step 5 [I2]: ...' (writing-design.md:252-253). marks gives step 5 stage 1 (plan-review-design.md:47), and scope.rev1.txt replaces step 5. Stage 2's steps become 4 and 6, stage.py cut rejects a cut carrying step 5, and the revised step 5 is never cut or written." }
] }
```
