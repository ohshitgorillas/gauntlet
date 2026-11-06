PLAN CHECKPOINT: decision
Plan: .planning/phases/1/PLAN-3.md
Tasks: 2 of 5 (Task 3 in progress: rounds 1 to 3 committed; the round-4 review and the convergence record remain)
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
| 3 round 3 (record) | 060107b | `REVIEW-pass3.md`, `reviews/conv3-*.md`, CONTEXT.md D-60..D-78 |
| 3 round 3 (D-79) | 60247c2 | orchestrator: CONTEXT.md D-79 |
| 3 round 3 (rulings G-104..G-119 applied, D-79 fixes) | 8c5ecc6 | seven designs, contracts.md, PROJECT.md, ROADMAP.md, REQUIREMENTS.md, CONTEXT.md, REVIEW-pass3.md, RULINGS.md (14 paths) |

Step 0 (diff of the stopped executor's partial edits against the instructions and the round-3 section of the previous report, `reports/plan-3.8.md`)

Kept (matches the instructions or the round-3 section):
- Every round-3 draft edit of the earlier report: G-104 (owed `owner`, `cite.py` exit 0 on a missing plan, landing `unreviewed`/`test-head`/`confirm`/`repair`/`hear`/`handoff`, fixture `repair-resumed`), G-105 `first`, G-106 commit tool and `result` leftover patch, G-107 `vacant`/`close`/`vacate` after the group, G-108 copy-list bullets and row H41, G-109 `slug` in `.shared/pin.py` and intake `from-file.py`, G-110, G-112, G-113 reporter prompts and row R13, G-114 `cite.py` JSON line and row S17, G-116 `FENCE_CUT`, G-117, G-118, G-119.
- D-79 medium fixes the stopped executor had already made, verified by grep and read: G-104 hearings (no "with no agent turn" in either fixture line or the ledger claims; fixture "a rerun finding an APPROVED/READY unanswered, asked again"); G-105 (`since`, `attempts`, `non_responsive`, `stretch`, owed `owner` counted from `first`, `spec-review-design.md` `state`); G-104 landing (`hear` retries only when no review of n or higher exists for the latest mend); G-111 in `gauntlet-design.md` node `env-check` (checks `git remote get-url <remote>`, `<remote>` being `worktree.remote`, `origin` when unset, and no base branch).
- `intake` `from-file` script, `.shared/red.py` `cut`, `GAUNTLET_FINAL_SUBJECT`, `leftover` patch, planning lines in PROJECT.md, ROADMAP.md, REQUIREMENTS.md.

Undone (did not match the G-115 ruling), replaced by the smallest edit that closes the scenario:
- Node `why` in plan review (the defense, `context: { resume: open }`), spec review (the speccer) and writing (the reviser), each with `output_format { reason }`: replaced by one fresh read-only `analyst` (`context: fresh`, `allowed_tools: []`, `analyst.mcp.json`) that writes `<slug>.idle.K.md`. (The defense fence's `FENCE_DENY` also listed `*.iter.txt`, so the old node's comment "the fence's reads include the iteration file" was unsafe.)
- `docket` field `idle: bool` with `idle` folded into case `guard` (plan review, spec review) and into `stalled` (writing): replaced by case `idle` of its own, fields `idle` (int, K) and `reason` (bool, idle file still absent), the way `summary` works. The second `docket` call no longer takes `INPUTS_REASON`; the idle file is the channel.
- Text in RULINGS.md G-115 row and authority paragraph, CONTEXT.md D-75, REVIEW-pass3.md section 9 ("the loop's author role analyze the reason ..."): rewritten to the owner's answers "Fresh analyst everywhere" and "Pause and ask", source "owner".
- `IDLE = 5` was already gone (the stopped executor had set `IDLE = 1`); kept at 1 in every profile.
- The base-branch/`origin/HEAD` clauses the stopped executor had left (it removed only `gauntlet-design.md:64-66`'s base-branch clause): deleted at `worktree-cut-design.md` ("Base branch" bullet, "Remote" bullet, `baseBranch` comment), `gauntlet-design.md` Homes row "The run-start checks", `contracts.md` H1 and P11.

Edits made this dispatch
- G-115: plan review (Terms "Idle iteration", Files row `<slug>.idle.K.md`, ledger docket, node `why`, `docket` binding, fixture, role `analyst.md`, fence `analyst.mcp.json`, Order step 3), spec review (same; `.shared/rounds.py` `IDLE`, `Profile`, `docket`, `record`), writing (Files row, `stage.py docket` and `record`, node `why`, fixture, role, fence, Order steps 4 and 7), `gauntlet-design.md` (the three fence lists name `plan-review/analyst.mcp.json` and `spec-review/analyst.mcp.json`; the count 3 became 4), `contracts.md` H28, P20, new rows F13 (analyst fences) and R14 (analyst roles). In writing, the reply to case `idle` is written as `<slug>.ruling.N.txt` as for `stalled` and `cap` (writing has no guard files); K is one above the highest move and no idle file counts as a move, so the second `docket` call still sees the iteration as idle. In plan and spec review K is one above the guard-record count, so a resumed iteration starts no second analyst.
- G-111 amended per `docs/reference/archon/cli.md:438-455` (no experiment run): D-72, RULINGS.md G-111 row, designs and contracts as listed above.
- RULINGS.md: new section "D-79 review of the pass-3 drafts" (clean groups, medium fixes, G-118 check: no repository on this host runs commitlint or a `commit-msg` body line limit, nothing changed).

D-63 grep (each changed fact, `grep -n` over `docs/superpowers/specs/*.md`, after the edits): 0 hits for `INPUTS_REASON`, `reason: { from`, `IDLE = 5`, `"idle": bool`, "defense says why"/"speccer says why"/"reviser says why", "the defense analyze", "no agent turn", "5 iterations". `origin/HEAD` and "base branch": only contracts H1, H16 (merge-base), P11, S14 (merge-base), each stating the fix or old history. `baseBranch`: contracts H1/P11, `worktree-cut-design.md` branch-reuse bullet and the config example. `node why`/`.idle.`/`reason`/`case idle`: every hit is a line of this dispatch.

Gates
- Fence suite: `71 passed`.
- Pre-commit: `filepawl check....Passed` (before and at commit).
- `archon workflow list --json`: `"errors": []`. `archon validate workflows`: `Results: 4 valid, 23 with errors` (the baseline).
- Lease-check: `ok:true`, 14 declared. Commit 8c5ecc6; no deleted file.

Checkpoint need
- Round 3 is applied and committed. Task 3 continues with the round-4 review under D-65: the orchestrator dispatches `cad-reviewer` at opus per design (round-3 application diff `060107b..8c5ecc6` plus a full read hunting high and medium defects only, under D-60), and the main session takes the result. Not done here: the spiker validation of the designed YAML (D-64), an orchestrator dispatch.

Deviations:
- [deviation] PLAN-3 Must-be-true 1 and Task 3 say load-bearing groups are "ruled on by `/cad-decision-review`" and each round's rulings land in one commit at once; D-79 (60247c2) replaces both for round 3: the owner rules every group; the drafts stayed uncommitted until the closed review's fixes. Followed D-79.
- [deviation] D-03 amended by D-64 (carried): the spiker validation of the designs' YAML is an orchestrator dispatch after apply, not run here.
- The earlier report's deviation on G-115 "in every profile" (writing's revision profile has no counter) is closed by the owner's ruling: IDLE = 1 in writing too, from writing's own `<slug>.iter.txt` lines.
- Carried unchanged: D-60 exit bar and AC3 reading, D-13 amendment, G-42, G-27 (see `reports/plan-3.7.md`).

Open items:
- Outside D-79 (per the instruction, here only): if `mend-code` commits and its node then fails before the mend is recorded, the resumed run lets an unreviewed commit through.
- Declined shape: a resumed hearing with an unanswered `guard`, `idle` or `cap` ask is not made `owed` `owner` (only review-born cases are), so one defense or speccer turn can run before that ask comes again.
- Declined shape: the menders get no rule for the commit tool's "nothing" answer.
- New role files `analyst.md` and fences `analyst.mcp.json` (three each) are designed, not built; their builds sit in the Order steps named above.
- Tooling disclosed (CLAUDE.md 1.1): this dispatch used the Edit tool throughout; two shell edits: one `sed -i` that I mis-aimed at `plan-review-design.md` line 151 (restored by Edit in the same session) and one `cat >>` heredoc append of the RULINGS.md section. No pack file holds new code.
- Carried: `/tmp/tmp.xTDZRgjxE3` and `/tmp/tmp.M5j1ysgIxi` scratch dirs left alone; the D-58 juror-route fixture and `juror.md` sentence; `gauntlet-design.md` not naming `bash run.sh`; ROADMAP/PROJECT Phase 2 lines, LAND-01, RUN-14 not edited; Task 4 flags for A10 and A19.
- Left uncommitted, not mine: `.gitignore`, `.planning/STATE.md`, `.planning/config.json`, `.planning/phases/1/reports/`, `reviews/pass2-*`.
- Previous report rotated to `reports/plan-3.8.md`.
- Process: no process left running (foreground `uv run pytest`, `archon`, `pre-commit` and `git` only, each exited). Full suite not run: the plan is not at its last task.
