---
phase: 1
status: complete
completed: 2026-11-08
---

# Phase 1: Design review - Summary

The seven Gauntlet designs, the owner-control design and a new `runtime-model-design.md` (the shared resume, loop and bounds, hearing state, commit model and ledger, written once) were reviewed over six passes. `contracts.md` became an index of homes with no values in it. Every finding group, from G-01 to G-137, was ruled by the owner and applied, and all nine spec files now read `Status: approved`. The review loop ended by the owner's ruling D-108, not by a clean read.

## What shipped

- Cross-design contract index: `docs/superpowers/specs/contracts.md`. It has sections H, P, F, S, R and A. Each row names one home and every spec that names it, and holds no value (D-01 as amended by D-98).
- The shared runtime model: `docs/superpowers/specs/runtime-model-design.md`. It is the one home for the facts the designs used to copy, and each design keeps a heading pointer in place of its copy (D-98).
- Review record: `.planning/phases/1/REVIEW-pass1.md` to `REVIEW-pass6.md`, `RULINGS.md`, `reviews/`, `PROBES.md` and `DECISION-REVIEW.md`.
- Convergence record: `.planning/phases/1/REVIEW-convergence.md` (commit 67a85e4).
- One-home token list: `.planning/phases/1/reviews/homes-4.md`.
- Section A verdicts closed. Each row is `documented`, `probed` or `unsupported` with its hash; A11 and A19 cite e9d81de.
- Approved specs: the seven designs, the owner-control design and the runtime model (commit afa4f14).
- Planning lines that the rulings contradicted were reworded: CONTEXT AC3 and D-01, ROADMAP passes 1 and 4 and criterion 3, and REQUIREMENTS REV-04 and REV-05.

## Commits

| Plan | Task | Commit | Description |
|---|---|---|---|
| 1 | 1 | 1770c57 | inventory skeleton seeded from the copy list |
| 1 | 2 | d20bb2e | node references and hand-off fields |
| 1 | 3 | 0f2a7b2 | paths named by two or more designs |
| 1 | 4 | ded274d | fence x variable matrix |
| 1 | 5 | 6fb0044 | scripts and roles with resolving folder |
| 1 | 6 | 6eb5df7 | assumed Archon features |
| 2 | 1 | eb13b6e | vendor the MCP-servers guide |
| 2 | 2 | 72d5030, 3cac029 | Archon feature verdicts (before and after probes) |
| 2 | 3 | 0e8203a | build orders as one graph |
| 2 | 4 | 6efe8f5 | pass-1 adversarial review of each design |
| 2 | 5 | ac6c0c4 | dedupe and group by inventory row |
| 3 | 1 | 0d08176, 14f5985 | routes D-11 to D-37 and pass-1 rulings |
| 3 | 2 | e9d81de, e01ea0b | apply rulings G-01 to G-50 |
| 3 | 3 | dfd1158, 47a356a, 9901135, af2e0ae, 1035d43, 87e0734 | pass 2: record, decision reviews, apply, rulings |
| 3 | 3 | 060107b, 60247c2, 8c5ecc6 | pass 3: record, D-79, rulings G-104 to G-119 applied |
| 4 | 1-8 | (rode 0549df8) | owner-control ruling drafted into the seven designs |
| 5 | 6 | 0549df8 | owner-control design carried into designs, contracts and planning lines |
| 6 | 1-8 | (rode ae19601) | round-4 restructure drafted: runtime model, index form of contracts.md |
| 7 | 2 | ae19601 | land the D-98 restructure, one home per fact |
| 7 | 4 | 43cb8a4 | pass-4 rulings G-120 to G-128 (D-99 to D-104) |
| 7 | 4 | 19d4e1b | pass-5 rulings G-129 to G-131 (D-105 to D-107) |
| 7 | 4 | bcdd58f | pass-6 rulings G-132 to G-137 (D-109, D-110) |
| 7 | 5 | 67a85e4 | convergence record, ended by D-108 |
| 7 | 6 | 0ba2298 | section A hashes for A11 and A19 |
| 7 | 7 | afa4f14 | approve the seven designs and the runtime model spec |

## Deviations

- [deviation] Plan 3 asserted the round-4 review, the convergence record and its Tasks 4 and 5. D-84 superseded them and plans 6 and 7 carried them out, and the owner closed plan 3 as superseded (no commit).
- [deviation] Plan 3: D-79 (60247c2) replaced `/cad-decision-review` and the one-commit-per-round rule for round 3. The owner rules every group, and drafts stay uncommitted until the closed review's fixes.
- [deviation] Plan 6, Task 8 Verify: the grep for the old AC3 phrase still prints CONTEXT line 115 (D-98), which quotes the phrase while ruling its rewrite. The plan forbids editing that decision line.
- [deviation] Plan 6, commit protocol: it made no task commits, by its own Must-be-true. Plan 7's single D-98 commit (ae19601) landed the work.
- [deviation] Round 4 did not end at a read with no new high or medium finding. Passes 4, 5 and 6 each found new ones (11, 3 and 6). The owner ended the loop by D-108, "Rule pass 6, then stop reads". The pass-6 round text was read only by its D-79 closed review.

## Open items

- The phase exit bar of AC3 and D-60 was not met by a read. Convergence rests on D-108, and `REVIEW-convergence.md` states it.
- The risk-surface review of plan 7 (`REVIEW-risk_surface-plan-7.md`, `ADJUDICATION-risk_surface-plan-7.json`) passed. Four findings survived unfixed and were filed on ohshitgorillas/gauntlet at the owner's word. They are fingerprints a65c9e50f716e564, 3307ed5485f79960, 180228073a728614 and e5426ab16b1c4361:
  - the mend's leftover and settle patches are lost on `archon complete --force`;
  - writing's `result` can fail between the blocks file and the patch;
  - `baseline`'s restore undoes `copyFiles` and `postCreate`;
  - the set-aside prefix clash between `X` and `X-summary`.
- The sweep of all 62 `homes-4.md` rows was not re-run as one pass after the last round; each round grepped its changed tokens and their neighbours.
- Residual in G-129: a brief-command run that rewrites a path the agent had already dirtied leaves both changes on that path.
- Executor choices recorded in RULINGS.md:
  - G-134: the owed-patch rule reuses `hear`'s numbering, so `hear`'s `n` can skip a number; the patch is named `settle.<s>.patch`.
  - G-136: the direction file takes N one above the highest move.
  - G-137: the first cut's cause is `INPUTS_SPEC` and its approved revisions.
- Plan 3 carried items:
  - a mend commit followed by a node failure before the mend is recorded lets an unreviewed commit through on resume;
  - the menders have no rule for the commit tool's "nothing" answer.
- Scratch directories left in /tmp by subagents, because a hook blocks `rm -rf`, need deleting by hand: `/tmp/tmp.Yett1YlNck`, `/tmp/g6.TUhrSQ` and `/tmp/g6.wZriIO`. Plan 3 left `/tmp/tmp.xTDZRgjxE3` and `/tmp/tmp.M5j1ysgIxi`.

## Goal check

The commits in the table above plausibly deliver the goal, consistency reached in one converging pass rather than finding by finding, in its D-98 shape, with one exception:
- **One home per fact.** Each restated fact now has one home: `runtime-model-design.md` holds the shared model, and `contracts.md` is an index of homes (ae19601). `homes-4.md` records a result of 0 per token.
- **Every group ruled.** Every finding group from G-01 to G-137 carries an owner ruling, applied in one commit per round: 0549df8, 43cb8a4, 19d4e1b, bcdd58f, plus plan 3's rounds.
- **Section A closed.** 0ba2298; no `pending probe` or `hash cited at close` is left.
- **Approved.** `grep -l '^Status: approved' docs/superpowers/specs/*-design.md | wc -l` prints 9.
- **The exception.** The phase did not end at a pass returning no new high or medium finding. Pass 6 found 6, and the loop stopped by D-108. The designs are therefore approved with a known rate of defects still being found per read, and four surviving risk-surface mediums and lows are filed as issues.
- **Checks.** `archon workflow list --json` shows `"errors": []`, and `archon validate workflows` holds at its 23-error baseline. The fence suite printed `71 passed`.

complete locally, not CI-verified
