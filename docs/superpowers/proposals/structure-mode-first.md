# Proposal: structure mode first

The governing order lives in `docs/roadmap.md` and `docs/superpowers/plans/structure-first-plan.md`; the roadmap's M6f and the spec's decisions 18 to 21 govern the questions below. "Inferred" marks a claim no document states.

Sources: `docs/roadmap.md` (R), `docs/design.md` (DD), its plan `docs/superpowers/plans/structure-first-plan.md` (P).

## 1. What a working structure mode needs

The target: `gauntlet audit <scope> --structure` on a real repository, the owner selects a candidate, and one STRUCTURE job runs DESIGN to LAND, porting every copy, landing only when `uncovered` is empty.

### Plan steps needed

| Step | Needed? | Reason |
|---|---|---|
| D0 | yes | The structure spec governs structure mode. |
| C1-C3 (`verdicts`, `design`, `causes`, `schedule`) | yes, whole | `Survey`, `Candidate`; `design_problems`, `uncovered`; `survey_problems` gates the survey; `route` sends REVIEW causes to fixes; `startable` runs STRUCTURE BUILD. |
| C4s | yes, minus `needs_design` | `Stage`, `Shape`, `FIRST`, `SKIPPED`. `needs_design` reads `Outline`, which a STRUCTURE job never has: it starts at DESIGN. Q1 defers `needs_design` to feature mode. |
| C4a | no | Tests `needs_design` only. |
| C4b | yes, minus one bullet | STRUCTURE bullets (DESIGN fails on `uncovered`, SPEC keeps, REVIEW leaves on empty `uncovered`, parallel BUILD) and generic DESIGN/STUBS/REVIEW bullets. The "OUTLINE → DESIGN or PLAN" bullet is JOB-shape only. |
| C5 | yes | Builds C4. |
| R1 `architect` | yes | DESIGN's role. Waits on Q8. |
| S1-S3 | yes, mostly | `write_design`, `read_design`, `write_causes`, `write_survey`, `open_structure`; `design_screen`, `causes_section`, `survey_screen`. `write_offers` and `structure_section` serve spawns and offers, feature mode only. |
| R2b `grouper` | yes | Audit groups survey findings into causes and REVIEW groups findings. |
| R3 `surveyor` | yes | The audit itself and the REVIEW survey behind the landing rule. |
| R2a `structure-reviewer` | not for a first landing (inferred) | Runs in every REVIEW, but the landing rule rests on the surveyor and `uncovered`. Can be a shown bypass. |
| C6, C7 | no | CoreMissing, offers, held paths, spawned jobs (P:276) are feature-job behavior. |
| S4-S6 | yes | Nothing in `audit --structure` reads a CoreMissing row. Their inputs for structure mode are C5, S3, R3. |

### Milestones it depends on

| Milestone | Dependency | Reason |
|---|---|---|
| Agents | yes | `core-builder`, `seam-builder` live proofs fall at M1, M2; `architect` requires a live proof and writes each milestone's design step. |
| Gates | yes | All code waits on it, mutation gate included. |
| M1 | yes, nearly whole | `decide`, `state.json`, `trace.jsonl`, resume. M1's design step must settle the record codec, error family, stage table as data, role registry, State/Answer builders, all of which S1 and C4s need. |
| M2 | yes, whole | Every role launches through the launcher; every git command and the job worktree go through `seams/git.py`. |
| M3 | structure scope | `runner.py` (red run, gates), `screens.py`, land. Its driver `gauntlet run <brief.md>` and its feature fixtures are not needed. |
| M4 | yes, for a real repo | Prosecutor rounds on the design and the arbiter that rejects a spec dropping a `keeps` line; the stop screen. |
| M5 | yes, for a real repo (inferred) | Not named by the structure spec; the roadmap places it before the pilot. Tests written against full source weaken the keeps lines locked before any port. |
| M6 | partly | Grouper and cause routing: yes. Repo reviewers, bailiff, full land: bypassable for a first landing, needed for "no bypass". |
| M7 | structure pilot | A structure pilot is the real-repo check. |
| M8 | only two sentences | "A STRUCTURE job ports every copy and lands only when `uncovered` is empty" and "The surveyor also runs in a structure job's Review". The rest (`reopen.py`, CoreMissing, offers) is feature mode. |
| M9, M11, M12, M13 | no | Brief/detective, repo roles, epics: STRUCTURE jobs run one after another until M12. |
| M10 | structure half only | `--structure`; the test audit is not needed. |

## 2. Proposed order

1. **Prerequisites and ordering:** M0, Agents, Gates, M2, M5 retain their roadmap requirements. Roadmap ordering rules 1-5 apply.
2. **M1, structure scope:** the roadmap's M1 requirements except `needs_design` and the OUTLINE rows of `decide`. FIRST/SKIPPED keep all three shapes as data; only the rows a STRUCTURE job walks are tested here.
3. **M2.**
4. **M3s, thin STRUCTURE job:** `gauntlet audit <fixture> --structure` → surveyor → grouper → `survey_problems` → survey screen → select → `open_structure` → DESIGN (one architect, no rounds) → PLAN → SPEC with keeps lines → STUBS → TESTS → red run → LOCK → BUILD under `startable` → REVIEW (surveyor, grouper, `route` FixStep, `uncovered`) → LAND. Bypassed and shown: prosecutor, arbiter, examiner, repo reviewers, structure reviewer, bailiff. Carries S4-S6, R1, R2b, R3, S1-S3, and M10's structure Done-when clauses.
5. **M4s:** the roadmap's M4 requirements, including the arbiter's keeps rejection in its Done-when.
6. **M5.**
7. **M6s:** M6 except its feature-job clause ("a job without a design that copies…"); R2a belongs here.
8. **M7s, structure pilot:** requires an audit and three STRUCTURE jobs to land on a real repository (e.g. `hqptuner`).
9. **Feature mode after:** M3f (`gauntlet run`, outline flag, C4a, `needs_design`, DESIGN skipped by rule), M6's feature clause, M7f feature pilot, M8 (reopen, CoreMissing, C6-C7, offers), M9, M10's test audit, M11, M12, M13.

### Built differently because feature mode is absent

- **DesignChange in a STRUCTURE job's REVIEW.** `route` can return one when the job has a design; it "reopens DESIGN on the change alone", which is M8's reopen (R:103). Until M8: stop screen (M4) or, before M4, a stop row in `state.json` (inferred; needs a ruling).
- **PLAN input for a STRUCTURE job.** DD:40 gives the planner "brief, outline, discovery, objections"; a STRUCTURE job has none of the first three, only "its candidate and the copies as its brief" and the approved design whose order "becomes its plan's steps". The planner's input for this shape is unspecified (gap; needs an architect ruling).
- **S5's second clause.** "without `--structure` the test-audit shape runs" (P:288) tests a shape not yet built. Until M10's test audit: drop the clause or make bare `audit` refuse (inferred; needs a ruling).
- **S4-S6 inputs:** C5, S3, R3 instead of C7 (P:288).
- **R3 and R2b** belong to M3s.
- **Parallel BUILD** arrives in the first end-to-end job, not after M8. DD:75 commits each finished step on one job branch; how two implementers' commits interleave in one worktree is not specified (inferred risk; a sequential first cut would need an owner ruling against decision 17).
- **M3's fixture repository** is first shaped for a copied concern (R:119), not a brief.

## 3. Risks and costs

- **Hardest shape first.** A STRUCTURE job "skips nothing" and alone adds survey, design, keeps, parallel BUILD and an `uncovered` landing rule. Rule 3 asks for the thinnest job first (R:11); the thinnest STRUCTURE job is thicker than M3's feature job (R:57). Rule 1 (R:9) is already spent on the launcher (M0 done), so it gives no cover.
- **Validated late:** Brief, Discovery, Outline and the planner's outline answer (DD:36-38) go untested end to end until M3f. A planner role written for STRUCTURE PLAN may need rework when Outline arrives (inferred).
- **Decision 1 needs both modes.** The structure reviewer's value on feature jobs and the COPY check on no-design jobs wait for M3f/M6.
- **No guard without M4.** Until M4s, keeps lines are added by the harness but nothing rejects a spec that drops one, so M3s must not run on a real repository (inferred).
- **Cost unknown.** A port touches every caller; launches per job scale with copies. Round-cap cost requires a pilot trace to answer.
- **Charter fit.** The charter targets established codebases (`docs/charter.md:8`); structure jobs are refactors of such codebases, so the reorder fits it. No charter line favors feature mode first.
- **Bad idea if:** the owner's pilot repository needs features before refactors; or the PLAN-input gap above cannot be ruled without designing Outline first; or parallel BUILD in one worktree proves unsafe and decision 17 is not relaxed.
- **Cheap parts:** C1-C3, C4s, S1-S3 require the same code in either order; C4a, C6-C7 and offers belong to feature mode.

## 4. Roadmap and plan requirements

### `docs/roadmap.md`

1. M1: `needs_design`/OUTLINE rows are outside its scope; STRUCTURE rows are its tested rows.
2. M3s follows the structure sequence above; M3f carries the feature sequence after M7s.
3. M4: Done-when includes the arbiter's keeps rejection.
4. M3f/M6f carry M6's no-design COPY clause.
5. M7s is the structure pilot; M7f is the feature pilot after M3f.
6. M3s carries M8's `uncovered` landing sentence and REVIEW-surveyor sentence.
7. M3s carries M10's `--structure` requirements and their Done-when clauses; M10 retains the test audit.
8. Open questions: the wall-clock question concerns M3s and the pilot-trace question concerns M7s.

### `docs/superpowers/plans/structure-first-plan.md`

1. Q1: `needs_design` belongs to the feature phase, outside C4s.
2. C4s Inputs and Writes exclude `needs_design` and `Outline`; C4a belongs to the feature phase.
3. C4b: the OUTLINE bullet belongs to the feature phase.
4. R2b and R3: M3s, inputs Q8 and C5.
5. S1-S3: `write_offers`, `structure_section` belong to the feature phase.
6. S4-S6: inputs C5, S3, R3; milestone M3s; S5's test-audit clause per §2.
7. C6, C7: feature phase.
8. New open questions: PLAN input for a STRUCTURE job; DesignChange before M8; parallel BUILD commits in one worktree.
9. Chains and Parallel sets follow the step order above.
