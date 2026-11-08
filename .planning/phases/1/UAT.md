---
status: testing
phase: 1
fields_version: 1
started: 2026-11-08
updated: 2026-11-08
---

## Items

### 1. contracts.md indexes every cross-design contract and every finding is anchored
expected: contracts.md has rows (naming each design that names them) for the amicus, item file, direction file, review before landing, stages, escalation-rules key and both scope checks; every finding in REVIEW-*.md cites a design anchor and a contracts.md entry or 'internal to <design>'
criterion: AC1
status: pass
first_pass: fail
source: model
evidence: After ebffe78: awk over contracts.md column 5 | grep -c runtime-model -> 22 rows (was 0); H51 -> 'gauntlet, plan-review, runtime-model'; S5 -> 'gauntlet, writing, plan-review, spec-review, runtime-model'; grep of every **N.NN** finding head in REVIEW-*.md for a row id, 'missing row' or 'internal to' -> no unanchored line (2.13 now 'internal to intake'). Scope: the verifier's named gaps; a token-presence diff of all other cells was spot-checked (H1, H43, H51, R13, A25) and read as mention noise, not each read.
reported: behavior wrong - the index's Named-by column is incomplete and one finding is unanchored, so contracts.md does not name every spec that names each contract (AC1, ROADMAP SC1, REV-04)
severity: major
cause: contracts.md Named-by column (4th field) never lists runtime-model-design.md (0 of 156 rows), though that spec was written after the index's rows were seeded and names H24, H43, H51, S5, S14, S17 contracts; the D-98 restructure (ae19601) added the spec but did not back-fill Named by. S5 also omits plan-review and spec-review (plan-review-design.md:106, spec-review-design.md:75). REVIEW-pass2.md finding 2.13 cites 'contract put's output_format' instead of a row id or 'internal to <design>'.
fix: ebffe78, retest

### 2. Owner-control ruling and every group ruling applied in single commits
expected: one commit applies the owner-control ruling to every design it names plus contracts.md and the contradicted PROJECT/ROADMAP/REQUIREMENTS lines; each other finding group has one owner ruling applied in one commit
criterion: AC2
status: pass
first_pass: pass
source: verifier
evidence: 0549df8 carries the owner-control ruling into all seven designs, contracts.md, PROJECT/ROADMAP/REQUIREMENTS; RULINGS.md rules every G-01..G-137, each round applied with contracts.md in one commit (e9d81de, e01ea0b, 9901135, af2e0ae, 87e0734, 8c5ecc6, ae19601, 43cb8a4, 19d4e1b, bcdd58f). 101 pass-1/2 groups were ruled by the main session under the owner's delegation (RULINGS.md:5)

### 3. REVIEW-convergence.md records round 4 in the D-98 shape
expected: REVIEW-convergence.md records the D-63 one-home grep, the build-order graph check, the one runtime-model review, and the local-defect read in the owner-ruled shape or the ruling that none runs; it holds no unruled high or medium finding and is committed after the last ruling commit
criterion: AC3
status: pass
first_pass: pass
source: verifier
evidence: REVIEW-convergence.md records the one-home grep, graph check, model-spec review and owner-shaped local read, 0 unruled high/medium, end by D-108; committed 67a85e4 after bcdd58f; full homes-4.md token sweep re-run by the verifier: 0 real hits

### 4. Every assumed-Archon-feature row carries a closed verdict
expected: every section A row in contracts.md, the three owner-control behaviours included, reads documented (docs/reference/archon path), probed (approved, with record) or unsupported (with commit); none open
criterion: AC4
status: pass
first_pass: pass
source: verifier
evidence: contracts.md A1..A32 all documented/probed/unsupported with citation or hash; A30-A32 documented

### 5. Designs approved and free of retired terms
expected: grep -l '^Status: approved' lists the seven designs and owner-control; the retired-term grep over the seven designs prints nothing; every gauntlet copy-list bullet is marked resolved
criterion: AC5
status: pass
first_pass: pass
source: verifier
evidence: 9 files at Status: approved; retired-term grep over the seven designs empty; 12/12 copy-list bullets resolved

### 6. Planning docs free of retired terms
expected: grep -nE 'juror|DEFECTIVE|gauntlet/failed|task-format' over REQUIREMENTS.md, ROADMAP.md, PROJECT.md prints no line
criterion: AC6
status: pass
first_pass: pass
source: verifier
evidence: grep -nE 'juror|DEFECTIVE|gauntlet/failed|task-format' over REQUIREMENTS/ROADMAP/PROJECT prints nothing

### 7. Archon discovery and validation clean for the pack
expected: archon workflow list --json shows "errors": [] and archon validate workflows reports no error under the pack root (23 non-pack 'No default provider' errors are baseline)
criterion: AC7
status: pass
first_pass: pass
source: verifier
evidence: workflow list --json errors []; validate: 23 with errors, all 'No default provider', none under the pack

### 8. Testing policy agrees with the workflow files
expected: test-policy check passes
status: skipped
first_pass: fail
source: model
cause: test-policy check: policy-disagrees. No .github/workflows/ directory exists, so required jobs tests, fixtures and lint and the accepted commands are in no workflow file; coverage.include .shared/**/*.py and */scripts/**/*.py match no tracked file. The CI gate and .shared/ are Phase 2 deliverables (ROADMAP Phase 2: Test gate and shared layer).
reason: Owner decision 2026-11-08: the CI gate (.github/workflows/ jobs tests, fixtures, lint) and .shared/ are Phase 2 deliverables (ROADMAP Phase 2: Test gate and shared layer); optional for Phase 1.

### 9. ROADMAP and REQUIREMENTS lines reworded for D-108's end of the review loop (D-02)
expected: behavior wrong - owner ruling D-108 ended round 4 without a clean read, but the ROADMAP and REQUIREMENTS lines it contradicts were not edited as D-02 requires
origin: verifier
status: pass
first_pass: fail
source: model
evidence: After df643e6: grep -c D-108 -> ROADMAP.md 1 (Phase 1 pass 4 names the owner's ruling ending the reads), REQUIREMENTS.md 1 (REV-05 names either end, every finding ruled).
reported: behavior wrong - owner ruling D-108 ended round 4 without a clean read, but the ROADMAP and REQUIREMENTS lines it contradicts were not edited as D-02 requires
severity: minor
cause: D-108 ended round 4 by owner ruling, but ROADMAP.md:25 (pass 4: 'The phase ends only when a pass returns no finding that is not already ruled') and REQUIREMENTS.md:16 (REV-05: 'returned no unruled finding') still state a clean-read exit. D-108 amended only PLAN-7 Task 4 and D-60; neither bcdd58f nor 67a85e4 touched the two planning files, against D-02's rule that a ruling rewords the planning lines it contradicts.
fix: df643e6, retest

## Summary

total: 9
passed: 8
failed: 0
pending: 0
skipped: 1
blocked: 0
reworked: 3
