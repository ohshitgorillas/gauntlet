PLAN CHECKPOINT: decision
Plan: .planning/phases/1/PLAN-3.md
Tasks: 2 of 5 (Task 3, round 3: the pass-3 record is committed; the rulings on G-104..G-119 are pending)
| Task | Commit | Note |
|---|---|---|
| 1 (routes, D-11..D-37) | 0d08176 | earlier dispatch: 50 groups routed, 27 load-bearing |
| 1 (rulings) | 14f5985 | 50 `Ruling:` lines, one per group |
| 2 (apply rulings, G-01..G-44, G-46..G-50) | e9d81de | designs, contracts.md, ROADMAP.md, REQUIREMENTS.md, PROJECT.md; copy list resolved |
| 2 (G-45) | e01ea0b | owner's option A, K = 2 |
| 3 round 2 (record) | dfd1158 | `REVIEW-pass2.md`, `reviews/conv-*.md`, `reviews/convergence-graph.md`, CONTEXT.md D-38..D-59 |
| 3 round 2 (decision reviews) | 47a356a | `DECISION-REVIEW.md` D-38..D-59, `RULINGS.md` pass-2 table, `reviews/dr2/` |
| 3 round 2 (apply, cross-design) | 9901135 | nine cross-design groups and all contracts rows |
| 3 round 2 (apply, per design) | af2e0ae | the seven designs and contracts.md |
| 3 round 2 (rulings after application, recorded) | 1035d43 | planning files only |
| 3 round 2 (apply the three, record rulings, graph) | 87e0734 | plan-review, spec-review, writing designs, contracts.md, `REVIEW-pass2.md` section 10, `reviews/convergence-graph-3.md` |
| 3 round 3 (record) | 060107b | `REVIEW-pass3.md` (41 findings 3.01-3.41, groups G-104..G-119), the seven `reviews/conv3-*.md`, CONTEXT.md D-60..D-78. Gates: pre-commit passed (filepawl), lease-check ok (9 staged), `archon workflow list --json` `"errors": []`, `archon validate workflows` 4 valid / 23 with errors (the baseline) |

Round 3 record (060107b):
- Findings: 41 (30 new, 11 matching a ruled group, all open). Severity as the reviewers gave it: 7 high (3.09, 3.17, 3.18, 3.28, 3.29, 3.30, 3.40), 17 medium, 17 low. Anchors: 41 of 41 hold at the working tree (= 87e0734 for designs and contracts.md); every cited row id exists. The seven highs' claims were read against their cited doc and design lines and hold; medium and low claims were not re-derived one by one.
- Groups (root cause, D-62): G-104 resume/rerun owed from files (3.10, 3.11, 3.19, 3.40); G-105 rounds.py one hearing per folder (3.18, 3.30); G-106 writing leftover edits and failed commits (3.28, 3.29, 3.32, 3.33, 3.34); G-107 vacate body-sink shape (3.09, 3.17, 3.15); G-108 restated facts off their home (3.01, 3.02, 3.04, 3.08, 3.22, 3.23, 3.25, 3.38, 3.41); G-109 slug after its phase (3.03, 3.24); G-110 standalone inputs (3.16, 3.21); G-111 run-start checks (3.05, 3.26, 3.27); G-112 intake "" (3.06, 3.07); G-113 reporter inputs (3.12); G-114 cite state (3.13, 3.14); G-115 spec bound (3.20); G-116 coder blindness (3.31, 3.35); G-117 divvy cause after PLAN (3.36); G-118 seal message vs commit-msg hook (3.37); G-119 writing docket base (3.39). Grep check: 41 of 41 ids in exactly one Members line.
- Routes: 13 load-bearing (D-66..D-78: G-104..G-109, G-111, G-113..G-118); 3 ask-user seam (G-110, G-112, G-119).
- CONTEXT.md: process rulings (a)-(f) as D-60..D-65; load-bearing groups as D-66..D-78.

CHECKPOINT (decision), Task 3 round 3, rulings.
Need: (1) run `/cad-decision-review` on CONTEXT.md D-66..D-78 (groups G-104..G-109, G-111, G-113..G-118); (2) take the owner's ruling, through the ask-user seam, on G-110, G-112 and G-119, and the owner's rulings on all 16 groups (options in `REVIEW-pass3.md` section 8). Then continue this plan at Task 3 round 3: record the rulings in `REVIEW-pass3.md` section 9 and `RULINGS.md`, apply them in one commit under D-61 (node ids or headings, one home per fact), grep each ruling at every place its fact appears (D-63). Later steps, not run by the executor: the spiker dispatch copying the designs' YAML into a scratch folder outside the pack and running `archon validate workflows` on it (D-64), then round 4 with the D-65 brief and the D-60 exit bar.

Deviations:
- [deviation] Plan 3 Task 3 Verify and AC3 assert the convergence record lists "no finding without a ruled group" after a round with zero new findings; the owner's ruling (a) (D-60) sets round 4's exit bar at no new high or medium finding, lows recorded and fixed without reopening a round. Recorded in D-60 as: a round-4 low gets a group and a ruling, is fixed, and is listed with that group in `REVIEW-convergence.md`, so Task 3's count of 0 still holds; no round 5 for lows.
- [deviation] D-03 says Phase 1 runs no probes; the owner's ruling (e) (D-64) adds a spiker running `archon validate workflows` on the designs' YAML outside the pack. D-64 records that it amends D-03 for this check.
- Carried unchanged: D-13 amendment (`FENCE_WRITE=gauntlet/scratch`), G-42 (`$LOOP_PREV.state.output.move`, later replaced by G-90), G-27 (`verdict $case.output.verdict`); see `reports/plan-3.6.md`.

Open items:
- Choice: the owner's four named groups take G-104..G-107 in the owner's order and the executor's groups start at G-108 (the dispatch said "new groups numbered from G-104"; the four needed ids too).
- Choice: 3.15 (`plan-review-design.md:144`, vacancy past iteration 200) was added to the owner's group G-107 as the same root cause (`vacate` acting one iteration late); `REVIEW-pass3.md` says so at the group.
- Choice: the load-bearing groups were written as D-66..D-78 in this commit, as Task 1 and pass 2 (dfd1158) did, so `/cad-decision-review` can run on them before the rulings (D-05). The dispatch named only the process rulings for CONTEXT.md.
- Host: the writing reviewer left a scratch repository at `/tmp/tmp.xTDZRgjxE3` (124K; a hook blocks `rm -rf` for agents). Not started by this dispatch; left in place.
- `contracts.md` H38 names `vacate` in writing too, but `writing-design.md` has no node `vacate` (grep); no reviewer filed it. Noted for the G-107 application.
- Carried from `reports/plan-3.6.md`: the D-58 juror-route fixture and `juror.md` sentence; `gauntlet-design.md:31` not naming `bash run.sh`; executor-chosen mechanisms where rulings were silent; ROADMAP/PROJECT Phase 2 lines, LAND-01, RUN-14 not edited; Task 4 flags for A10 and A19.
- Uncommitted by design, not mine: `.gitignore`, `.planning/STATE.md`, `.planning/config.json`, `.planning/phases/1/reports/`, `reviews/pass2-*`.
- Previous report rotated to `reports/plan-3.6.md`.
- Process: no scaffolding written; shell `sed -n`, `grep` and `du` were read-only probes. No process left running. Full suite not run: the plan is not at its last task.
