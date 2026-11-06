# Phase 1 review, pass 2 (convergence pass over the designs as committed at e01ea0b)

Date: 2026-11-05
Plan: `.planning/phases/1/PLAN-3.md`, Task 3 (new-finding branch)
Reviewed: the seven designs under `docs/superpowers/specs/` as committed at `e01ea0b` (the pass-1 rulings in `e9d81de` and G-45 in `e01ea0b`) against `docs/superpowers/specs/contracts.md`, with the pass-1 groups G-01 to G-50 and their rulings (`REVIEW-pass1.md`, `RULINGS.md`) as the ruled set.

Ids: findings are `2.NN` (pass 2); groups are `G-NN`, numbered on from G-50 of pass 1. A finding cites `<design>.md:<line>`, the text it is about and a `contracts.md` row id, or names the contract a missing row would hold. Mark per finding: `new`, or `matches G-NN` as the reviewer marked it; a `matches` finding whose ruled value is applied and whose defect still stands sits in a new group that cites the earlier group.

Sources: (1) seven `cad-reviewer-medium` (opus) dispatches, saved unchanged as `.planning/phases/1/reviews/conv-<design>.md`: 68 findings, 51 marked new and 17 marked as matching a ruled group (the writing return's header said 13 findings; it holds 14); (2) the graph check by the executor, `.planning/phases/1/reviews/convergence-graph.md` (one finding, 2.69).

Check of anchors: every anchor was read with `sed -n` against the working tree, which equals `e01ea0b` for the seven designs and `contracts.md` (`git status` shows none of them modified). All 68 reviewer findings hold the quoted text at the anchor given. Where a quote wraps over lines the anchor names both lines. None dropped: no quoted text is absent, and no defect is already resolved by a design line (each was checked against the lines the group lists). The reviewers dropped items themselves: `conv-gauntlet-intake.md` lists four (Homes rows `:281`, `:288`; "failing on any name conflict" `:152`; `fence/spike.py` as a second file server; launch lines `:113`; guard messages `:60-62`), kept there. `conv-gauntlet.md` carries one reviewer note, not a finding: `RULINGS.md` G-10 says `--allow-empty` where the D-19 amendment in `DECISION-REVIEW.md` replaced it with (b); `gauntlet-design.md:290` and `:403` apply the amendment.

Missing contracts (rows to add under D-01 with the ruling that touches them, in the ruling commit, not in this record's commit): the `put`/`put-open` refusal hand-off to Clerk (G-73); the grammar of the defense's `[cite: ...]` marker (G-59); the command form of `fence/spike.py` (G-62); the log and diff the mend's juror and reviewer read (G-98); the one stall count writing and landing copy (G-95); agent sessions started per round (G-58).

## 1. gauntlet-design.md

Source: `reviews/conv-gauntlet.md` (10 findings: 9 new, 1 matching a ruled group). 10 of 10 anchors hold.

**2.01** `gauntlet-design.md:120`, rows H24, P20, H29. New, high. Group G-51.
Text: "aside into the folder gauntlet/failed/$pin.output.slug.approved/, so a rerun on the slug re-hears them".
Finding: `fail` moves only the slug's `approved/` files. The round, review and ruling files stay, so `state` returns `owed: ended` from the old approve ruling (`plan-review-design.md:110`), and `close`/`enter` re-approve the defective plan unheard after two paid sessions. Same for spec review. The file route reruns the same slug (`gauntlet-intake-design.md:180`).

**2.02** `gauntlet-design.md:117-118`, row H24. New, medium. Group G-52.
Text: "target present: exit non-zero naming it, nothing copied".
Finding: a second DEFECTIVE verdict on one slug cannot be recorded: `gauntlet/failed/<slug>.txt` and `<slug>.approved/` exist, `fail` exits non-zero, the run fails instead of cancelling at `kill`, and every resume fails, against the Homes row at `:400` ("a node failing the run for it"). Reachable because `kill`'s message (`:124`) invites a rerun and 2.01 sends the same plan back.

**2.03** `gauntlet-design.md:106`, rows H23, H39. New, medium. Group G-68.
Text: "id: land-3 ... # round 3, the last: a move found here stops the run".
Finding: a move during `land-3`'s gate wait makes `merge` print `moved` and exit 0; `land-3` hands off `moved`, no node follows, the run completes unlanded with a false "the next round checks it and asks again", against `:17`.

**2.04** `gauntlet-design.md:17`, row H39 (G-45). New, medium. Group G-69.
Text: "It re-mends at most twice, each round an `include` of `land` under its own id ... and a third move stops the run".
Finding: the budget counts rounds, not re-mends: a gate-wait move uses a round without a re-mend, so the run can stop after one re-mend and two moves with the message "for the third time, after landing re-mended twice".

**2.05** `gauntlet-design.md:390`, rows A1, H13-H15. Matches G-12, medium. Group G-65 (cites G-12).
Text: "Run-owned settings (`worktree`, `container`, `budget`, `evidence_policy`) | `gauntlet-run.yaml`; `gauntlet-tree.yaml` for the tree run | any of them in a phase file".
Finding: G-12 is applied at `:24` and `:154` (`worktree: { enabled: false }` in intake, plan-review, spec-review), but this Homes row still forbids the key in a phase file.

**2.06** `gauntlet-design.md:193`, rows H19, H18. New, low. Group G-66.
Text: "depends_on: [copy-in, baseline]" (node `paths`).
Finding: `:192` and `:186` call it the cut design's hand-off, whose `depends_on` is `[copy-in, baseline, settings]` (`worktree-cut-design.md:189`). `write` can start, and run on after a failed `settings`, before `gauntlet/settings.json` exists (P19).

**2.07** `gauntlet-design.md:398`, row H40. New, low. Group G-67.
Text: "`copy-in` of the re-mend run for the whole of the previous tree's `gauntlet/`".
Finding: the first tree's `gauntlet/mend/*.verdict.*` and `.reply.*` reach the second tree; `pose`'s stall count (`landing-design.md:178`) includes them, so the re-mend can ask after its first verdict (CLAUDE.md 1.4).

**2.08** `gauntlet-design.md:286`, row P3. New, low. Group G-70.
Text: "`gauntlet/plans/approved/<slug>.rev<N>.txt` and `gauntlet/specs/approved/<slug>.rev<N>.txt`, in the tree only."
Finding: landing's `record` copies them into the checkout (`landing-design.md:298-301`), allowed by Homes `:398`, so "in the tree only" and `enter` as "the only writer of approved revisions" (`:269`) are false.

**2.09** `gauntlet-design.md:7`, rows H39, H40 (also Homes `:388`). New, low (G-45 leftover). Group G-71.
Text: "No phase goes back to an earlier phase."
Finding: landing (phase 7) starts `gauntlet-remend`, which runs block `mend` (phase 6) again. Homes `:388` forbids "any node or phase sending the run back to an earlier phase".

**2.10** `contracts.md:21`, row H5. New, low. Group G-64.
Text: "`gauntlet-design.md:26` states plan review's and spec review's `handoff` declare no `output_format`".
Finding: `gauntlet-design.md:26` now reads "3 `handoff` nodes, each declaring an `output_format` that names every field it prints" (`:156-159` agrees); the row records the reversed value, which its "Citation age" note (`contracts.md:9`) does not cover, because that note covers line numbers only.

## 2. gauntlet-intake-design.md

Source: `reviews/conv-gauntlet-intake.md` (8 findings: 6 new, 2 matching ruled groups). 8 of 8 anchors hold.

**2.11** `gauntlet-intake-design.md:212`, row A15 (G-26 form). New, high. Group G-72.
Text: "task=$put.output.task".
Finding: the `talk` group's `until_bash` reads `put`, which iteration 1 always skips (it depends on `turn`, whose `when:` skips it). `loop-nodes.md:930` "explicitly skipped nodes have no output"; `:696-697` reading a wait its own `when:` can skip "fails the group". The owner's first answer, the approve route included, can fail the group. G-26 covered plan review and spec review only.

**2.12** `gauntlet-intake-design.md:221`, missing row (the `put`/`put-open` refusal hand-off to Clerk that the G-16 amendment requires). New, medium. Group G-73.
Text: "the refusal $LOOP_PREV.put.output.refusal".
Finding: in iteration 2 `$LOOP_PREV.put` is iteration 1's skipped `put`, so a `put-open` refusal never reaches Clerk, against `:263` ("the refusal reaches Clerk's next turn"): one more refused turn and owner answer. `show` (`:235`, "the refusal (put's, else put-open's)") keeps showing the stale opening refusal on later turns where `put` succeeds with refusal "".

**2.13** `gauntlet-intake-design.md:138`, contract `put`'s `output_format` (`:204`, `:230`). New, high. Group G-74.
Text: "draft \"\" or slug \"\": writes nothing."
Finding: the branch states no stdout, while `put-open` and `put` require `{ slug, task, refusal }`. In the common opening case (first reply asks questions, draft ""), `put-open` fails its `output_format` and the Clerk route stops before the owner sees the first reply, unless `put` prints `{ slug: "", task: "", refusal: "" }`.

**2.14** `gauntlet-intake-design.md:257`, row H3. New, medium. Group G-75.
Text: "task = file || the absolute path of gauntlet/tasks/<slug>.md for the slug whose marker owned.<slug> sits in $ARTIFACTS_DIR".
Finding: only the prompt rule at `:96` keeps the slug unchanged after the first write; `put.ts` (`:139-142`) writes any free slug and touches its marker. A changed slug leaves two markers, `handoff` has no rule to choose, and the other `gauntlet/tasks/` file stays as a slug later runs see as taken.

**2.15** `gauntlet-intake-design.md:96`, internal to intake (CLAUDE.md 1.3). New, low. Group G-76.
Text: "outputs the whole current draft once it holds enough to draft, and again every turn after".
Finding: Clerk re-emits the whole task file every turn, unchanged or not, only because `put`, `show` and `until_bash` treat draft "" as no task file.

**2.16** `gauntlet-intake-design.md:9`, internal to intake (cross-design wording). New, low. Group G-77.
Text: "Script nodes run on Bun."
Finding: stated for the whole pack, but the other designs run Python script nodes on `uv` (`.shared/rounds.py`, ledgers, `pin.py`, `stage.py`, `verify.py`, `cite.py`; `runtime: uv` in plan-review, spec-review, writing, landing and worktree-cut).

**2.17** `gauntlet-intake-design.md:110-118`, rows A12, P6, F5. Matches G-16, low. Group G-64 (cites G-16).
Text: `"env": { "FENCE_READ": "." }` with no `FENCE_WRITE`.
Finding: `contracts.md` A12 still quotes `"FENCE_WRITE": "gauntlet/tasks"` and P6's Writer cell says "Clerk writes it" (`:86`, `:90`, `:94` of the 0d08176 design); only F5 was updated for the amended G-16.

**2.18** `gauntlet-intake-design.md:195`, row A26. Matches G-19, low. Group G-64 (cites G-19).
Text: `pattern: "^([a-z0-9]+(-[a-z0-9]+)*)?$"`.
Finding: `contracts.md` A26 still quotes `"^[a-z0-9]+(-[a-z0-9]+)*$"`, which forbids the empty slug G-19 needs.

## 3. plan-review-design.md

Source: `reviews/conv-plan-review.md` (7 findings, all new). 7 of 7 anchors hold.

**2.19** `plan-review-design.md:136`, rows H28, H29. New, high. Group G-54.
Text: "# Every case is read only from a review written in this iteration; an iteration with no new review is \"none\"."
Finding: the guard case `repairs >= REPAIRS` (`:133`, `:25`) can never fire: `repairs` counts cite lines for rounds above the latest tried round, so it is non-zero only in repair-only iterations, which write no review, so `:136` forces `none`. A marker that never resolves loops the Opus defense up to 200 times and ends on `max_iterations`, against `:26` and `:286`; the fixture "five repair-only iterations asking" (`:418`) cannot pass. Even if it fired, docket's `round` (`:131`) names an earlier round, so `record` writes a ruling for it or exits 1. This cancels the G-04 amendment "the owner is asked after 5".

**2.20** `plan-review-design.md:102`, rows A15, H28. New, medium. Group G-55.
Text: "CAP = 200       # the hearing's max_iterations; from this many run rounds every round calls the owner".
Finding: `cap` counts tried rounds, `max_iterations: 200` counts iterations; with k >= 1 repair-only iterations, iteration 200 arrives at run_rounds = 200 - k, the cap ask never fires and the run fails on `max_iterations`, against `:26` and `:286`. The defect G-38 ruled for writing, left in plan review.

**2.21** `plan-review-design.md:416`, rows P20, H29, H24. New, high. Group G-51.
Text: "A task changed since, or a slug whose run ended defective (`fail` moves the approved plan aside), is heard afresh."
Finding: the old `approve` ruling stays in `gauntlet/plans/`, so `state` reports `owed: ended` (`:110`) whenever `owed: approved` fails. (1) After `fail`: two Opus opening sessions, then `close` returns the old approved round and `enter` copies the DEFECTIVE plan back into `approved/` unheard. (2) Edited task: the same two sessions, then `enter`'s `cp -n` hits the existing `approved/<slug>.txt` and the run fails. The G-25 amendment "a rerun re-hears them" is not delivered.

**2.22** `plan-review-design.md:270`, row A19. New, medium. Group G-57.
Text: "allowed_tools: [Agent]             # no Bash: node `cite` runs cite.py".
Finding: node `open` holds `Agent` but declares no `agents:`; only `defend` declares `detective` (`:316-320`), yet defense.md's "Detectives: dispatch through Agent to `detective`" (`:176`) applies to the opening turn, told to "read the task file and the code it touches" (`:159`). The call fails (a wasted turn) or reaches an unfenced sub-agent. Spec review's `open` takes `allowed_tools: []` (`spec-review-design.md:358`).

**2.23** `plan-review-design.md:19`, missing row (agent sessions); A13. New, low. Group G-58.
Text: "No agent node starts a session per round but `screen`."
Finding: `report` is `context: fresh` per APPROVED round (`:367-374`), named at `:336` ("besides report") and in the Homes row `:427` ("`report` excepted"): two rules for one node.

**2.24** `contracts.md:89`, row F1 against `plan-review-design.md:229`. New, low. Group G-64.
Text: row F1 holds `gauntlet/plans/*.review.*.txt:gauntlet/plans/*.ruling.*.txt` as the defense's `FENCE_DENY`.
Finding: G-20 added `gauntlet/plans/*.cite.*.txt` to the defense's `FENCE_DENY`; F1 still holds the 0d08176 value. A fence built from F1 leaves the cite files writable, so the defense could truncate them and break the repair count (`:119`).

**2.25** `plan-review-design.md:69`, missing row (cite.py in one design; P20). New, low. Group G-59.
Text: "# Marker the defense writes: [cite: <path> | <quote>]".
Finding: the grammar does not say how a quote holds `]` or `|` (`items[0]`, `a | b`), nor does defense.md (`:171`). Such a marker fails as "quote not found" or "no such file" with no reason given, costing a repair-only Opus iteration each (CLAUDE.md 1.3).

## 4. spec-review-design.md

Source: `reviews/conv-spec-review.md` (9 findings: 5 new, 4 matching ruled groups). 9 of 9 anchors hold.

**2.26** `spec-review-design.md:279`, rows F4, F12. Matches G-03, high. Group G-60 (cites G-03).
Text: "`speccer.mcp.json` names three: `fence-files` for the speccer, and for its spikers `fence-scratch` (`fence/files.py`) and `fence-spike` (`fence/spike.py`)."
Finding: `open` and `file` both take `mcp: speccer.mcp.json`; Archon adds `mcp__<server>__*` for every declared server to a Claude node's `allowed_tools` (`mcp-servers.md:241-245`), so the speccer itself gets `fence-scratch` and `fence-spike`'s `run_command`, against `:53`, `:253`, Homes `:520` and the G-03 amendment.

**2.27** `spec-review-design.md:294`, rows F12, P14, P15, copy-list B09 (`gauntlet-design.md:31`). Matches G-03, high. Group G-61 (cites G-03).
Text: "# folder: a path inside gauntlet/scratch of the root, else PermissionError. Runs".
Finding: `run_command` checks only its working folder, then runs `bash -c <command>` unconfined, so `:279`, `:302`, `gauntlet-design.md:31` and `:381` are false, as is the G-03 premise "no Bash read is left open". A spiker can `cat ../../failed/x.txt` and `sed -i` source in the owner's live checkout; the Homes ban at `:520` rests on the prompt alone.

**2.28** `spec-review-design.md:103`, rows P2, P20, H24. Matches G-25, high. Group G-51 (cites G-25).
Text: "owed \"ended\": the latest ruling's decision is an OwnerCase \"ends\"; the loop ends one iteration after it".
Finding: `ended` ignores the approved file and task hash: after `fail` moves the approved spec aside, a rerun runs `open`, `swear-in`, one script-only iteration, and `enter`'s `cp -n` copies the DEFECTIVE spec back as approved, against `gauntlet-design.md:120`.

**2.29** `spec-review-design.md:105`, rows P2, P20. Matches G-25, medium. Group G-51 (cites G-25).
Text: "exists and <folder>/approved/<slug>.task.sha256 equals the sha256 of the task file (INPUTS_TASK), so a rerun on an".
Finding: a hash mismatch falls through to `ended`; after paid Opus turns `enter` hits its `cp -n` refusal and fails the run; the changed task is never re-heard.

**2.30** `spec-review-design.md:355`, row H29. New, medium. Group G-53.
Text: `when: "$docket-in.output.owed != 'approved'"`.
Finding: with `owed` `ended` the hearing is decided, yet `open` and `swear-in` start two Opus sessions reading the whole record (`:225` forces needed=true) (CLAUDE.md 1.3). Plan review has the same pair of `when:` lines (`plan-review-design.md:268`, `:277`).

**2.31** `spec-review-design.md:374`, rows H28, H29. New, medium. Group G-55.
Text: "max_iterations: 200              # rounds.py CAP; from 200 run rounds every round asks, so this never fails the run".
Finding: owner asks count tried rounds; an iteration with no block or no review adds none and `docket` returns `none`, with no REPAIRS-like counter. E.g. the arbiter writes `<slug>-review.N.txt` (the old name, `:13`), FENCE_WRITE refuses, and `screen` plus `arbitrate-k` rerun on round N to iteration 200, failing the run.

**2.32** `spec-review-design.md:102`, rows H38, H28. New, medium. Group G-56.
Text: "\"vacant\" as soon as twelve such reviews exist, whatever the round's state (the cancel needs no repair turn first)."
Finding: the twelfth LEADING review makes stretch = 12, `docket` returns `guard` and `bench` asks; the next iteration's `filing` reports vacant and `vacate` cancels, discarding the reply (CLAUDE.md 1.4). The fixture "all twelve slots retired" (`:506`) passes this ask first.

**2.33** `spec-review-design.md:188`, rows H26, F7. New, low. Group G-63.
Text: "Gauntlet steering check, included by plan-review and spec-review once per round. Not for direct use."
Finding: also `:183` and Homes `:517` omit writing, which includes `screen` (H26, G-23; `writing-design.md:453`; this design's `:12`).

**2.34** `spec-review-design.md:411`, missing row (spike.py command form; P14). New, low. Group G-62.
Text: "a time, which runs it as `timeout -k 10 600 nice -n 10 <command>` in the foreground with the scratch folder".
Finding: restates spike.py mechanics in a node prompt, which Homes `:527` forbids, and wrongly: `:295` runs `timeout -k 10 600 nice -n 10 bash -c <command> < /dev/null`.

## 5. worktree-cut-design.md

Source: `reviews/conv-worktree-cut.md` (9 findings: 8 new, 1 matching a ruled group). 9 of 9 anchors hold.

**2.35** `worktree-cut-design.md:189`, rows H18, H19, P19. New, medium. Group G-66.
Text: "depends_on: [copy-in, baseline, settings]".
Finding: `gauntlet-design.md:193` replaces that node with `paths`, `depends_on: [copy-in, baseline]`, so `settings` drops out of the chain into `write`, `mend` and `handoff` (`gauntlet-design.md:201`, `:207`, `:214`). A failed `settings` still lets `paths`, `write` and `mend` run; every writer's `fence-checks` and `@base` fence finds no `gauntlet/settings.json` and refuses (`writing-design.md:90`), paying agent turns for refusals (CLAUDE.md 1.3).

**2.36** `worktree-cut-design.md:224`, rows H1, P11. Matches G-31 (misapplied), medium. Group G-78 (cites G-31).
Text: "`GAUNTLET_TEST_COMMAND`, `GAUNTLET_TEST_BRIEF_COMMAND`, `GAUNTLET_TEST_TIMEOUT` and `GAUNTLET_TEST_BASE` in the repository's `env:`, refused at run start when blank or malformed (`gauntlet-design.md`)".
Finding: G-31 and the guard (`gauntlet-design.md:139-140`) refuse only a blank test or brief command and a malformed timeout; this design defaults an unset timeout and test base (`:169-170`, `:210`). Built to this row, an unset `GAUNTLET_TEST_BASE` stops the run at start (CLAUDE.md 1.4).

**2.37** `worktree-cut-design.md:217`, rows H36, H16. New, medium. Group G-82.
Text: "| Slug | `gauntlet-run/scripts/pin.py` | any node, prompt or other script deriving it |".
Finding: unscoped, it forbids what G-23 requires: `.shared/rounds.py` deriving the slug from `INPUTS_TASK` (`spec-review-design.md:90`, `plan-review-design.md:92`), plan review's `handoff` and both opening prompts (`plan-review-design.md:272`, `:407`; `spec-review-design.md:360`), intake's `from-file` (`gauntlet-intake-design.md:180`). Line 18 scopes the rule to "this phase"; the Homes row does not.

**2.38** `worktree-cut-design.md:160`, rows H2, S2, S3, H1. New, medium. Group G-80.
Text: "script: guard".
Finding: the tree's guard checks the `.gitignore` committed at `HEAD`; the run-start guard accepts a working-copy-only ignore line, and its message says "Add it to .gitignore and restart the run" (`gauntlet-intake-design.md:60`) with no commit required, as G-31 requires for `.archon/config.yaml`. Intake, plan review and spec review are paid for, then `gauntlet-tree`'s `guard` fails, and a resume reuses the same tree and fails again.

**2.39** `worktree-cut-design.md:186`, rows P11, H20, H1. New, medium. Group G-81.
Text: "The run-start guard has refused a blank command, so none is recorded as \"no test command\"" (the quote wraps from `:185`).
Finding: the guard refuses only an `.archon/config.yaml` with uncommitted changes, which `git status` does not report for an ignored file, and `:35` leaves open whether an ignored or uncommitted config's `env:` reaches the tree run. If not, `baseline` runs `bash -c ""` (exit 0) and `settings` writes an empty `brief`: no red can fire and untested code reaches the land gate.

**2.40** `worktree-cut-design.md:208`, row P11. New, low. Group G-78.
Text: "env:\n  GAUNTLET_TEST_COMMAND: ...\n  GAUNTLET_TEST_TIMEOUT: ...".
Finding: `:201` says the block declares "everything the tree needs" and `:15` points to it, but it omits `GAUNTLET_TEST_BRIEF_COMMAND`, which `baseline`, `settings` and the guard need (named only at `writing-design.md:524-525`). A config copied from the block is refused at every run start.

**2.41** `worktree-cut-design.md:66`, rows S14, H16, H17. New, low. Group G-83.
Text: "branch present: left as it is, base = git merge-base <source, or HEAD for \"\"> <branch>. Always a full hash."
Finding: no design reads `base` (`$pin`, `$repin`, `$cut`), nor the cut hand-off's `task`, `plan` and `spec` (`:130-132`, `:191`); `land`, `fail` and `kill` read only `slug`, `worktree`, `branch`, `line`, `summary`, `outcome`, `verdict`. The merge-base branch and its test (`:69`) are unneeded work, as G-32 removed for `uncommitted` (CLAUDE.md 1.3).

**2.42** `worktree-cut-design.md:21`, rows H39, H40, S15. New, low. Group G-84.
Text: "the re-mend run works in a second tree, cut on a new branch pinned at the first tree's tip, never in the first."
Finding: round `land-2` pins at the tip of `$land.output.branch`, the second tree's branch (`landing-design.md:342`, `gauntlet-design.md:103-104`). Lines 21 and 42 ("holds a copy of the first tree's `gauntlet/`") misstate the second re-mend; built to them, the first re-mend's rebase, mend commits and `gauntlet/mend/` records are dropped.

**2.43** `worktree-cut-design.md:220`, rows H9, H40. New, low. Group G-85.
Text: "any other `git branch` in a Gauntlet file".
Finding: `branch-check` (`:164`), `handoff` (`:192`) and `gauntlet-remend`'s `branch-check` and `handoff` run `git branch --show-current`; `:223` forbids "any install, copy or setup command in a Gauntlet file" while `copy-in` runs `cp -n`. A literal Homes check flags them (CLAUDE.md 1.4).

## 6. writing-design.md

Source: `reviews/conv-writing.md` (14 findings: 8 new, 6 matching ruled groups). 14 of 14 anchors hold.

**2.44** `writing-design.md:122`, rows H1, A11, P19. Matches G-31, high. Group G-79 (cites G-31).
Text: "GAUNTLET_TEST_COMMAND or GAUNTLET_TEST_BRIEF_COMMAND blank: every mode exits 1 naming it."
Finding: `stage.py` is a script node; `:22` says the repository `env:` reaches bash nodes only (unmeasured for a script node per `gauntlet-design.md`'s guard module), so this repeat can fail every mode with the variables set; the gauntlet Homes row "The run-start checks" forbids it outside `gauntlet-run`'s guard.

**2.45** `writing-design.md:159`, row P19. New, medium. Group G-79.
Text: "a tests block path outside tests/ and GAUNTLET_TEST_BASE".
Finding: `stage.py cut` reads the test base from the environment a script node may not see; every other reader (`@base`, `:86-87`) takes `settings.json` "base". Absent, every test-base path is a cut problem and the divvy repeats until `stalled` (CLAUDE.md 1.4).

**2.46** `writing-design.md:528`, rows P11, P19 (also `worktree-cut-design.md:169`, `:224`; `gauntlet-design.md:139`). New, medium. Group G-78.
Text: "Writing needs `GAUNTLET_TEST_COMMAND` and `GAUNTLET_TEST_BRIEF_COMMAND` to be set".
Finding: since G-29 dropped the full baseline nothing reads `GAUNTLET_TEST_COMMAND` or `settings.json` "test"; `:542` forbids a writer reaching it. A blank value is refused at run start though unused (CLAUDE.md 1.4).

**2.47** `writing-design.md:73`, near rows F8, F9 (`FENCE_COMMIT`). Matches G-41, medium. Group G-86 (cites G-41).
Text: "Returns \"exit=<n>\", then git's and the hooks' output cut as checks.py cuts it".
Finding: contradicts `:72` ("the names of the hooks that failed and never their output") and the Homes row at `:541`; a leftover of the G-41 amendment.

**2.48** `writing-design.md:217`, row R7. New, medium. Group G-87.
Text: "A failed commit is ruled like any red, on the file that fails the hook."
Finding: under `:72` `commit-failed` grounds hold hook names only (`:290`, `:164`) and no file stores hook output; the juror cannot find the failing file nor re-run hooks (CLAUDE.md 1.3).

**2.49** `writing-design.md:131`, row S5. Matches G-37, medium. Group G-88 (cites G-37).
Text: "tests and code: the first unrun wave of the latest cut, then the unrun waves carried from the cuts it replaced".
Finding: `:160` already puts "a step of an uncommitted earlier block" into a code cut, so carried code steps run twice (1.3); a concatenated `wave` breaks "blocks of one wave share no path" and "one kind per fan-out"; carried blocks get the new cause's ruling (`:132`).

**2.50** `writing-design.md:448`, row R12. Matches G-43, high. Group G-89 (cites G-43).
Text: "prompt: <round $state.output.round; kind $state.output.kind; plan files; spec files>".
Finding: G-43 made `state` print `cause` for `revise` (`:137`) but the prompt never passes it; round 1 has no earlier round file, so the reviser cannot write its required `Answers: <path>` line (`:225`).

**2.51** `writing-design.md:362`, row S5. Matches G-42, low. Group G-90 (cites G-42).
Text: "move: $LOOP_PREV.state.output.move".
Finding: a stall arises in an iteration that just made move M, so `record` writes `ruling.M` beside `verdict.M`, breaking "one counter over every kind" (`:29`) and blurring "since the latest writing ruling" (`:173`); a tie counting verdict M after the ruling re-fires the stall right after the owner's reply. (The text is the executor's deviation from G-42's ruling `$state.output.move`, recorded in the plan-3 report.)

**2.52** `writing-design.md:355`, row S7. Matches G-38, low. Group G-55 (cites G-38).
Text: "rounds.py CAP; from 200 moves every iteration asks".
Finding: G-38 ruled `cap` counts iterations (`:174` does); the comment still says moves.

**2.53** `writing-design.md:228`, rows R12, R3. New, medium. Group G-91.
Text: "A spec revision holds no source text, as speccer.md rules a spec block."
Finding: `speccer.md` lives in `spec-review/commands/`, unreadable through the reviser's tree-rooted fence, and `gauntlet-design.md`'s Homes row (`:413`) forbids a `write/` role relying on a `spec-review/` role file.

**2.54** `writing-design.md:373`, row H8. New, medium. Group G-92.
Text: "trigger_rule: all_done".
Finding: `enter` exits non-zero when the target is present, yet `state` runs, treats the round as closed (the approve ruling exists) and divvies against files lacking the revision: a failed `enter` silently drops an approved revision.

**2.55** `writing-design.md:399`, row A9 (`workflow-language.md:2613-2614`). New, medium. Group G-93.
Text: "fan_out: { items: $state.output.wave, as: block, max_parallel: 2 }".
Finding: instances share one checkout, so two writers edit one tree; paths are coordinated only. Each `fence-checks` runs the suite over the other's half-done files (a contest over a test that is not wrong, 1.4); each `commit`'s pre-commit stashes the other writer's unstaged edits and can fail on restore, a spurious `commit-failed` and juror dispatch. The flock (`:69-70`) serialises commits only.

**2.56** `writing-design.md:13`, rows P14, P19. New, low. Group G-94.
Text: "writing reuses `checks.py` unchanged."
Finding: `:78-90` and Order step 1 change `checks.py` (`settings.json` replaces `FENCE_TEST_COMMAND` and `FENCE_TEST_TIMEOUT`).

**2.57** `writing-design.md:173`, missing row (the stall count landing copies). New, low. Group G-95.
Text: "stalled (verdicts and rejected cuts since the latest writing ruling >= 5)".
Finding: `landing-design.md:22` says "5 verdicts since the latest owner ruling", dropping rejected cuts: two stall rules for one copy.

## 7. landing-design.md

Source: `reviews/conv-landing.md` (11 findings: 8 new, 3 matching ruled groups). 11 of 11 anchors hold; wrapped quotes at `:288-289`, `:243-244`, `:176-178` name both lines.

**2.58** `landing-design.md:288-289`, rows H39, H23. New, high. Group G-68.
Text: "The checkout moved from <onto> to <now> while landing waited; the next round checks it and asks again."
Finding: `land-3` has no next round: a move during its gate wait makes `merge` print `moved` and exit 0, `record` and `remove` skip, and `gauntlet-run` has no node after `land-3` (`gauntlet-design.md:106-112`, `:19`), so the run completes unlanded with no stop naming the move, against G-45. No land fixture (`:331`) covers it.

**2.59** `landing-design.md:243-244`, row H39. New (G-45 bound misapplied), medium. Group G-69 (cites G-45).
Text: "The checkout moved to <head> for the third time, after landing re-mended twice".
Finding: the stop counts rounds, not moves: move 1 during `land`'s gate wait, re-mend 1 in `land-2`, move 2 during its gate wait, and `land-3` (remend `no`) fails on the second move after one re-mend, with a false message.

**2.60** `landing-design.md:55-56`, row H22. Matches G-44, high. Group G-96 (cites G-44).
Text: "A rebase that changed the branch: write gauntlet/mend/$INPUTS.slug.rebased.<head> by cp -n semantics."
Finding: on a conflict `rebase` exits 1 before writing the marker (`:57-58`); after a hand `git rebase --continue` and resume, `onto` sees no move and no marker, skips `test-tree`, `red`, `confirm`, `repair`, and `handoff` prints "Checkout not moved past the tree's base: not rerun." (`:202`). An untested rebase reaches the gate.

**2.61** `landing-design.md:119`, row H34 (also `:169`, role inputs `:413`, `:449`); missing producer row. New, high. Group G-98.
Text: "git log and diff of $onto.output.head..$INPUTS.branch;".
Finding: no `mend` node produces that log and diff, and juror and reviewer hold `allowed_tools: []` and fence-files only (no git tool: `fence/files.py`). `mend-review` rules on a mend it cannot see.

**2.62** `landing-design.md:176-178`, row H34. Matches G-50, medium. Group G-99 (cites G-50).
Text: "A retry whose rerun is not red, with no uncommitted mend (git status --porcelain empty, gauntlet/ excluded): end \"done\"."
Finding: ends the repair with a committed mend no review read, against `:160` and Homes `:498`. Iteration 1 CODE mend commits, recheck red, review skipped; iteration 2 DEFECTIVE, owner `retry`; iteration 3 green: "done", unreviewed mend lands.

**2.63** `landing-design.md:378`, rows H40, H31. New, medium. Group G-67.
Text: "Every file under it, gauntlet/settings.json included, to the same path under this tree".
Finding: the re-mend inherits the first mend's verdict, review and reply files; `hear`'s n and `pose`'s stall count (`:181`) count them, so after 4 earlier verdicts the re-mend's first verdict asks the owner (CLAUDE.md 1.4), and the juror prompt (`:118-119`) is fed superseded verdicts (1.3).

**2.64** `landing-design.md:290-291`, row H39. New, medium. Group G-100.
Text: "Stash or commit those edits, then archon workflow resume <run id>."
Finding: committing moves HEAD; on resume only `onto` reruns while `repin`, `retree`, `cur`, `gate` replay (`:220`, `:329`), so `merge --ff-only` fails on every resume with the same advice; in `land-3` `onto` fails on the owner's own commit. `merge` also reads any ff-only refusal as uncommitted edits.

**2.65** `landing-design.md:240-241`, rows H37, H39. New, low. Group G-101.
Text: "tip = git -C $INPUTS.worktree rev-parse $INPUTS.branch, \"\" when the branch is absent".
Finding: `remove` deletes the INPUTS tree (in `made`) before the landed one; if the final `archon complete` fails (e.g. A23 ownership), a resume's `onto` runs `git -C` on a deleted folder ("fatal: cannot change to"), an outcome the design does not give, so every resume fails.

**2.66** `landing-design.md:9`, rows H31, A21 (also `:22`). New, low. Group G-102.
Text: "The owner is asked on the tree run's id, in plain words and with no diff".
Finding: in a re-mend the ask is on the re-mend run's id (`:31`, `:353`; `gauntlet-design.md:7`, `:129`, `:395`).

**2.67** `landing-design.md:343-344`, rows S14, S15. New, low. Group G-83.
Text: "created at the tip of INPUTS_BRANCH (left as it is when present); base the full hash of that tip".
Finding: for a present branch `worktree-cut-design.md:65-66` gives base = `git merge-base <source> <branch>`; `.shared/pin.py` and `test_pin.py` (`:349`) disagree.

**2.68** `landing-design.md:495`, row H22. Matches G-44, low. Group G-97 (cites G-44).
Text: "a test run when the checkout's `HEAD` is in the branch's history".
Finding: the Homes row forbids it, but the G-44 marker rule (`:48-49`) runs `test-tree` exactly then after a first-pass rebase.

## 8. Build orders (graph check)

Source: `reviews/convergence-graph.md` (40 steps, no cycle, no in-design forward reference, every file built; section A re-check of A1, A5, A10, A11, A12, A15, A19, A29). One finding.

**2.69** `landing-design.md:514`, row H39 (build order, `landing:6`). New, low. Group G-103.
Text: "`gauntlet-design.md`'s step 11 needs step 6."
Finding: `gauntlet-design.md` has 10 steps; its landing step is 10. Stale since G-10's step drop (`e9d81de`); the sentence read "step 11 needs step 4" at `0d08176`, and G-45's edit changed "4" to "6" for the renumbered landing steps and left "11".

## 9. Groups

Each group is one disagreement. "Members" lists the findings it holds, "Where" every design line where it occurs, "Statement" the disagreement in plain words with a scenario, "Options" each value, cited. Option (a) is the designs' current text unless it says otherwise; an option that cites no design line is a proposal from the finding or from this record, offered for the ruling to accept or replace, and is not a value any design gives. "Route": load-bearing (a D-NN line in CONTEXT.md from D-38, reviewed by `/cad-decision-review`) when the ruling changes a `contracts.md` row a later phase builds against (hand-off field, node id, path, fence value, script or role resolution, feature verdict) or contradicts a PROJECT, ROADMAP or REQUIREMENTS line; the ask-user seam otherwise. The 2.NN ids in this record appear in exactly one group each (checked by grep: 69 of 69).

**G-51** A rerun on a slug after `fail`, or after the task changed (rows P1, P2, P20, H24, H29; cites G-25).
Members: 2.01, 2.21, 2.28, 2.29.
Where: `gauntlet-design.md:118-120`; `plan-review-design.md:110`, `:416`; `spec-review-design.md:103`, `:105`; `gauntlet-intake-design.md:180`.
Statement: `fail` sets aside only the slug's `approved/` files. The old round, review and ruling files stay, so the ledger still sees the old approve ruling and answers `ended`. Scenario: the juror rules plan P defective; `fail` moves `approved/P.txt` aside; the owner starts a new run on the same slug; plan review runs two paid Opus opening sessions, finds `ended`, and `enter` copies the defective plan P back into `approved/` unheard. Second scenario: the owner edits the task, so the stored hash differs; the ledger falls through to `ended`, two paid sessions run, and `enter` fails on `cp -n` because the old approved file is still there.
Options: (a) as written (`gauntlet-design.md:120`, `plan-review-design.md:110`, `spec-review-design.md:103`, `:105`); (b) (proposal) the block's first script node, and `fail`, set the slug's round, review, ruling and cite files aside with its approved files, into `gauntlet/failed/<slug>.approved/`, whenever the recorded hash differs or a failed record exists, so the rerun starts at round 1; (c) (proposal) `state` returns a new owed value `stale` for those two cases and `open` fails at once, naming the files for the owner to move, before any agent runs (as G-25's option c).
Route: load-bearing (ledger `owed` values, a path), D-38.

**G-52** `fail` cannot record a second DEFECTIVE verdict on one slug (row H24).
Members: 2.02.
Where: `gauntlet-design.md:117-118`, `:124`, `:400`.
Statement: `fail` copies the verdict with `cp -n` and exits non-zero when the target exists. Scenario: a slug is judged defective once, the owner starts a new run, the new plan is judged defective too; `fail` finds `gauntlet/failed/<slug>.txt`, exits non-zero, the run fails and every resume fails, instead of ending cancelled at `kill`.
Options: (a) as written; (b) (proposal) `fail` first moves the existing `<slug>.txt` into `gauntlet/failed/<slug>.approved/verdict.<n>.txt` (n the next free number), then copies the new verdict to `<slug>.txt`, so Clerk keeps reading one name; (c) (proposal) `fail` overwrites `<slug>.txt`, the older verdict kept only in git-ignored history.
Route: load-bearing (path `gauntlet/failed/<slug>.txt`), D-39.

**G-53** `open` and `swear-in` start Opus sessions when the hearing is already decided (row H29).
Members: 2.30.
Where: `spec-review-design.md:355`, `:365`, `:225`; `plan-review-design.md:268`, `:277`.
Statement: both nodes run unless `owed` is `approved`. Scenario: the owner had approved in an earlier run and the run died before `enter`; the rerun reads `owed: ended`, yet two Opus sessions read the whole record before the loop ends one iteration later with nothing to do.
Options: (a) as written; (b) (proposal) both nodes also skip when `owed` is `ended`, the loop going straight to `enter`. Depends on the ruling of G-51 (which decides when `ended` can hold on a fresh run).
Route: ask-user seam.

**G-54** Plan review's repair guard can never fire (rows H28, H29; amends the G-04 amendment).
Members: 2.19.
Where: `plan-review-design.md:25`, `:101`, `:117-119`, `:131`, `:133`, `:136`, `:418`.
Statement: the owner is to be asked after 5 repair-only iterations (a defense turn whose citations did not resolve). The ledger reads a case only from a review written in the same iteration, and a repair-only iteration writes none. Scenario: a citation that never resolves; the defense repairs 200 times at Opus cost and the run ends on `max_iterations` without one ask.
Options: (a) as written; (b) (proposal) the guard case reads `repairs` from state whatever the iteration wrote, and its `round` is the round of the plan being repaired, so `record` writes the ruling for that round; (c) (proposal) `cite` fails the node on the fifth unresolved iteration, a stop naming the markers, with no ask.
Route: load-bearing (docket case contract, H28), D-40.

**G-55** The loop bound counts iterations while `cap` counts something else (rows H28, H29, A15, S7; cites G-38).
Members: 2.20, 2.31, 2.52.
Where: `plan-review-design.md:26`, `:102`, `:286`; `spec-review-design.md:374`; `writing-design.md:355`, `:174`.
Statement: `max_iterations: 200` counts iterations. Plan review's and spec review's `cap` counts tried rounds, so an iteration that adds no round (a repair, a refused write) moves the loop toward 200 without moving the ask. Scenario: the arbiter keeps writing a file name the fence refuses; the same round reruns until iteration 200 and the run fails without asking. Writing already counts iterations (G-38); only its comment still says moves.
Options: (a) as written; (b) (proposal) plan review and spec review count iterations as writing's `state` does (a line appended per `state` call to `<slug>.iter.txt`), and writing's comment says iterations.
Route: load-bearing (a new ledger path and field), D-41.

**G-56** The twelfth LEADING review asks, then the next iteration cancels (rows H38, H28; relates to G-11).
Members: 2.32.
Where: `spec-review-design.md:102`, `:506`; `plan-review-design.md:25`, `:133` (same shape, not reviewer-cited).
Statement: stretch reaches 12 on the twelfth LEADING review, so `docket` returns `guard` and the owner is asked; the next iteration `filing` reports `vacant` and `vacate` cancels. Scenario: the owner types guidance in answer to the ask and the run is cancelled one step later with the reply discarded.
Options: (a) as written; (b) (proposal) `docket` returns `none` when `next` is `vacant`, so the cancel comes first and nothing is asked.
Route: ask-user seam.

**G-57** Plan review's `open` holds `Agent` and declares no sub-agent (row A19).
Members: 2.22.
Where: `plan-review-design.md:159`, `:176`, `:270`, `:316-320`; `spec-review-design.md:358`.
Statement: the defense's opening turn is told to dispatch a detective, but only the later turn node declares one. Scenario: the opening turn tries `Agent` to `detective`, which that node does not define; the call fails (a lost turn) or reaches an agent nobody fenced.
Options: (a) as written; (b) `open` takes `allowed_tools: []` as spec review's does (`spec-review-design.md:358`) and the Detectives sentence applies to `defend` only; (c) `open` declares the same `agents: detective` as `defend`.
Route: ask-user seam.

**G-58** `report` against "no agent node starts a session per round but `screen`" (missing row: agent sessions; A13).
Members: 2.23.
Where: `plan-review-design.md:19`, `:336`, `:367-374`, `:427`.
Statement: `report` is a fresh session for each approved round, yet line 19 names `screen` as the only per-round starter, while `:336` and `:427` except `report`.
Options: (a) as written; (b) line 19 says "but `screen` and `report`" like `:336` and `:427`.
Route: ask-user seam.

**G-59** The defense's `[cite: path | quote]` marker cannot carry `]` or `|` (missing contract: the marker grammar; P20).
Members: 2.25.
Where: `plan-review-design.md:69`, `:171`.
Statement: the grammar has no escape. Scenario: the defense cites `items[0]` or `a | b`; `cite.py` answers "quote not found" with no hint, and a repair-only Opus iteration is spent on a marker that was right.
Options: (a) as written; (b) (proposal) the parser splits on the first ` | ` and ends the quote at the last `]` of the marker's line, stated in `cite.py` and `defense.md`; (c) (proposal) the unresolved reason names the cause "quote holds `]` or `|`".
Route: ask-user seam.

**G-60** The speccer node holds the spiker's tools through the shared `speccer.mcp.json` (rows F4, F12; cites G-03).
Members: 2.26.
Where: `spec-review-design.md:53`, `:253`, `:279`, `:520`; `mcp-servers.md:241-245`; `workflow-language.md:126`, `:641`.
Statement: the G-03 amendment gave the speccer `fence-files` only and the spikers `fence-scratch` and `fence-spike`. One config names all three and both speccer nodes use it, and Archon adds a wildcard for every declared server to the node. Scenario: the speccer itself calls `run_command` and runs a shell command; the confinement rests on the prompt.
Options: (a) as written; (b) (proposal, untested) the speccer nodes carry `denied_tools` naming the `mcp__fence-scratch__*` and `mcp__fence-spike__*` tools (`denied_tools` is documented at `workflow-language.md:126`, `:641`; whether it takes wildcards and whether a sub-agent keeps its own `tools:` is unmeasured); (c) (proposal) the spiker becomes its own node with its own config naming `fence-scratch` and `fence-spike`, started by the speccer's reply.
Route: load-bearing (fence config F4/F12, A10), D-42.

**G-61** `fence/spike.py` `run_command` confines only the working folder (rows F12, P14, P15; cites G-03).
Members: 2.27.
Where: `spec-review-design.md:279`, `:294-295`, `:302`, `:520`; `gauntlet-design.md:31`, `:381`.
Statement: `run_command` requires its folder inside `gauntlet/scratch` and then runs `bash -c <command>` as the owner. Scenario: a spiker's command is `cat ../../failed/x.txt` or `sed -i` on a source file; nothing stops it, so the G-03 premise "no Bash read is left open" is false.
Options: (a) as written (Homes rows and prompt carry the confinement); (b) (proposal) the command runs inside an OS-level confinement of the child process (not measured on this host; needs a probe, D-03); (c) (proposal) `run_command` takes an argv list from an allow-list of test runners and runs no shell.
Route: load-bearing (fence tool F12, A10), D-43.

**G-62** The spiker's node prompt restates `run_command`'s command form wrongly (missing row: spike.py command form; P14).
Members: 2.34.
Where: `spec-review-design.md:295`, `:411`, `:527`.
Statement: the prompt says it runs `timeout -k 10 600 nice -n 10 <command>`; the tool runs `timeout -k 10 600 nice -n 10 bash -c <command> < /dev/null`, and Homes `:527` forbids a prompt restating the mechanics.
Options: (a) as written; (b) the prompt drops the form and says only that the tool runs one command at a time with a time limit.
Route: ask-user seam.

**G-63** The `screen` workflow's includers omit writing (rows H26, F7).
Members: 2.33.
Where: `spec-review-design.md:183`, `:188`, `:517`, `:12`; `writing-design.md:453`.
Statement: three lines say plan review and spec review include it, but writing includes it too.
Options: (a) as written; (b) the three lines name writing as well.
Route: ask-user seam.

**G-64** `contracts.md` rows carry values the pass-1 rulings replaced (rows H5, A12, P6, A26, F1; cites G-16, G-19, G-20).
Members: 2.10, 2.17, 2.18, 2.24.
Where: `contracts.md:21` (H5), `:161` (A12), `:67` (P6), `:175` (A26), `:89` (F1); `gauntlet-design.md:26`; `gauntlet-intake-design.md:110-118`, `:195`; `plan-review-design.md:229`.
Statement: the inventory is the closed reference later phases build against, and five rows still quote the pre-ruling value. Scenario: Phase 3 builds the Clerk config from A12 and gives Clerk write rights over `gauntlet/tasks`, which G-16 removed; Phase 4 builds the slug pattern from A26 and rejects the empty slug G-19 needs.
Options: (a) as written; (b) each row takes the ruled value its design now gives: H5 "declares an `output_format`", A12 no `FENCE_WRITE`, P6 Writer the `put` node, A26 the pattern allowing "", F1 the `*.cite.*.txt` deny.
Route: load-bearing (fence value, hand-off, rows), D-44.

**G-65** Homes row `gauntlet-design.md:390` still forbids `worktree` in a phase file (rows A1, H13-H15; cites G-12).
Members: 2.05.
Where: `gauntlet-design.md:24`, `:154`, `:390`.
Statement: G-12 made the three phase files `worktree: { enabled: false }`; the Homes row forbids the key there.
Options: (a) as written; (b) the row allows `worktree: { enabled: false }` in the standalone phase files.
Route: ask-user seam.

**G-66** `settings` drops out of the chain into `write` (rows H18, H19, P19).
Members: 2.06, 2.35.
Where: `gauntlet-design.md:186`, `:192-193`, `:201`, `:207`, `:214`; `worktree-cut-design.md:189`.
Statement: the cut design's hand-off waits for `copy-in`, `baseline` and `settings`; the gauntlet design's node `paths` waits for the first two only. Scenario: `settings` fails (it writes `gauntlet/settings.json`); `paths` still runs and the writers start, and each writer's check tool and `@base` fence refuses for the missing file, paying a refused agent turn each.
Options: (a) as written; (b) `paths` takes `depends_on: [copy-in, baseline, settings]`.
Route: load-bearing (node chain), D-45.

**G-67** `copy-in` carries the first mend's verdicts into the re-mend (rows H40, H31).
Members: 2.07, 2.63.
Where: `gauntlet-design.md:398`; `landing-design.md:118-119`, `:178`, `:181`, `:378`.
Statement: the re-mend run's tree receives the whole previous `gauntlet/`, including `gauntlet/mend/` verdict, review and reply files. `hear`'s number and `pose`'s stall count count them. Scenario: the first mend ended after 4 verdicts; the re-mend's first verdict is its fifth, so it asks the owner at once; the juror is also fed the superseded verdicts.
Options: (a) as written; (b) (proposal) `copy-in` copies everything except `gauntlet/mend/<slug>.verdict.*`, `.review.*`, `.reply.*`, `.grounds.*` and `.rebased.*`, so the re-mend starts its own numbering; (c) (proposal) `copy-in` copies all, and `hear`, `pose` and the juror prompt count and read only files newer than a start marker `copy-in` writes.
Route: load-bearing (path and copy rule, H40), D-46.

**G-68** A move found at the last round's gate wait ends the run unlanded and unnamed (rows H23, H39; cites G-45).
Members: 2.03, 2.58.
Where: `gauntlet-design.md:17`, `:19`, `:106-112`; `landing-design.md:288-289`, `:329`, `:331`, `:503`.
Statement: G-45 says a third move stops the run, naming the move. `land-3` stops a move found at its start (`onto`) but a move found while it waits at the gate only makes `merge` print `moved` and exit 0, and no node follows. Scenario: the checkout moves twice before round 3, then the owner answers `land` in round 3 while a colleague commits; `merge` prints `moved`, the run completes with the branch unlanded and no message.
Options: (a) as written; (b) (proposal) in the last round (`remend` `no`) `merge` exits 1 naming the move, as `onto` does; (c) (proposal) a fourth node after `land-3` fails when `land-3` handed off `moved`.
Route: load-bearing (outcome of block `land`, H23), D-47.

**G-69** The re-mend bound counts rounds, not re-mends (row H39; cites G-45).
Members: 2.04, 2.59.
Where: `gauntlet-design.md:17`, `:106`; `landing-design.md:243-244`.
Statement: G-45 ruled at most two re-mends. A move found at `onto` re-mends in the same round; a move found at the gate wait uses a round and re-mends in the next. Scenario: the checkout moves during `land`'s gate wait (no re-mend yet), `land-2` re-mends once, the checkout moves again during its wait, `land-3` stops with "for the third time, after landing re-mended twice" though it re-mended once.
Options: (a) three rounds kept, the sentences (`gauntlet-design.md:17`, `landing-design.md:243`) say what the shape does: "a move found at the start of the third round stops the run"; (b) four rounds (`land` to `land-4`), so two re-mends hold whatever the timing of the moves; the message and `gauntlet-design.md` change with it.
Route: load-bearing (node ids in `gauntlet-run`, H39), D-48.

**G-70** "In the tree only" against landing's copy into the checkout (row P3).
Members: 2.08.
Where: `gauntlet-design.md:269`, `:286`, `:398`; `landing-design.md:298-301`.
Statement: approved revision files are said to live in the tree only and `enter` to be their only writer; landing's `record` copies them into the checkout.
Options: (a) as written; (b) `:286` and `:269` say "written by `enter` in the tree, copied into the checkout by `record` on landing".
Route: ask-user seam.

**G-71** "No phase goes back to an earlier phase" against the re-mend (rows H39, H40).
Members: 2.09.
Where: `gauntlet-design.md:7`, `:388`; `landing-design.md:9`.
Statement: landing starts a run that executes block `mend`, a phase before it.
Options: (a) as written; (b) the sentence and the Homes row say the re-mend run repeats only block `mend`, in a second tree, and no `gauntlet-run` node goes back.
Route: ask-user seam.

**G-72** Intake's `talk` loop ends on a node its own condition can skip (row A15; cites G-26).
Members: 2.11.
Where: `gauntlet-intake-design.md:208-213`, `:212`; `loop-nodes.md:696-697`, `:930`.
Statement: G-26 required completion to read only nodes that always run; intake's `until_bash` reads `put`, which the first iteration skips. Scenario: the owner's first answer is `approve` on the opening draft; the group's completion check reads a node with no output and the group fails before the task file is handed off.
Options: (a) as written; (b) `until_bash` reads `answer` and the task path from a node that always runs (a script node with `trigger_rule: all_done` that prints `put`'s task, else `put-open`'s).
Route: load-bearing (node id, A15 form), D-49.

**G-73** A `put-open` refusal never reaches Clerk, and `show` shows a stale one (missing contract: the refusal hand-off; cites G-16).
Members: 2.12.
Where: `gauntlet-intake-design.md:221`, `:235`, `:263`.
Statement: Clerk's next turn is handed `$LOOP_PREV.put.output.refusal`; in iteration 2 that is iteration 1's skipped `put`. Scenario: the opening draft's slug is taken by another run, `put-open` refuses, the owner answers; Clerk is not told, writes the same slug again, is refused again, and another owner round is spent. Later, `show` keeps printing the opening refusal though `put` succeeded.
Options: (a) as written; (b) (proposal) a script node that always runs prints the latest refusal (put's, else put-open's); Clerk's prompt and `show` both read it.
Route: load-bearing (new node, hand-off), D-50.

**G-74** `put` prints nothing when the draft is empty (script `put`; `output_format` `:204`, `:230`).
Members: 2.13.
Where: `gauntlet-intake-design.md:138`, `:204`, `:230`.
Statement: the script is declared to write nothing for an empty draft or slug, but both nodes require `{ slug, task, refusal }`. Scenario: Clerk's first reply asks questions and holds no draft; `put-open` prints nothing, fails its `output_format`, and the Clerk route stops before the owner reads the reply.
Options: (a) as written; (b) the branch prints `{ "slug": "", "task": "", "refusal": "" }`.
Route: ask-user seam.

**G-75** Intake's hand-off picks the slug by marker and a second slug leaves two markers (row H3).
Members: 2.14.
Where: `gauntlet-intake-design.md:96`, `:139-142`, `:257`.
Statement: only Clerk's prompt keeps the slug fixed after the first write. Scenario: Clerk writes slug `fix-login`, later changes it to `fix-the-login`; two markers and two files exist and `handoff` has no rule to choose; the unused file is later seen as a slug taken by another run.
Options: (a) as written; (b) (proposal) `put` refuses a slug unlike the one its first marker owns, with a refusal naming it; (c) (proposal) `handoff` takes the task path from the latest successful `put`.
Route: ask-user seam.

**G-76** Clerk re-emits the whole task file every turn (internal to intake; CLAUDE.md 1.3).
Members: 2.15.
Where: `gauntlet-intake-design.md:96`, `:138`, `:212`.
Statement: "again every turn after" costs the output tokens of the whole file each turn, needed only because an empty draft counts as no task file. Scenario: a 60-line task file and ten turns, each answer restating it whole.
Options: (a) as written; (b) (proposal) an empty draft after the first write means "unchanged": `put` prints the existing task path and writes nothing.
Route: ask-user seam.

**G-77** "Script nodes run on Bun" stated for the whole pack (internal to intake; cross-design wording).
Members: 2.16.
Where: `gauntlet-intake-design.md:9`; `runtime: uv` in the other six designs.
Statement: the line is true of intake and the cut's guard, false of the ledgers, `pin.py`, `stage.py`, `verify.py` and `cite.py`.
Options: (a) as written; (b) "Intake's script nodes run on Bun; the Python ones named in the other designs run on `uv`".
Route: ask-user seam.

**G-78** Which test variables the guard requires, and what the config example shows (rows P11, H1; cites G-31).
Members: 2.36, 2.40, 2.46.
Where: `gauntlet-design.md:139-140`; `worktree-cut-design.md:169-170`, `:201`, `:208-210`, `:224`; `writing-design.md:524-525`, `:528`, `:542`.
Statement: the guard refuses a blank test command or brief command and a malformed timeout. The cut's Homes row says all four variables are refused when blank or malformed, though timeout and base have defaults; the config example omits the brief command that the guard requires; writing requires `GAUNTLET_TEST_COMMAND` though nothing reads it since G-29. Scenario: a repository sets the brief command and a timeout only; built to the Homes row, the run stops at start for the unset base; built to the example, the brief command is missing and every run is refused.
Options: (a) as written; (b) (proposal) required: `GAUNTLET_TEST_BRIEF_COMMAND` only; `GAUNTLET_TEST_COMMAND` dropped from the guard, `writing-design.md:528` and the example; timeout and base optional with their defaults; the example block lists brief command, timeout and base; (c) (proposal) keep `GAUNTLET_TEST_COMMAND` required and name its reader (the `settings.json` "test" key, which D-36 left without one).
Route: load-bearing (env contract H1, P11), D-51.

**G-79** Script nodes read `GAUNTLET_*` from the environment (rows H1, A11, P19; cites G-31).
Members: 2.44, 2.45.
Where: `writing-design.md:22`, `:86-87`, `:122`, `:159`; `gauntlet-design.md:139-143`.
Statement: the repository `env:` is measured for bash nodes only. `stage.py` is a script node and reads the blank checks and the test base from its environment, where every other reader takes `gauntlet/settings.json`. Scenario: the variables are set but a script node does not see them; every `stage.py` mode exits 1 at the first call, or every test-base path is a cut problem and the divvy repeats until `stalled`.
Options: (a) as written; (b) (proposal) `stage.py` reads `gauntlet/settings.json` ("brief", "base"), and the blank check lives in the guard only; (c) (proposal) a probe measures whether the repository `env:` reaches a script node (D-03), and (a) or (b) follows from it.
Route: load-bearing (script input, P19), D-52.

**G-80** The tree run's `.gitignore` check and the run-start check differ (rows H2, S2, S3, H1).
Members: 2.38.
Where: `worktree-cut-design.md:94-95`, `:160`; `gauntlet-intake-design.md:56`, `:60`; `gauntlet-design.md:136-137`.
Statement: the run-start guard passes when git reports `gauntlet/` ignored in the checkout (the working copy counts); the tree has only committed files. Scenario: the owner adds `gauntlet/` to `.gitignore` without committing; the run-start guard passes, intake, plan review and spec review are paid for, then the tree run's `guard` fails, and a resume reuses the same tree and fails again.
Options: (a) as written; (b) (proposal) the run-start guard also requires the ignore line in `HEAD`'s `.gitignore` (or `.git/info/exclude`, which a tree shares) and its message says to commit it, as G-31 requires for `.archon/config.yaml`.
Route: load-bearing (guard check list, H1), D-53.

**G-81** An ignored or uncommitted `.archon/config.yaml` may not reach the tree run (rows P11, H20, H1; cites G-31).
Members: 2.39.
Where: `worktree-cut-design.md:35`, `:164-186`; `gauntlet-design.md:138-141`.
Statement: the guard refuses a config with uncommitted changes, which `git status` does not report when the file is ignored, and the cut design states it is unmeasured whether such a config's `env:` reaches the tree run. Scenario: it does not reach; `baseline` runs `bash -c ""` (exit 0), `settings` writes an empty `brief`, no red can fire, and untested code reaches the land gate.
Options: (a) as written; (b) (proposal) the guard also refuses a config that is untracked, ignored or different from `HEAD`; (c) (proposal) node `settings` exits 1 when the brief command is blank, before any paid writer starts.
Route: load-bearing (guard check list, node `settings`), D-54.

**G-82** The Homes row on the slug forbids what G-23 requires (rows H36, H16).
Members: 2.37.
Where: `worktree-cut-design.md:18`, `:217`; `spec-review-design.md:90`, `:360`; `plan-review-design.md:92`, `:272`, `:407`; `gauntlet-intake-design.md:180`.
Statement: the row says only `gauntlet-run/scripts/pin.py` derives the slug; G-23 has `.shared/rounds.py` derive it from `INPUTS_TASK` and the opening prompts name it. Scenario: a Phase 5 builder who follows the Homes row removes the derivation from `rounds.py`, so a standalone plan review has no slug.
Options: (a) as written; (b) the row is scoped to the tree run, as `:18` says "this phase"; (c) (proposal) one function in `.shared/pin.py` derives the slug and `rounds.py` and `from-file` import it, the prompts being told the slug by the ledger state.
Route: load-bearing (slug derivation, H36), D-55.

**G-83** The `base` a branch that exists is given (rows S14, S15, H16, H17).
Members: 2.41, 2.67.
Where: `worktree-cut-design.md:65-66`, `:69`; `landing-design.md:343-344`, `:349`.
Statement: for a branch that exists, the cut design says `base` is the merge-base with the source; landing says it is the full hash of the branch tip. No design reads `base`.
Options: (a) as written (two values); (b) the tip hash in both, as landing's; (c) (proposal) `pin` prints no `base` and the merge-base branch and its test go, as G-32 dropped `uncommitted`.
Route: load-bearing (stdout field of `pin`, S14), D-56.

**G-84** The second re-mend's tree is described as pinned at the first tree (rows H39, H40, S15).
Members: 2.42.
Where: `worktree-cut-design.md:21`, `:42`; `landing-design.md:342`; `gauntlet-design.md:103-104`.
Statement: round `land-2` pins at the previous round's tree branch (the re-mend's), not the first tree's.
Options: (a) as written; (b) the two lines say "pinned at the tip of the branch of the tree the round lands, the first tree's for round 1" and "holds a copy of the previous tree's `gauntlet/`".
Route: ask-user seam.

**G-85** The Homes bans on `git branch` and on "copy" commands read literally forbid used nodes (rows H9, H40).
Members: 2.43.
Where: `worktree-cut-design.md:164`, `:192`, `:220`, `:223`; `landing-design.md:378`.
Statement: `branch-check` and `handoff` run `git branch --show-current`; `copy-in` runs `cp -n`.
Options: (a) as written; (b) the two rows are scoped: "any other `git branch` command that creates, moves or deletes a branch" and "any install or setup command".
Route: ask-user seam.

**G-86** Two contradicting lines on the `commit` tool's return (rows F8, F9; cites G-41).
Members: 2.47.
Where: `writing-design.md:72`, `:73`, `:541`.
Statement: line 72 returns hook names only; line 73 returns git's and the hooks' output.
Options: (a) as written; (b) line 73 goes (the G-41 amendment kept line 72).
Route: ask-user seam.

**G-87** A failed commit is "ruled on the file that fails the hook" with no file known (row R7).
Members: 2.48.
Where: `writing-design.md:72`, `:164`, `:217`, `:290`.
Statement: grounds hold hook names only, and no file stores hook output. Scenario: a pre-commit hook fails; the juror gets a hook name and no file to rule on.
Options: (a) as written; (b) the juror rules on the block's paths and the hook names, and `:217` says so.
Route: ask-user seam.

**G-88** Carried unrun waves are joined into one `wave` and can run twice (internal to writing; row S5; cites G-37).
Members: 2.49.
Where: `writing-design.md:28`, `:131`, `:132`, `:160`.
Statement: G-37 carries the replaced cut's unrun waves into the next cut. The text joins them with the new cut's first wave into one list, which breaks "blocks of one wave share no path" and "one kind per fan-out", gives carried blocks the new cause's ruling, and runs a code step twice when the new cut already holds it. Scenario: a code cut replaced mid-way; the carried wave and the new cut both hold step 3 and it is written twice.
Options: (a) as written; (b) (proposal) `state` hands one wave per iteration, carried waves first, each with its own ruling, and a carried block whose step an uncommitted earlier block's new cut holds is dropped.
Route: load-bearing (`state` field `wave`, S5), D-57.

**G-89** The reviser is not handed the path its answer names (row R12; cites G-43).
Members: 2.50.
Where: `writing-design.md:137`, `:225`, `:448`.
Statement: `state` prints `cause` for `revise` but the reviser's prompt omits it. Scenario: round 1 has no earlier round file, so the reviser has no path for its `Answers:` line and `enter` or the ledger refuses the file.
Options: (a) as written; (b) the prompt adds `cause $state.output.cause`.
Route: ask-user seam.

**G-90** `record` writes a ruling under the move of the verdict that raised it (row S5; cites G-42).
Members: 2.51.
Where: `writing-design.md:29`, `:173`, `:362`.
Statement: G-42 ruled `$state.output.move`, which `record` cannot read (`record` runs before `state`); the text uses the previous iteration's move, so a ruling and a verdict share a number. Scenario: a stall at move 5 writes `ruling.5` beside `verdict.5`; a count "since the latest writing ruling" then ties, and the stall can fire again right after the owner replies.
Options: (a) as written (`$LOOP_PREV.state.output.move`); (b) `record` derives the move from the files, the next free number (G-42's option b).
Route: ask-user seam.

**G-91** The reviser's rules point at `speccer.md` (rows R12, R3).
Members: 2.53.
Where: `writing-design.md:19`, `:228`; `gauntlet-design.md:413`.
Statement: a file the reviser cannot read and a Homes row bans.
Options: (a) as written; (b) the reviser's role states the rule itself ("a spec revision holds no source text").
Route: ask-user seam.

**G-92** A failed `enter` is followed by `state` (row H8).
Members: 2.54.
Where: `writing-design.md:373`, `:369-372`; `gauntlet-design.md:269`.
Statement: `state` runs on `all_done`, so after `enter` exits non-zero it treats the round as closed. Scenario: `enter` fails on an existing target; the next move divvies against files lacking the revision and the approved revision is silently dropped.
Options: (a) as written; (b) `state` takes `trigger_rule: none_failed_min_one_success`, so a failed `enter` fails the iteration and a resume re-drives it.
Route: ask-user seam.

**G-93** Two parallel writers in one checkout (row A9).
Members: 2.55.
Where: `writing-design.md:69-70`, `:399`, `:417`; `workflow-language.md:2613-2614`.
Statement: Archon's doc says instances share the parent's checkout and writers must coordinate. Writing coordinates paths only. Scenario: block A's check tool runs the suite over block B's half-done files and contests a test that is not wrong; A's pre-commit stashes B's unstaged edits and fails to restore them, giving a spurious `commit-failed` and a juror dispatch.
Options: (a) as written (`max_parallel: 2`); (b) `max_parallel: 1` on both fan-outs (`workflow-language.md:2615`); the waves run one block at a time.
Route: load-bearing (A9 row value), D-58.

**G-94** "Reuses `checks.py` unchanged" (rows P14, P19).
Members: 2.56.
Where: `writing-design.md:13`, `:78-90`.
Statement: Order step 1 changes `checks.py`.
Options: (a) as written; (b) "reuses `checks.py` with the settings-file change of `:78-90`".
Route: ask-user seam.

**G-95** Two stall rules for the one copy writing and landing share (missing contract: the stall count; `landing-design.md:22`).
Members: 2.57.
Where: `writing-design.md:173`; `landing-design.md:22`, `:181`.
Statement: writing counts verdicts and rejected cuts since the latest writing ruling; landing says 5 verdicts since the latest owner ruling (the mend has no cuts).
Options: (a) as written; (b) landing's line says "the same count, with no cuts in the mend".
Route: ask-user seam.

**G-96** The rebase marker is not written on a conflict (row H22; cites G-44).
Members: 2.60.
Where: `landing-design.md:48-49`, `:55-58`, `:202`.
Statement: G-44 reruns `test-tree` on resume through a marker `rebase` writes after a changing rebase; a conflict exits 1 first. Scenario: a rebase conflicts, the owner resolves it by hand with `git rebase --continue` and resumes; `onto` sees no move and no marker, skips every test and repair node, and the gate shows "not rerun" for a rebase nobody tested.
Options: (a) as written; (b) `rebase` writes the marker before it runs git, so a conflict leaves it.
Route: ask-user seam.

**G-97** The Homes row forbids the test run G-44 requires (row H22; cites G-44).
Members: 2.68.
Where: `landing-design.md:48-49`, `:495`.
Statement: "a test run when the checkout's HEAD is in the branch's history" is forbidden, and the marker rule runs `test-tree` in exactly that state.
Options: (a) as written; (b) the row says "except after a first-pass rebase, marked by the marker file".
Route: ask-user seam.

**G-98** The mend's juror and reviewer are promised a log and diff nothing produces (row H34; missing producer row).
Members: 2.61.
Where: `landing-design.md:119`, `:169`, `:413`, `:449`; `fence/files.py`.
Statement: juror and reviewer have `allowed_tools: []` and fence-files and no git tool, and no `mend` node writes the log and diff. Scenario: `mend-review` is asked whether the mend is sound and cannot see what the mend changed.
Options: (a) as written; (b) (proposal) a node `changes` runs `git -C <tree> log -p $onto.output.head..$INPUTS.branch` into `gauntlet/mend/<slug>.changes.<n>.txt` and the prompts name that file; (c) (proposal) the clause goes and the roles read the committed files through fence-files.
Route: load-bearing (new node, path), D-59.

**G-99** `pose` ends "done" after a retry although a committed mend was never reviewed (row H34; cites G-50).
Members: 2.62.
Where: `landing-design.md:160`, `:176-178`, `:498`.
Statement: the G-50 amendment ends the repair "done" when a retry rerun is not red and no mend is uncommitted; `:160` says `review` runs "every committed mend ... not after a retry or a red recheck", so a mend committed in a red-recheck iteration is never read once a later retry is green. Scenario: iteration 1 commits a CODE mend, recheck red, review skipped; iteration 2 DEFECTIVE, the owner chooses `retry`; iteration 3 is green; the mend lands unreviewed.
Options: (a) as written; (b) the retry arm ends "done" only when the latest committed mend has a SOUND review; otherwise `review` runs once more.
Route: ask-user seam.

**G-100** The resume advice after a refused merge cannot work (row H39).
Members: 2.64.
Where: `landing-design.md:220`, `:290-291`, `:329`.
Statement: "Stash or commit those edits, then resume". A commit moves `HEAD`; the resume replays `gate` and `merge --ff-only` fails again. Scenario: the owner commits the edits as told, resumes, `merge` fails with the same advice; in the last round `onto` fails on the owner's own commit. `merge` also reads any ff-only refusal as uncommitted edits.
Options: (a) as written; (b) the advice says "stash those edits"; `merge` tells uncommitted edits apart from a moved `HEAD` by `git status`.
Route: ask-user seam.

**G-101** `remove` deletes the folder `onto` reads on resume (rows H37, H39).
Members: 2.65.
Where: `landing-design.md:240-241`, `:353`.
Statement: `onto` reads the tip from the tree folder; `remove` deletes that tree first. Scenario: removal completes, `archon complete` fails, and the owner resumes: `onto` runs `git -C` on a deleted folder and every resume fails.
Options: (a) as written; (b) `onto` reads the tip with `git rev-parse` in the checkout, where a worktree's branch is visible, so it needs no tree folder.
Route: ask-user seam.

**G-102** Which run id the owner answers a re-mend ask on (rows H31, A21).
Members: 2.66.
Where: `landing-design.md:9`, `:22`, `:31`, `:353`, `:500`; `gauntlet-design.md:7`, `:129`, `:395`.
Statement: lines 9 and 22 say the tree run's id; in a re-mend it is the re-mend run's.
Options: (a) as written; (b) the two lines say "the id of the run the mend executes in".
Route: ask-user seam.

**G-103** A stale step number in the landing Order (build order; row H39).
Members: 2.69.
Where: `landing-design.md:514`; `gauntlet-design.md` Order (10 steps).
Statement: "step 11 needs step 6" names a step that does not exist; the landing step is 10.
Options: (a) as written; (b) "step 10".
Route: ask-user seam.

Route count: load-bearing 22 (G-51, G-52, G-54, G-55, G-60, G-61, G-64, G-66, G-67, G-68, G-69, G-72, G-73, G-78, G-79, G-80, G-81, G-82, G-83, G-88, G-93, G-98), D-38 to D-59; ask-user 31.

## 10. Rulings (Plan 3 Task 3, round 2)

Each group carries one ruling, the row of its group id below, copied unchanged from `RULINGS.md` section "Pass 2 rulings". Where `/cad-decision-review` amended a ruling, the amendment is in `DECISION-REVIEW.md` under its D-NN and is the ruling the designs follow. Rulings made after application (G-93/D-58, G-54/D-40, G-61/D-43) follow the table and were applied in the round-2 follow-up commit.

Authority. The owner ruled G-69 and G-61 on 2026-11-05. For G-61 the owner pointed back to the fence MCP server, the route the D-13 amendment already chose (`DECISION-REVIEW.md:78-83`). For the other 51 groups the main session took the proper fix under CLAUDE.md 3.2, as in pass 1; each is named `main session (3.2)`. The 22 load-bearing ones (D-38 to D-59) go through `/cad-decision-review` under D-05.

| Group | D-NN | Ruling | By |
|---|---|---|---|
| G-51 | D-38 | (b) `fail`, and the block's first script node when the recorded task hash differs or a failed record exists, set the slug's round, review, ruling and cite files aside with its approved files into `gauntlet/failed/<slug>.approved/`, so a rerun starts at round 1 | main session (3.2) |
| G-52 | D-39 | (b) `fail` moves an existing `<slug>.txt` to `gauntlet/failed/<slug>.approved/verdict.<n>.txt`, then copies the new verdict to `<slug>.txt` | main session (3.2) |
| G-53 | - | (b) `open` and `swear-in` also skip when `owed` is `ended` | main session (3.2) |
| G-54 | D-40 | (b) the guard reads `repairs` from state whatever the iteration wrote; its `round` is the round being repaired | main session (3.2) |
| G-55 | D-41 | (b) plan review and spec review count iterations as writing does; writing's comment says iterations | main session (3.2) |
| G-56 | - | (b) `docket` returns `none` when `next` is `vacant` | main session (3.2) |
| G-57 | - | (b) `open` takes `allowed_tools: []`; the Detectives sentence applies to `defend` only | main session (3.2) |
| G-58 | - | (b) line 19 names `screen` and `report` | main session (3.2) |
| G-59 | - | (b) the parser splits on the first ` | ` and ends the quote at the marker line's last `]`, stated in `cite.py` and `defense.md` | main session (3.2) |
| G-60 | D-42 | the spiker's fence servers reach the spiker only and never the speccer node: by a per-sub-agent server list if `docs/reference/archon/` documents one, else (c) the spiker as its own node with its own config; never an untested `denied_tools` wildcard | main session (3.2) |
| G-61 | D-43 | the D-13 amendment as ruled: the spiker holds no shell. `fence/spike.py`'s `run_command` (`bash -c <command>`) goes. The spiker writes its experiment files in `gauntlet/scratch/<slug>/` through `fence-files` and runs them through a fence tool with cwd in that folder, as `checks.py` runs the test command; the command the tool runs is fixed in the fence, never supplied by the agent | owner |
| G-62 | - | (b) the prompt drops the command form | main session (3.2) |
| G-63 | - | (b) the three lines name writing too | main session (3.2) |
| G-64 | D-44 | (b) H5, A12, P6, A26 and F1 take the ruled values | main session (3.2) |
| G-65 | - | (b) the row allows `worktree: { enabled: false }` in the standalone phase files | main session (3.2) |
| G-66 | D-45 | (b) `paths` takes `depends_on: [copy-in, baseline, settings]` | main session (3.2) |
| G-67 | D-46 | (b) `copy-in` skips `gauntlet/mend/<slug>.verdict.*`, `.review.*`, `.reply.*`, `.grounds.*` and `.rebased.*` | main session (3.2) |
| G-68 | D-47 | (b) in the last round `merge` exits 1 naming the move | main session (3.2) |
| G-69 | D-48 | (b) four rounds, `land` to `land-4`, so two re-mends hold whatever the timing of the moves; messages and `gauntlet-design.md` follow | owner |
| G-70 | - | (b) "written by `enter` in the tree, copied into the checkout by `record` on landing" | main session (3.2) |
| G-71 | - | (b) the re-mend run repeats only block `mend`, in a second tree; no `gauntlet-run` node goes back | main session (3.2) |
| G-72 | D-49 | (b) `until_bash` reads `answer` and the task path from an always-run node | main session (3.2) |
| G-73 | D-50 | (b) an always-run script node prints the latest refusal; Clerk's prompt and `show` read it | main session (3.2) |
| G-74 | - | (b) the empty branch prints `{ "slug": "", "task": "", "refusal": "" }` | main session (3.2) |
| G-75 | - | (b) `put` refuses a slug unlike the one its first marker owns | main session (3.2) |
| G-76 | - | (b) an empty draft after the first write means unchanged | main session (3.2) |
| G-77 | - | (b) "Intake's script nodes run on Bun; the Python ones run on `uv`" | main session (3.2) |
| G-78 | D-51 | (b) only `GAUNTLET_TEST_BRIEF_COMMAND` required; `GAUNTLET_TEST_COMMAND` dropped; timeout and base optional with defaults; the example lists brief command, timeout and base | main session (3.2) |
| G-79 | D-52 | (b) `stage.py` reads `gauntlet/settings.json`; the blank check lives in the guard only | main session (3.2) |
| G-80 | D-53 | (b) the run-start guard requires the ignore line in `HEAD`'s `.gitignore` or `.git/info/exclude`, and says to commit it | main session (3.2) |
| G-81 | D-54 | (c) node `settings` exits 1 on a blank brief command, before any writer starts (a refusal of an ignored config would stop on a config that may reach the tree) | main session (3.2) |
| G-82 | D-55 | (b) the Homes row is scoped to the tree run | main session (3.2) |
| G-83 | D-56 | (c) `pin` prints no `base`; the merge-base branch and its test go | main session (3.2) |
| G-84 | - | (b) "the tip of the branch of the tree the round lands" and "the previous tree's `gauntlet/`" | main session (3.2) |
| G-85 | - | (b) the two rows are scoped to branch-changing and install or setup commands | main session (3.2) |
| G-86 | - | (b) line 73 goes | main session (3.2) |
| G-87 | - | (b) the juror rules on the block's paths and the hook names | main session (3.2) |
| G-88 | D-57 | (b) one wave per iteration, carried first, each with its own ruling; a carried block whose step a newer cut holds is dropped | main session (3.2) |
| G-89 | - | (b) the prompt adds `cause $state.output.cause` | main session (3.2) |
| G-90 | - | (b) `record` takes the next free move number from the files | main session (3.2) |
| G-91 | - | (b) the reviser's role states the rule itself | main session (3.2) |
| G-92 | - | (b) `state` takes `trigger_rule: none_failed_min_one_success` | main session (3.2) |
| G-93 | D-58 | (b) `max_parallel: 1` on both fan-outs | main session (3.2) |
| G-94 | - | (b) "reuses `checks.py` with the settings-file change" | main session (3.2) |
| G-95 | - | (b) "the same count, with no cuts in the mend" | main session (3.2) |
| G-96 | - | (b) `rebase` writes the marker before it runs git | main session (3.2) |
| G-97 | - | (b) the row excepts the marked post-rebase run | main session (3.2) |
| G-98 | D-59 | (b) node `changes` writes `gauntlet/mend/<slug>.changes.<n>.txt` from `git -C <tree> log -p`; the prompts name it | main session (3.2) |
| G-99 | - | (b) the retry arm ends "done" only when the latest committed mend has a SOUND review | main session (3.2) |
| G-100 | - | (b) the advice says stash; `merge` tells edits from a moved `HEAD` by `git status` | main session (3.2) |
| G-101 | - | (b) `onto` reads the tip with `git rev-parse` in the checkout | main session (3.2) |
| G-102 | - | (b) "the id of the run the mend executes in" | main session (3.2) |
| G-103 | - | (b) "step 10" | main session (3.2) |

## Rulings after application (2026-11-05)

| Group | Decision | Ruling | By |
|---|---|---|---|
| G-93 | D-58 | a `blocked` outcome is a juror case, as `contest` and `commit-failed` are; the juror's verdict starts the cut that carries the block | main session (3.2) |
| G-54 | D-40 | a guard record resets the stretch as well as `repairs`: tried rounds with N > `since` and N at or above the latest guard record's round | main session (3.2) |
| G-61 | D-43 | objections 2 and 3: `fence/spike.py`'s fixed command is the constant `bash run.sh` in the folder; no settings file; the spiker writes `run.sh` | main session (3.2) |
