# Proposal: structure mode first

Status: approved by the owner and applied to `docs/roadmap.md` and `docs/superpowers/plans/structure-first-plan.md`, bar the edits section 4 leaves to a ruling. Line citations are to `main` at `cd6415c`. "Inferred" marks a claim no document states.

Sources: `docs/roadmap.md` (R), `docs/design.md` (DD), the structure-first spec `docs/superpowers/specs/2026-10-20-structure-first-design.md` (S), its plan `docs/superpowers/plans/structure-first-plan.md` (P), the gates core spec `docs/superpowers/specs/2026-10-20-gates-core-design.md` (GC).

## 1. What a working structure mode needs

The target: `gauntlet audit <scope> --structure` on a real repository, the owner selects a candidate, and one STRUCTURE job runs DESIGN to LAND, porting every copy, landing only when `uncovered` is empty (S:123, S:191-194).

### Plan steps needed

| Step | Needed? | Reason |
|---|---|---|
| D0 | yes | S:3 still reads "proposed"; P:180-182 records approval. |
| D1 | done | Commit `889bc23`; DD:32, DD:39, DD:100 carry it. |
| C1-C3 (`verdicts`, `design`, `causes`, `schedule`) | yes, whole | `Survey`, `Candidate` (S:47-65); `design_problems`, `uncovered` (S:119, S:123); `survey_problems` gates the survey (S:155); `route` sends REVIEW causes to fixes (S:154, S:193); `startable` runs STRUCTURE BUILD (S:191). |
| C4s | yes, minus `needs_design` | `Stage`, `Shape`, `FIRST`, `SKIPPED` (S:170-181). `needs_design` reads `Outline` (S:113), which a STRUCTURE job never has: it starts at DESIGN (S:180). P:157 Q1 already defers it. |
| C4a | no | Tests `needs_design` only (P:246). |
| C4b | yes, minus one bullet | STRUCTURE bullets (DESIGN fails on `uncovered`, SPEC keeps, REVIEW leaves on empty `uncovered`, parallel BUILD) and generic DESIGN/STUBS/REVIEW bullets (P:247). The "OUTLINE → DESIGN or PLAN" bullet is JOB-shape only. |
| C5 | yes | Builds C4. |
| R1 `architect` | yes | DESIGN's role (S:225). Waits on Q8 (P:164). |
| S1-S3 | yes, mostly | `write_design`, `read_design`, `write_causes`, `write_survey`, `open_structure` (S:199-204); `design_screen`, `causes_section`, `survey_screen` (S:210-213). `write_offers` and `structure_section` serve spawns and offers (S:202, S:212), feature mode only. |
| R2b `grouper` | yes | Audit groups survey findings into causes (R:117, S:155) and REVIEW groups findings (S:193). |
| R3 `surveyor` | yes | The audit itself (S:228) and the REVIEW survey behind the landing rule (S:194). |
| R2a `structure-reviewer` | not for a first landing (inferred) | Runs in every REVIEW (S:231), but the landing rule rests on the surveyor and `uncovered` (S:194). Can be a shown bypass (R:11, DD:238). |
| C6, C7 | no | CoreMissing, offers, held paths, spawned jobs (P:276) are feature-job behavior (S:188-190). |
| S4-S6 | yes, re-pointed | P:288 makes them wait on C7; nothing in `audit --structure` (S:216-219) reads a CoreMissing row. They need C5, S3, R3. |

### Milestones it depends on

| Milestone | Dependency | Reason |
|---|---|---|
| M0 | done | R:17 "Open: none". |
| Agents | yes | `core-builder`, `seam-builder` live proofs fall at M1, M2 (R:23); `architect` proof outstanding (R:23) and it writes each milestone's design step (GC:368, `docs/superpowers/specs/2026-10-18-agents-design.md:27`). |
| Gates | yes | All code waits on it, mutation gate included (P:169, R:29). Makefile runs 5 gates, no mutation gate yet (`Makefile:6-11`). |
| M1 | yes, nearly whole | `decide`, `state.json`, `trace.jsonl`, resume (R:35-42). M1's design step must settle the record codec, error family, stage table as data, role registry, State/Answer builders (GC:378-383), all of which S1 and C4s need (P:170, P:241, P:259). |
| M2 | yes, whole | Every role launches through the launcher (DD:127); every git command and the job worktree go through `seams/git.py` (DD:155, R:51). |
| M3 | yes, re-scoped | `runner.py` (red run, gates), `screens.py`, land (R:59-62). Its driver `gauntlet run <brief.md>` and its feature fixtures (R:57, R:64) are not needed. |
| M4 | yes, for a real repo | Prosecutor rounds on the design (S:314, decision 2) and the arbiter that rejects a spec dropping a `keeps` line (S:192, S:339 decision 16); the stop screen (R:71). |
| M5 | yes, for a real repo (inferred) | Not named by S; R places it before the pilot (R:75-82, R:93). Tests written against full source weaken the keeps lines locked before any port (S:192). |
| M6 | partly | Grouper and cause routing: yes (S:193). Repo reviewers, bailiff, full land: bypassable for a first landing (R:11), needed for "no bypass". |
| M7 | replaced | A structure pilot replaces the feature pilot as the real-repo check (R:95-97). |
| M8 | only two sentences | "A STRUCTURE job ports every copy and lands only when `uncovered` is empty" and "The surveyor also runs in a structure job's Review" (R:103). The rest (`reopen.py`, CoreMissing, offers) is feature mode (R:101-105). |
| M9, M11, M12, M13 | no | Brief/detective (R:109), repo roles (R:123), epics: STRUCTURE jobs run one after another until M12 (S:165, S:216). |
| M10 | second half only | `--structure` (R:117); the test audit (R:115) is not needed. |

## 2. Proposed order

1. **Unchanged:** M0, Agents, Gates, M2, M5. Ordering rules 1-5 (R:9-13) unchanged.
2. **M1, trimmed:** as R:35-44 minus `needs_design` and the OUTLINE rows of `decide`. FIRST/SKIPPED keep all three shapes as data (S:180-181); only the rows a STRUCTURE job walks are tested here.
3. **M2.**
4. **M3s, thin STRUCTURE job** (replaces M3's slot): `gauntlet audit <fixture> --structure` → surveyor → grouper → `survey_problems` → survey screen → select → `open_structure` → DESIGN (one architect, no rounds) → PLAN → SPEC with keeps lines → STUBS → TESTS → red run → LOCK → BUILD under `startable` → REVIEW (surveyor, grouper, `route` FixStep, `uncovered`) → LAND. Bypassed and shown: prosecutor, arbiter, examiner, repo reviewers, structure reviewer, bailiff. Carries S4-S6, R1, R2b, R3, S1-S3, and M10's structure Done-when (R:119, its structure clauses).
5. **M4s:** M4 as written (R:68-73), with the arbiter's keeps rejection added to its Done-when.
6. **M5.**
7. **M6s:** M6 minus its feature-job clause ("a job without a design that copies…", R:91); R2a joins here.
8. **M7s, structure pilot:** an audit and three STRUCTURE jobs landed on a real repository (e.g. `hqptuner`, R:95).
9. **Feature mode after:** M3f (`gauntlet run`, outline flag, C4a, `needs_design`, DESIGN skipped by rule; R:57-64), M6's feature clause, M7f feature pilot, M8 (reopen, CoreMissing, C6-C7, offers), M9, M10's test audit, M11, M12, M13.

### Built differently because feature mode is absent

- **DesignChange in a STRUCTURE job's REVIEW.** `route` can return one when the job has a design (S:154); it "reopens DESIGN on the change alone" (S:193), which is M8's reopen (R:103). Until M8: stop screen (M4) or, before M4, a stop row in `state.json` (inferred; needs a ruling).
- **PLAN input for a STRUCTURE job.** DD:40 gives the planner "brief, outline, discovery, objections"; a STRUCTURE job has none of the first three, only "its candidate and the copies as its brief" (S:191) and the approved design whose order "becomes its plan's steps" (S:191). The planner's input for this shape is unspecified (gap; needs an architect ruling).
- **S5's second clause.** "without `--structure` the test-audit shape runs" (P:288) tests a shape not yet built. Until M10's test audit: drop the clause or make bare `audit` refuse (inferred; needs a ruling).
- **S4-S6 inputs:** C5, S3, R3 instead of C7 (P:288).
- **R3** moves from M8 (P:282) to M3s; R2b from M6 (P:270) to M3s.
- **Parallel BUILD** (S:191, decision 17 at S:341) arrives in the first end-to-end job, not after M8. DD:75 commits each finished step on one job branch; how two implementers' commits interleave in one worktree is not specified (inferred risk; a sequential first cut would need an owner ruling against decision 17).
- **M3's fixture repository** (GC:396) is first shaped for a copied concern (R:119), not a brief.

## 3. Risks and costs

- **Hardest shape first.** A STRUCTURE job "skips nothing" (S:178) and alone adds survey, design, keeps, parallel BUILD and an `uncovered` landing rule. Rule 3 asks for the thinnest job first (R:11); the thinnest STRUCTURE job is thicker than M3's feature job (R:57). Rule 1 (R:9) is already spent on the launcher (M0 done), so it gives no cover.
- **Validated late:** Brief, Discovery, Outline and the planner's outline answer (DD:36-38) go untested end to end until M3f. A planner role written for STRUCTURE PLAN may need rework when Outline arrives (inferred).
- **Decision 1 needs both modes.** The structure reviewer's value on feature jobs (S:312, decision 1) and the COPY check on no-design jobs (R:91) wait for M3f/M6.
- **No guard without M4.** Until M4s, keeps lines are added by the harness but nothing rejects a spec that drops one (S:192), so M3s must not run on a real repository (inferred).
- **Cost unknown.** A port touches every caller (S:321 decision 7); launches per job scale with copies. Round-cap cost is an open question settled only by a pilot trace (R:146).
- **Charter fit.** The charter targets established codebases (`docs/charter.md:8`); structure jobs are refactors of such codebases, so the reorder fits it. No charter line favors feature mode first.
- **Bad idea if:** the owner's pilot repository needs features before refactors; or the PLAN-input gap above cannot be ruled without designing Outline first; or parallel BUILD in one worktree proves unsafe and decision 17 is not relaxed.
- **Cheap parts:** C1-C3, C4s, S1-S3 are the same code in either order; only C4a, C6-C7 and offers move later. Nothing written so far under `gauntlet/` is thrown away (it is empty: `gauntlet/core/__init__.py`, `gauntlet/seams/__init__.py`).

## 4. Edits the reorder would need (not made)

### `docs/roadmap.md`

1. M1 (R:35-44): drop `needs_design`/OUTLINE rows; say STRUCTURE rows are its tested rows.
2. Replace M3 (R:55-64) with M3s above; move today's M3 text to a new M3f after M7s.
3. M4 (R:66-73): add the arbiter's keeps rejection to Done-when.
4. M6 (R:84-91): move the no-design COPY clause (R:91) to M3f/M6f.
5. M7 (R:93-97): structure pilot; add M7f feature pilot after M3f.
6. M8 (R:103): move the `uncovered` landing sentence and the REVIEW-surveyor sentence to M3s.
7. M10 (R:113-119): move the `--structure` paragraph and its Done-when clauses to M3s; keep the test audit.
8. Open questions (R:145-148): "M3 wall clock" and "M7 trace" re-pointed to M3s and M7s.

### `docs/superpowers/plans/structure-first-plan.md`

1. Q1 (P:157): `needs_design` moves to the feature phase, not C4s.
2. C4s (P:239-242): drop `needs_design` and `Outline` from Inputs and Writes; C4a (P:246) to the feature phase.
3. C4b (P:247): split out the OUTLINE bullet.
4. R2b (P:270-272) and R3 (P:282-284): M3s, inputs Q8 and C5.
5. S1-S3 (P:257-268): `write_offers`, `structure_section` to the feature phase.
6. S4-S6 (P:286-288): inputs C5, S3, R3; milestone M3s; S5's test-audit clause per §2.
7. C6, C7 (P:274-280): marked feature phase.
8. New open questions: PLAN input for a STRUCTURE job; DesignChange before M8; parallel BUILD commits in one worktree.
9. Chains (P:175) and Parallel sets (P:290-292) follow the moved steps.
