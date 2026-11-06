# Phase 1 review, pass 3 (convergence round 3 over the designs as committed at 87e0734)

Date: 2026-11-05
Plan: `.planning/phases/1/PLAN-3.md`, Task 3 (new-finding branch), round 3
Reviewed: the seven designs under `docs/superpowers/specs/` and `contracts.md` as committed at `87e0734`, with the ruled set G-01 to G-103 (`REVIEW-pass1.md`, `REVIEW-pass2.md`, `RULINGS.md`; `DECISION-REVIEW.md` amendments replace a ruling where they say so).

Ids: findings are `3.NN`; groups are `G-NN` from G-104. The owner named four groups by root cause (process ruling (c), D-62 in CONTEXT.md); they take G-104 to G-107 in the owner's order. The executor grouped the other findings by root cause from G-108. Mark per finding: `new`, or `matches G-NN` as the reviewer marked it. All 41 findings are open: a `matches` finding is a ruled group whose defect still stands, so it sits in a pass-3 group that cites the earlier one.

Severity: as each reviewer gave it. 7 high, 17 medium, 17 low. Under D-60 a low finding is recorded and fixed but does not reopen a round.

Sources: seven `cad-reviewer-medium` (opus) dispatches, saved unchanged as `.planning/phases/1/reviews/conv3-<design>.md`: 41 findings, 30 marked new and 11 marked as matching a ruled group. The graph check of this round (`reviews/convergence-graph-3.md`, committed in `87e0734`: 40 steps, no cycle, no forward need) holds no finding.

Check of anchors: every anchor was read with `sed -n` against the working tree, which equals `87e0734` for the seven designs and `contracts.md` (`git status` shows none of them modified). 41 of 41 anchors hold the quoted text, or its first line where it wraps. Every row id cited exists in `contracts.md`. The claims of the seven high findings were read against their cited lines and hold: 3.09 and 3.17 against `loop-nodes.md:682-684` and `workflow-language.md:773` (node `vacate` is a second sink); 3.18 and 3.30 against `spec-review-design.md:112` and `writing-design.md:148-150`; 3.28 and 3.29 against `writing-design.md:130-166`; 3.40 against `landing-design.md:234`. The medium and low claims were not re-derived one by one; their anchors hold.

Process rulings (owner, after round 3; CONTEXT.md D-60 to D-65; they bind this and later rounds):
- (a) D-60. Round-4 exit bar: no new high or medium finding (replaces "zero new findings"). Low findings are still recorded and fixed; they do not reopen a round.
- (b) D-61. In the round-3 apply step, cross-design citations change to node ids or headings, never line numbers. Each restated fact is cut down to one home; other designs point to it by name.
- (c) D-62. Pass 3 is grouped by root cause; the four named groups are G-104 to G-107, the rest from G-108.
- (d) D-63. After the rulings are applied, each ruling is grepped at every place its fact appears, before any reviewer runs.
- (e) D-64. A spiker copies the YAML from the designs into a scratch folder outside the pack and runs `archon validate workflows` on it: an orchestrator dispatch after apply.
- (f) D-65. The round-4 reviewer brief is the round-3 application diff plus a full read hunting high and medium defects only.

Missing contracts (rows to add under D-01 in the ruling commit, not in this record's commit): `cite.py`'s exit contract (G-104); the source of the reply intake's `show` displays (G-112); the reporter role's inputs (G-113); the cite-marker grammar, named missing by G-59 and still absent (G-114); a bound on spec-review iterations that try no round (G-115); the `gauntlet-run` head's node list (G-108).

## 1. gauntlet-design.md

Source: `reviews/conv3-gauntlet.md` (4 findings: 3 new, 1 matching). 4 of 4 anchors hold.

**3.01** `gauntlet-design.md:409`, row H24 (copy-list seed B09). Matches G-51, medium. Group G-108.
Text: "read by Clerk" (Home column); "a phase block reading or writing `gauntlet/failed/`" (Forbidden column).
Finding: the row forbids what its Home column and `:357-371` grant: intake's node `ground` lists `gauntlet/failed/`, and intake is a phase block. `:371` "Only Clerk reads `gauntlet/failed/`" also contradicts `ground.ts`. The D-38 wording aimed at the ledger's first script node now forbids intake's own reader.

**3.02** `gauntlet-design.md:409`, rows F1-F4, F9, F10 (seed B09). New, low. Group G-108.
Text: "a fence outside `intake/` with `FENCE_READ` covering `gauntlet/failed/` and no `FENCE_HIDE` for it".
Finding: the clause has no checkout scope. Tree fences (`divvyer`, `juror`, `reviser`, `reviewer-plan`, the coder, `mend-juror`, `mend-review`) set `FENCE_READ=.` with no hide for `gauntlet/failed`, yet no tree ever holds that folder. Read literally it forces about eight needless `FENCE_HIDE` additions or a stop.

**3.03** `gauntlet-design.md:102`, rows H16, H17, H23. New, low. Group G-109.
Text: "with: { slug: $pin.output.slug, round: land, worktree: $cut.output.worktree,".
Finding: the four landing rounds (`:102`, `:109`, `:116`, `:124`; `landing-design.md:240` "A round takes `slug` from node `pin`") read `pin`, an inner node of the cut phase whose hand-off `cut` prints no slug. The Homes row "The hand-off between phases" (`:401`) forbids "a phase reading another phase's inner node".

**3.04** `gauntlet-design.md:23`, rows H1, H5, H6, H12-H15, A1-A3, R12, S4-S6 (seeds B01-B12). New, low. Group G-108.
Text: "Resolved by G-12: `gauntlet-design.md:138`, `gauntlet-intake-design.md:152`, `plan-review-design.md:242`, ...".
Finding: nearly every `Resolved` line citation of the copy list (`:23-34`, 33 citations) lands on unrelated text at `87e0734` (`:138` is `depends_on: [fail]`, `:141` blank, `plan-review-design.md:413` `form: select`, `spec-review-design.md:325` a `fence/spike.py` comment). Only `writing-design.md:19` holds. G-12 corrected the bullets' facts, not the later line drift.

## 2. gauntlet-intake-design.md

Source: `reviews/conv3-gauntlet-intake.md` (4 findings: 4 new). 4 of 4 anchors hold.

**3.05** `gauntlet-intake-design.md:59-60`, rows H1, S3. New, medium. Group G-111.
Text: "a rule from a .gitignore passes only when git tracks that file and `git diff --quiet HEAD -- <file>` holds."
Finding: the D-53 form refuses the run whenever `.gitignore` has any uncommitted edit, even when `HEAD`'s copy already holds the `gauntlet/` rule the tree will get (an unrelated `*.log` line is enough). It pre-empts the `dirty` ask (`gauntlet-design.md:65-71`), which offers "Go on" for exactly such changes. Variant: the working copy adds the rule and `.git/info/exclude` also holds it; `check-ignore` names the `.gitignore`, so the run is refused though the tree shares `info/exclude`.

**3.06** `gauntlet-intake-design.md:255`, row A14; missing contract: the source of the reply `show` displays. New, low. Group G-112.
Text: "script: <print reply (turn's, else the opening), the refusal when there is one, a rule, then the task file or \"No task file yet.\">" with `reply: { from: $turn.output.reply, if_skipped: "" }` (`:257`).
Finding: `show` cannot tell a skipped `turn` from one that ran with an empty reply, so it reprints Clerk's opening questions above a new draft as if current.

**3.07** `gauntlet-intake-design.md:145`, rows P6, H3, the refusal hand-off added by G-73. New, low. Group G-112.
Text: "draft \"\" or slug \"\": writes nothing (an empty draft after the first write means unchanged),".
Finding: a non-empty draft with slug "" (the `clerk`/`turn` pattern allows "", `:205`, `:231`) is dropped with no refusal, unlike every other wrong-slug case (`:147-150`). Clerk believes its draft written; each owner answer is spent with no task file, and after a first write an edited draft is discarded silently.

**3.08** `gauntlet-design.md:23`, rows H13, A1, S13, H3, H6 (seeds B01-B05). New, low. Group G-108.
Text: the copy list's citations into the intake design, for example "`gauntlet-intake-design.md:152`" for the description.
Finding: `:152` is `put.ts`'s stdout comment (the description is at `:161-162`); `:157`, `:165`, `:260`, `:179`/`:186` and `:122` likewise land on a prose line, `effort: medium`, `show`'s `opening:` binding, comments and JSON. Same drift as 3.04, from the intake side.

## 3. plan-review-design.md

Source: `reviews/conv3-plan-review.md` (8 findings: 7 new, 1 matching). 8 of 8 anchors hold.

**3.09** `plan-review-design.md:330`, rows H38, A15. New, high. Group G-107.
Text: "- id: vacate ... depends_on: [filing] ... cancel: ..." (`:330-333`) against "- id: bench  # the owner; sole terminal sink of the body" (`:409`).
Finding: nothing depends on `vacate` and it does not lead to `bench`, so the body has two terminal sinks. `loop-nodes.md:682-684`: a wait pauses the group "only as the body's sole terminal sink ... Any other placement is a load error". `plan-review.yaml` as designed fails `archon validate workflows`, standalone and as a block of `gauntlet-run`. G-11 and G-56 ruled what `vacate` reads, not the sink rule.

**3.10** `plan-review-design.md:149`, row H28. New, medium. Group G-104.
Text: "Every case but guard and cap is read only from a review written in this iteration; an iteration with no new review".
Finding: a failure resume restarts the loop at iteration 1 (`loop-nodes.md:945-947`) and a rerun continues from the files, so a review whose case never reached the owner loses it. An APPROVED review written before `report` fails: on resume `filing` owes the defense round N+1, `docket` returns none, and an Opus defense revises an approved plan. An APPROACH THE BENCH question is lost the same way; spec review shares it through `.shared/rounds.py`.

**3.11** `plan-review-design.md:87`, missing contract: `cite.py`'s exit contract (P20 area). New, medium. Group G-104.
Text: "# Plan file unreadable or unwritable: exit 2."
Finding: a defense turn that wrote no plan N fails node `cite`, which blocks `ready` (`none_failed_min_one_success`) and fails the run, where `state` already reports a missing plan as owed defense (`:119`) and spec review simply retries the speccer. Against `cite`'s own comment (`:349`) "exit 0, so a bad marker fails nothing". The resume then restarts the loop at iteration 1.

**3.12** `plan-review-design.md:400`, missing contract: the reporter role's inputs (R1, R2 cover only `defense.md` and `prosecutor.md`). New, medium. Group G-113.
Text: "prompt: <approved round $case.output.round>".
Finding: the reporter is `context: fresh` (`:397`) and its role (`:243`) reads `gauntlet/plans/<slug>.N.txt`, but no input names the slug or the task. With two tasks' round-3 files in the folder it must guess; `FENCE_ONCE` then blocks a correct rewrite, and the owner approves on a wrong `attention`. `spec-review-design.md:489` and `writing-design.md:513` pass the same round-only prompt.

**3.13** `plan-review-design.md:76`, row H29; missing contract: the cite-marker grammar (named missing by G-59). Matches G-20, medium. Group G-114.
Text: "# The path ends at the first \" | \" after \"[cite: \"; the quote ends at the last \"]\" of the marker's line, so a quote may" against "# A plan is cited when it holds no \"[cite:\" marker." (`:106`).
Finding: the ledger's cited test is a bare substring match; `cite.py`'s grammar has no case for a marker without " | " (`:81`). Such text (`[cite: a.py]`, or quoted code holding "[cite:", such as `spec-review-design.md:178`) can leave `cite.py` printing nothing unresolved while the ledger owes the defense forever, `repairs` at 0, up to cap 200. G-20's ruling (b) made `cite.py` exit 0 but did not align the two tests.

**3.14** `plan-review-design.md:140`, rows H28, P20. New, low. Group G-114.
Text: "others: the counts and the latest review's text".
Finding: a guard ask raised by `repairs >= REPAIRS` shows the counts and an older review, never the unresolved markers or their reasons; those exist only in `cite`'s stdout, and `<slug>.cite.N.txt` keeps only "unresolved <n>". The owner answers blind, and five more Opus repair turns pass before the next ask.

**3.15** `plan-review-design.md:144`, rows H28, A15. New, low. Group G-107.
Text: "# Cases, first that holds: none when next is vacant (vacate cancels in the next iteration, nothing asked);" against `:26` "so the loop never ends on `max_iterations`".
Finding: at iteration m >= 200, run only because the owner answered the cap ask, the twelfth LEADING review makes `docket` return none; with no answer Archon permits no iteration m+1 (`workflow-language.md:773`), so `vacate` never runs and the hearing fails on `max_iterations` instead of ending cancelled (`gauntlet-design.md:19`). An interaction of the G-55 and G-56 rulings.

**3.16** `plan-review-design.md:30`, rows P7, H36. New, low. Group G-110.
Text: "- **Slug**: kebab-case, `[a-z0-9]` runs joined by `-` (intake design), so no plan file `<slug>.N.txt` shares a name with any `<slug>.review.N.txt`".
Finding: the standalone input takes "the owner's own" task file (`:278`) and nothing checks its name. `--input task=gauntlet/tasks/a.review.md` gives slug `a.review`, whose plan 1 is slug `a`'s review 1, and the defense's `FENCE_DENY` `gauntlet/plans/*.review.*.txt` (`:255`) forbids it to write its own plan. A dotted slug (`v2.1-fix`) shares a prefix with `v2` in the stale set-aside (`:44`).

## 4. spec-review-design.md

Source: `reviews/conv3-spec-review.md` (6 findings: 6 new). 6 of 6 anchors hold.

**3.17** `spec-review-design.md:421`, rows A15, H38. New, high. Group G-107.
Text: "- id: vacate ... depends_on: [filing] ... cancel: ..." against "bench # the owner; sole terminal sink of the body" (`:498`).
Finding: the shape of 3.09 in spec review: two terminal sinks, a load error (`loop-nodes.md:682-684`). Spec review cannot load, so neither can `gauntlet-run`, which includes it. A15's documented verdict never checked `vacate`.

**3.18** `spec-review-design.md:112`, rows H29, S7, S10. New, high. Group G-105.
Text: "#   owed \"ended\": the latest ruling file's decision is an OwnerCase \"ends\"; the loop ends one iteration after it, and every".
Finding: no Profile field turns this off. Writing's revision profile declares `OwnerCase("SOUND", ..., ends="approve")` (`writing-design.md:103`) and runs more rounds after an approve ruling (`writing-design.md:148-150`). After one approved revision `rounds.state` reports `ended` for good; `stage.py` maps no `next` for it, and writing stalls until its cap.

**3.19** `spec-review-design.md:131`, rows H28, H29. New, medium. Group G-104.
Text: "#   Every case but guard and cap is read only from a review written in this iteration; an iteration with no new review".
Finding: with round = latest tried + 1 (`:104-110`), a rerun never asks again about a READY, INVALID or APPROACH THE BENCH review left unanswered: its round counts as tried and the speccer is owed a new block. The Why and Terms text says a rerun "continues the rounds from the files", but no file records a pending ask. Plan review has the same gap for an unanswered APPROVED.

**3.20** `spec-review-design.md:128`, row H28; missing contract: a bound on iterations that try no spec round. New, medium. Group G-115.
Text: "#   attempts >= 5; non_responsive >= 2; guard (stretch >= STRETCH or repairs >= 5); cap (profiles with iterations:".
Finding: `repairs` counts plans only (`:120`). A speccer turn that writes no block N, or an arbiter turn that writes no review, adds to neither stretch nor repairs, so only `cap` at 200 asks, each iteration resuming Opus sessions (and spikers). D-14 objection 1 was fixed for plans through `repairs` and left open for specs.

**3.21** `spec-review-design.md:364`, rows H15, H5. New, low. Group G-110.
Text: "plan: { description: Path of gauntlet/plans/approved/<slug>.txt, or \"\" when planning found no plan needed. }".
Finding: no `default: ""`. The standalone form (`:553`) is `--input task=<path> --input plan=<path>` and nothing tells the owner to pass `--input plan=` for a tests-only task; `workflow-language.md:1946-1947`: an input with no default "leaves it unset, and a body referencing it fails at the reference site". `open` fails at `$INPUTS.plan`.

**3.22** `spec-review-design.md:335`, rows A3, H27. New, low. Group G-108.
Text: "A named script, because an inline `script:` inside an `include:` block cannot read the block's inputs."
Finding: `workflow-language.md:1704-1708` gives every `script:` node, "whether the body is inline or a named file", `INPUTS_<UPPER_SNAKE>`; only the `$INPUTS.<name>` macro is a load error (A3). `plan-review-design.md:434-437` does the same job inline, and `gauntlet-design.md:28` states both hand-offs read `INPUTS_<NAME>`. Two contradicting statements of one rule.

## 5. worktree-cut-design.md

Source: `reviews/conv3-worktree-cut.md` (5 findings: 3 new, 2 matching). 5 of 5 anchors hold.

**3.23** `worktree-cut-design.md:227`, rows H7, H8, P3. Matches G-12, medium. Group G-108.
Text: "any agent or other node writing the tree's `gauntlet/tasks`, `gauntlet/plans` or `gauntlet/specs`" (with `:172` "# the only writer of the tree's gauntlet/tasks, plans and specs").
Finding: writing's `enter` writes the tree's `gauntlet/plans/approved/<slug>.rev<N>.txt` and `gauntlet/specs/approved/<slug>.rev<N>.txt` (`gauntlet-design.md` Homes row "Writing to the tree's `approved/` folders", copy-list bullet `:29`). G-12 rewrote only the copy list (B07); the cut design and `contracts.md` H7 ("the only writer") still state the old rule, so `enter` has no legal place.

**3.24** `worktree-cut-design.md:217`, rows H36, H16. Matches G-82, medium. Group G-109.
Text: "| Slug of the cut and the tree run | `gauntlet-run/scripts/pin.py`, handed to `gauntlet-tree` as input `slug` | any node, prompt or other script of the cut or the tree run deriving it |".
Finding: writing's hearing runs in the tree run as block `write`, and "the hearing's rounds.py calls derive theirs from INPUTS_TASK" (`writing-design.md:122`; `spec-review-design.md:96`). D-55's scoping to the tree run still forbids that derivation.

**3.25** `worktree-cut-design.md:100`, rows H1, H13-H16; missing contract: the `gauntlet-run` head's node list. New, low. Group G-108.
Text: "Its head (`name`, `inputs`, `worktree`, nodes `guard`, `intake`, `plan-review`, `spec-review`) is `gauntlet-design.md`'s." (and `:110`).
Finding: the list leaves out `env-check`, `dirty` and `stop`, which `gauntlet-design.md` gives (`:59-76`, Order step 1, Phase order row) since D-33, D-52 and D-54. A builder of cut step 3 may drop or reorder them.

**3.26** `worktree-cut-design.md:32`, rows P11, H9, A22. New, low. Group G-111.
Text: "a repository with no remote, or an unreachable one, cannot be cut, pinned branch or not; node `tree` fails with Archon's message".
Finding: no run-start node checks for an `origin` remote or a resolvable base branch (`:31`, `:200`), so a cause visible at run start surfaces only at phase 4, after the owner has answered every pause of intake, plan review and spec review: the pattern D-54 objection 2 rejected for the config check.

**3.27** `worktree-cut-design.md:83`, row H16. New, low. Group G-111.
Text: "# Not inside a git work tree, or HEAD has no commit: stderr names the checkout; exit 2." (and `:87` "exit 2 outside a git work tree").
Finding: no run reaches this branch: `guard` and `env-check` run before `pin` and need a work tree with a commit, and without the check `git branch` still fails the node. The branch and its test are work the sequence does not need (CLAUDE.md 1.3).

## 6. writing-design.md

Source: `reviews/conv3-writing.md` (12 findings: 6 new, 6 matching). 12 of 12 anchors hold. The reviewer's note: a scratch repository it made, `/tmp/tmp.xTDZRgjxE3` (124K), is still on the host because a hook blocks `rm -rf` for agents; no process was left.

**3.28** `writing-design.md:132-133`, rows S5, A9. Matches G-93, high. Group G-106.
Text: "Carried: a replaced cut's unrun waves, and of its run waves the blocks that ended blocked."
Finding: a contest or commit-failed block leaves uncommitted (or staged) edits that nothing in writing commits or removes. The carried waves run before the new cut's block that would own those paths, so `clean` blocks them again on every cut, the juror case reopens after each reply, and only DEFECTIVE or a manual edit ends it.

**3.29** `writing-design.md:152`, rows S5, A9. Matches G-93, high. Group G-106.
Text: "the juror's TESTS or CODE verdict starts the cut that carries the block".
Finding: a coder's leftover outside `tests/` can never sit in a test block's paths (`cut` rejects them, `:164-165`), and test waves run before code waves (`:130`), so a test block blocked by it is never unblocked. The fixture route "a coder's contest ruled `TESTS`, fixed, green" (`:539`) cannot reach green when the coder left an edit.

**3.30** `writing-design.md:150`, rows H29, S7, S10. New, high. Group G-105.
Text: "next from rounds.state: reviser owes: revise; reviewer owes: review."
Finding: `.shared/rounds.py` holds one hearing per folder (3.18). After the first approved revision round in `gauntlet/revisions/`, a later SPEC or PLAN verdict finds "a revision owed" (`:148`) but `rounds.state` returns `owed: ended`, which maps to no `next`. The divvy rule after it is never reached; the loop idles to `cap`, then asks on every iteration with no way to finish.

**3.31** `writing-design.md:549`, rows P11, F9, P19. Matches G-41, medium. Group G-116.
Text: "GAUNTLET_TEST_BRIEF_COMMAND: \"<the whole test command, printing one line per test: PASSED <id>, FAILED <id> or ERROR <id>, and no test source; for pytest, the command with --tb=no -rA -q>\"".
Finding: with `-rA` pytest prints `FAILED <id> - <message>`; `.shared/red.py` itself drops the text "from \" - \" on" (`gauntlet-design.md:344`), but `checks.py` returns the raw last 200 lines (`:82-83`). The coder sees `assert 7 == 5` from a test hidden by `FENCE_HIDE=tests` (D-36 objection 3 survived).

**3.32** `writing-design.md:70`, rows F8, F9, P14. New, medium. Group G-106.
Text: "#   git add -A -- <paths>, then git commit --only -m <message> -- <paths>; hooks run, never --no-verify."
Finding: a block's `paths` lists every file it may change (`:26`). git refuses a pathspec matching nothing ("fatal: pathspec ... did not match any files", exit 128, reviewer-checked in a scratch repository) and a commit with no change (exit 1). The tool returns only `exit=<n>` and hook names, the writer may never retry (`:315`), so each costs a juror dispatch and a new cut, and the staged edits block later blocks.

**3.33** `writing-design.md:315`, rows R12, F8, F9. New, medium. Group G-106.
Text: "outcome commit-failed, the tool's output as grounds. Never retry it." (same at `:339`).
Finding: a hook that fixes files and exits non-zero (a formatter, an end-of-file fixer) needs one more attempt. Here it becomes a juror case, a divvy and a fresh writer session, and the fixed files stay uncommitted, blocking the next block's `clean` (3.28).

**3.34** `writing-design.md:133`, row S5. Matches G-37, medium. Group G-106.
Text: "waves the blocks that ended blocked."
Finding: a block that ended `contest` or `commit-failed` is not carried, and the cut check "a step of an uncommitted earlier block missing from a code cut" (`:165-166`) binds only a code cut, while a TESTS verdict starts a test-only cut (`:38`). A contested code block's plan steps are never re-cut: with no test covering them the run seals `written` with plan steps unwritten.

**3.35** `writing-design.md:163`, rows S5, R7, F8, F9. New, medium. Group G-116.
Text: "# Writes <slug>.cut.<move>.json: { \"cause\", \"waves\", \"problems\" }. Problems, each one line: an empty wave; a code".
Finding: no problem rejects a code block in a cut answering TESTS, or a test block in a cut answering CODE. Each block's ruling is filled from its cut's cause (`:135`), and the juror's no-test-source rule binds only the CODE section (`:219-220`), so a coder can be handed the TESTS ruling quoting spec text and test source, against the Homes row at `:570`; the reverse breaks `:569`.

**3.36** `writing-design.md:156`, rows S5, R12. New, medium. Group G-117.
Text: "#   no cut since the latest cause, or the latest cut rejected: divvy. The cause is the latest verdict TESTS or".
Finding: after a PLAN verdict with a spec, the spec round closes last, so the divvyer's cause is the spec round alone. A "No change." spec round affects nothing; the divvyer cuts nothing or tests only (no problem fires: the coverage check binds code cuts), and the run seals `written` without the code the plan revision changed. `:41` "then a cut of the affected tests and code" has no input naming the plan revision.

**3.37** `writing-design.md:452`, row H33. Matches G-10, medium. Group G-118.
Text: "Else git add -A, git commit -F - with the message on stdin, hooks run: line 1 \"<slug>: final\", a blank line,".
Finding: D-19 objection 1 survived: on a dirty tree a conventional-commit `commit-msg` hook rejects the fixed message, the seal file records `exit=1`, the juror rules, cut and test follow, and `seal` fails the same way until `stalled`. No verdict can change the message (CLAUDE.md 1.4).

**3.38** `writing-design.md:566`, row H33. Matches G-10, low. Group G-108.
Text: "node `seal` for the final commit, only on a dirty tree, and its message, as `gauntlet-design.md` gives it".
Finding: `gauntlet-design.md:299` says "Node `seal` is the writing design's" and gives only `<slug>: final`; the body is only at `writing-design.md:451-455`. Each design points to the other for the message.

**3.39** `writing-design.md:180`, row H28. New, low. Group G-119.
Text: "#   lines of <slug>.iter.txt above \"base\", >= rounds.CAP); none."
Finding: `open` prints `base` (`:124`), but `docket(start)` takes none and nodes `case` (`:504`) and `docket` (`:520`) bind only `start`; plan review binds `base: $docket-in.output.base` (`plan-review-design.md:391`). `stage.py docket` must count every line or fail, breaking "since open".

## 7. landing-design.md

Source: `reviews/conv3-landing.md` (2 findings: 1 new, 1 matching). 2 of 2 anchors hold.

**3.40** `landing-design.md:234`, rows H22, H34, P9. New, high. Group G-104.
Text: "a resumed `repair` starts at iteration 1, its verdict, review, reply, changes and mended files kept".
Finding: `repair` runs only when `confirm` is red. On a resume `test-tree` runs on the tip that carries the mend and reuses retest's green file under the same key (`run.<head>.<tip>.txt`, `:66`, `:157`), so `confirm` and `repair` are skipped and `handoff` (`:220-222`) prints "Rerun on <head>: no new failure." though a `mended.*` file exists. A mend whose `review` crashed or was UNSOUND reaches the gate unreviewed, against the Homes rows "a mend that ends unreviewed" (`:526`) and the line at the gate (`:528`).

**3.41** `landing-design.md:353`, row H39. Matches G-68, low. Group G-108.
Text: "Landing re-mends at most twice, whatever the timing of the moves, in four rounds." (the D-47 amendment, "`merge` counts a move only when the checkout's `HEAD` is no longer an ancestor of the branch, in every round").
Finding: the gauntlet Homes row "Landing on the checkout" (`gauntlet-design.md:414`) still allows the merge only "in the round the owner answers land, with the checkout unmoved"; a checkout `HEAD` the branch still fast-forwards lands under landing and is a forbidden write under the gauntlet row.

## 8. Groups

Each group is one root cause (D-62). "Members" lists its findings, "Where" every design line the findings cite, "Statement" the cause with a scenario, "Options" each value; option (a) is the designs' current text, and an option marked (proposal) is offered for the ruling to accept or replace, not a value any design gives. Severity is the highest of the members'. "Route": load-bearing (a D-NN line in CONTEXT.md from D-66, reviewed by `/cad-decision-review` under D-05) when the ruling changes a `contracts.md` row a later phase builds against or contradicts a PROJECT, ROADMAP or REQUIREMENTS line; the ask-user seam otherwise. Each 3.NN id is in exactly one group (41 of 41). Every ruling is applied under D-61 (citations by node id or heading, one home per fact) and grepped under D-63.

**G-104** Resume and rerun work out what is owed from the files (owner's group 1; rows H28, H29, H22, H34, P9, P20; missing row: `cite.py`'s exit contract). High.
Members: 3.10, 3.11, 3.19, 3.40.
Where: `plan-review-design.md:149`, `:87`, `:119`, `:349`; `spec-review-design.md:131`, `:104-110`; `landing-design.md:234`, `:66`, `:157`, `:220-222`.
Statement: a failure resume restarts a `loop_group` at iteration 1 (`loop-nodes.md:945-947`) and a rerun has only the files. Three designs decide what is owed from something neither has: an owner case read "only from a review written in this iteration" (3.10, 3.19), a node failure on a missing plan the ledger already treats as owed (3.11), and a landing test file keyed to the tip, so a resumed run reuses retest's green result (3.40). Scenario: the mend is committed and retest green, `review` crashes; on resume `test-tree` reuses the green file, `confirm` and `repair` are skipped, `handoff` says "no new failure" and the gate offers an unreviewed mend.
Options: (a) as written; (b) (proposal) what is owed is read from the files alone: `docket`'s owner case comes from the latest tried round whose review has no ruling or guard record after it, whichever iteration wrote it, so a resume or rerun asks again; `cite.py` treats a missing plan file as nothing to resolve (exit 0, `{ "unresolved": [] }`, no cite line), the ledger owing the defense as `state` does at `:119`; landing owes repair while the latest `mended` file has no SOUND review after it, whatever `confirm` says, and `handoff` checks that before "no new failure"; (c) (proposal) as (b) for the hearings, but node `cite` is skipped by its `when:` when the filing's plan file is absent, and landing's resume reruns `review` on the latest unreviewed mend instead of re-entering `repair`.
Route: load-bearing (docket case contract H28, H29; landing H22, H34; a new `cite.py` exit row), D-66.

**G-105** `.shared/rounds.py` holds one hearing per folder (owner's group 2; rows H29, S7, S10). High.
Members: 3.18, 3.30.
Where: `spec-review-design.md:112`; `writing-design.md:103`, `:148-150`.
Statement: `owed "ended"` holds for good once the latest ruling's decision is an `ends` case. Writing runs a revision hearing per SPEC or PLAN verdict in one folder, `gauntlet/revisions/`, and its profile's SOUND case `ends="approve"`. Scenario: revision round 1 is approved and entered; a later SPEC verdict owes a revision, `rounds.state` says `ended`, `stage.py` has no `next` for it, and writing idles to `cap`.
Options: (a) as written; (b) (proposal) a hearing in a shared folder starts where its caller says: `rounds.state` takes the hearing's first round and reads `ended` only from a ruling at or after it; writing's `stage.py` passes the round after the latest closed one; (c) (proposal) writing's revision profile declares no `ends` case: `stage.py` closes a round by its own rule (an approve ruling, or SOUND on a "No change." round, `:148-150`) and calls `rounds.state` only for who owes within an open round; (d) (proposal) each revision hearing has its own folder, `gauntlet/revisions/<slug>.<k>/`, k the verdict's move.
Route: load-bearing (S7 API, H29 owed values; a path under (d)), D-67.

**G-106** Writing handles leftover edits and failed commits (owner's group 3; rows S5, A9, F8, F9, P14, R12). High.
Members: 3.28, 3.29, 3.32, 3.33, 3.34.
Where: `writing-design.md:26`, `:70`, `:130`, `:132-133`, `:152`, `:164-166`, `:315`, `:336`, `:339`, `:539`.
Statement: a block that ends `contest` or `commit-failed` leaves its edits, staged or not, in the tree, and nothing commits or removes them: every later block's `clean` sees them and ends blocked, a test block can never own a coder's leftover outside `tests/`, and the juror case reopens on each cut until `stalled` (3.28, 3.29). The commit tool fails over non-issues: a listed path that does not exist (exit 128), no change (exit 1), and a fixer hook needing one more attempt (3.32, 3.33). A `contest` or `commit-failed` block is not carried, so its steps are lost under a TESTS cut (3.34). Scenario: block A's ruff-format hook rewrites files and fails the commit; B is blocked; the juror rules TESTS; carried B is blocked again on every cut.
Options: (a) as written; (b) (proposal) the commit tool adds only the block's paths git lists as changed, makes no commit and returns exit 0 with "nothing" when none changed, and retries once when a failing hook changed files; a block that does not end committed has every uncommitted change in the tree restored to `HEAD` by `result` (staged and unstaged, its new untracked files removed; writers run one at a time under D-58, so every such change is the block's own), and `contest` and `commit-failed` blocks are carried as blocked ones are; (c) (proposal) as (b), but before the restore `result` saves the changes as `gauntlet/write/<slug>.leftover.<move>.patch`, named in the juror case's grounds.
Surface (destructive): (b) and (c) discard an agent's uncommitted edits. The restore runs in the tree only (`git -C <tree>`, never the checkout), and (c) keeps the edits as a file first.
Route: load-bearing (commit tool contract F8, F9, P14; S5 `state`; a path under (c)), D-68.

**G-107** The body-sink shape of `vacate` (owner's group 4; rows A15, H38, H28). High.
Members: 3.09, 3.17, 3.15 (the last added by the executor: the same root cause, `vacate` acting in the iteration after the vacancy; the owner's anchors were `plan-review-design.md:330` and `spec-review-design.md:421`).
Where: `plan-review-design.md:330-333`, `:409`, `:144`, `:26`; `spec-review-design.md:421-424`, `:498`; `gauntlet-design.md:19`.
Statement: `vacate` depends on `filing` and nothing depends on it, so each hearing body has two terminal sinks, a load error (`loop-nodes.md:682-684`): `plan-review.yaml`, `spec-review.yaml` and so `gauntlet-run` fail `archon validate workflows`. Because `vacate` cancels one iteration after the twelfth LEADING review, at iteration 200 or later no next iteration is permitted and the hearing ends on `max_iterations` (3.15).
Options: (a) as written (a load error); (b) (proposal) `vacate` leads to `bench`: `docket` also depends on `vacate`, with a trigger rule that runs when `vacate` is skipped, so every body node leads to the sink; 3.15 stays unless `cap` precedes "none when vacant", which re-opens G-56 (an ask whose answer the next iteration cancels); (c) (proposal) `vacate` leaves the body: `docket` reports a case `vacant` in the iteration the twelfth review lands, the group's `until_bash` ends the loop on it, and a `cancel:` node after the group fires on it, so the body keeps one sink and the cancel comes before any ask and before the bound (3.15 and G-56 both hold).
Route: load-bearing (A15 verdict and its citations, H38 node, H28 case), D-69.

**G-108** A fact restated outside its home, left at a pre-ruling or wrong value (rows H24, H7, H33, H39, H1, H13-H16, A3, H27, F1-F4, F9, F10; missing row: the `gauntlet-run` head's node list). Medium.
Members: 3.01, 3.02, 3.04, 3.08, 3.22, 3.23, 3.25, 3.38, 3.41.
Where: `gauntlet-design.md:409`, `:357-371`, `:23-34`, `:299`, `:414`; `worktree-cut-design.md:227`, `:172`, `:100`, `:110`; `spec-review-design.md:335`; `writing-design.md:566`; `landing-design.md:353`; `contracts.md` H7.
Statement: each fact has a home where its ruling was applied and a second statement elsewhere at the old or a wrong value. The failed record's Homes row forbids the reading its Home column grants to Clerk and intake's `ground`, and its fence clause reaches tree fences where no `gauntlet/failed/` exists (3.01, 3.02); the cut design and H7 make `copy-in` the only writer of the tree's plans and specs while writing's `enter` writes `rev<N>` files there (3.23); landing's D-47 move rule is missing from the gauntlet row "Landing on the checkout" (3.41); the cut design lists the head without `env-check`, `dirty` and `stop` (3.25); the seal message's home points each design to the other (3.38); about 33 copy-list `Resolved` line citations land on unrelated text (3.04, 3.08); spec review states an inline-script rule the docs and A3 contradict (3.22).
Options: (a) as written; (b) D-61 applied, one home per fact and a pointer by heading or node id everywhere else: the failed record's home is gauntlet's Homes row, its readers Clerk and intake's node `ground`, its Forbidden column naming the ledgers' script nodes and the checkout's fences outside `intake/` (3.01, 3.02, `:371` to match); the tree's approved files' home is the cut's Homes row, naming `copy-in` for the cut's copies and writing's `enter` for `rev<N>` files, H7 and the `copy-in` comment to match (3.23); the move rule's home is landing's node `merge`, the gauntlet row pointing to it (3.41); the head's home is the gauntlet design's head, the cut design pointing to it by heading without a list (3.25); the seal message's home is writing's node `seal`, the gauntlet sentence pointing to it (3.38); each copy-list `Resolved` names its ruling group and the design and heading or node id, which meets AC5's "ruling" arm (3.04, 3.08); the false reason at spec review's `handoff` goes, A3 its home (3.22).
Route: load-bearing (H7's "only writer" and H24's readers change), D-70.

**G-109** The slug after the phase that derives it (rows H36, H16, H17, H23). Medium.
Members: 3.03, 3.24.
Where: `gauntlet-design.md:102`, `:109`, `:116`, `:124`, `:401`; `landing-design.md:240`; `worktree-cut-design.md:217`; `writing-design.md:122`; `spec-review-design.md:96`.
Statement: `pin` derives the slug for the cut and the tree run, but writing's hearing calls `.shared/rounds.py`, which derives its own from `INPUTS_TASK` inside the tree run, which the D-55-scoped row forbids (3.24); the landing rounds read `$pin.output.slug`, an inner node of the cut phase, which the hand-off row forbids (3.03).
Options: (a) as written; (b) (proposal) one slug rule in `.shared/pin.py` (D-55's option c): `pin`, `rounds.py` and intake's `from-file` import its function, the Homes row names that function as the one derivation, and `cut` hands off `slug`, the landing rounds binding `$cut.output.slug`; (c) (proposal) the rows except them: the cut's slug row excepts `.shared/rounds.py`'s derivation from `INPUTS_TASK`, and the hand-off row excepts `$pin.output.slug` for the landing rounds.
Route: load-bearing (H17 hand-off field, H36), D-71.

**G-110** Standalone phase runs take inputs intake would have shaped (rows P7, H36, H15, H5). Low.
Members: 3.16, 3.21.
Where: `plan-review-design.md:30`, `:44`, `:255`, `:278`; `spec-review-design.md:364`, `:553`.
Statement: G-12 made plan and spec review standalone, but their inputs still assume intake: a task file not named in kebab-case gives a slug whose files collide with another slug's (3.16), and spec review's `plan` has no default, so a tests-only standalone run fails at `open` (3.21).
Options: (a) as written; (b) (proposal) the block's first script node refuses a task file name that is not kebab-case, exit 1 naming the file and the pattern, before any agent runs, and `plan` declares `default: ""`; (c) (proposal) `plan` declares `default: ""`, and the slug sentence names the standalone limit (the owner's file is named in kebab-case) with no check. Under G-109 (b) the shape check sits in the one slug function.
Route: ask-user seam (no row value changes: H36's derivation and H15's input names stay).

**G-111** The run-start checks test the working copy, not what the cut needs (rows H1, S2, S3, P11, H9, H16, A22). Medium.
Members: 3.05, 3.26, 3.27.
Where: `gauntlet-intake-design.md:59-60`, `:66-67`; `gauntlet-design.md:65-71`; `worktree-cut-design.md:31-32`, `:83`, `:87`, `:200`.
Statement: the tree is cut from `HEAD` and needs an `origin` and a base branch. The guard refuses a `.gitignore` with any uncommitted edit even when `HEAD`'s copy holds the rule (3.05); nothing at run start checks `origin` or the base branch, so their absence fails node `tree` after three phases of owner answers (3.26); `pin`'s exit 2 guards an input the run-start checks already exclude (3.27).
Options: (a) as written; (b) (proposal) the guard reads the rule from what the tree will hold: `HEAD`'s committed `.gitignore` (`git show HEAD:<file>`), `.git/info/exclude` or the global excludes file, whatever the working copy holds; `env-check` refuses a repository with no `origin` remote configured, or with neither `origin/HEAD` nor `worktree.baseBranch`, naming the fix (configuration only, no network call); `pin`'s exit-2 branch and its test case go; (c) (proposal) as (b) without the `origin` check: node `tree`'s failure stays the report and the run is resumed once the remote exists, as the cut design states now.
Route: load-bearing (S3 guard contract, D-53's ruled form; P11 `env-check`; H16 `pin`'s exits), D-72.

**G-112** Intake's "" stands for both "skipped" and "nothing" (rows P6, H3, A14; missing row: the source of `show`'s reply). Low.
Members: 3.06, 3.07.
Where: `gauntlet-intake-design.md:145`, `:147-150`, `:205`, `:231`, `:255`, `:257`.
Statement: `show` binds `turn`'s reply with `if_skipped: ""`, so a turn with nothing to say reprints Clerk's opening (3.06); `put`'s first branch drops a non-empty draft with slug "" and refuses nothing (3.07).
Options: (a) as written; (b) (proposal) `show` binds the reply with `if_skipped: "<skipped>"` as `latest` does and prints the opening only on `<skipped>`; `put`'s first branch splits: draft "" writes nothing, and a draft with slug "" writes nothing and refuses "The draft has no slug. Give one."
Route: ask-user seam (internal to intake; the refusal hand-off keeps its fields).

**G-113** The fresh reporter is not told whose round (missing row: the reporter role's inputs; R1, R2, R12). Medium.
Members: 3.12.
Where: `plan-review-design.md:243`, `:397`, `:400`; `spec-review-design.md:489`; `writing-design.md:513`.
Statement: three designs prompt a `context: fresh` reporter with a round number only, and its role reads `<slug>.N.txt`. Scenario: `a.3.txt` and `b.3.txt` both exist; the reporter guesses `b`, `FENCE_ONCE` blocks the correct rewrite, and the owner approves on a wrong summary.
Options: (a) as written; (b) (proposal) the reporter's prompt names the round file to read and the summary file to write, from the block's slug output and the round, and a row for the reporter's inputs is added; (c) (proposal) the prompt adds the task path and the role derives both paths from it.
Route: load-bearing (a role-input contract across three designs), D-73.

**G-114** Citation state lives only in `cite`'s stdout (rows H28, H29, P20; missing row: the cite-marker grammar, named missing by G-59; cites G-20). Medium.
Members: 3.13, 3.14.
Where: `plan-review-design.md:76`, `:81`, `:106`, `:140`; `spec-review-design.md:178`.
Statement: the ledger judges a plan cited by the substring "[cite:", while `cite.py` resolves a grammar with no case for a marker without " | ", so a malformed marker leaves the defense owed forever with no unresolved line and no guard (3.13); a guard ask shows counts and an older review, never which markers failed or why (3.14), because `<slug>.cite.N.txt` keeps only "unresolved <n>".
Options: (a) as written; (b) (proposal) `cite.py` is the one judge: any "[cite:" opens a marker, one without " | " is unresolved with its own reason, each unresolved marker and reason is appended to `<slug>.cite.N.txt`, the ledger's cited test reads that file's latest entry instead of the substring, and the guard's attention quotes it; (c) (proposal) only the grammar is aligned: `cite.py` counts a marker without " | " as unresolved; the attention is unchanged.
Route: load-bearing (H29's cited test, P20, the grammar row), D-74.

**G-115** Spec review has no bound on iterations that try no round (row H28; missing row: that bound). Medium.
Members: 3.20.
Where: `spec-review-design.md:120`, `:128`.
Statement: `guard` is `stretch >= STRETCH or repairs >= 5` and `repairs` counts plans only, so a speccer that writes no block, or an arbiter that writes no review, moves nothing until `cap` at 200, each iteration resuming Opus sessions.
Options: (a) as written; (b) (proposal) in every profile `guard` also holds on 5 iterations since the latest tried round or guard record (counted from `<slug>.iter.txt`), `repairs` kept for plans; (c) (proposal) as (b) for spec review only.
Route: load-bearing (H28 docket case), D-75.

**G-116** Coder blindness leaks through text nothing filters by kind (rows F9, P19, P11, S5, R7; cites G-41). Medium.
Members: 3.31, 3.35.
Where: `writing-design.md:82-83`, `:135`, `:163-166`, `:207-208`, `:219-220`, `:549`, `:569`, `:570`; `gauntlet-design.md:344`.
Statement: the brief example `--tb=no -rA -q` prints `FAILED <id> - <message>` and `checks.py` returns it raw (3.31); `cut` accepts a code block in a cut answering TESTS, and a block's ruling text comes from its cut's cause, so a coder can be handed spec text and test source (3.35).
Options: (a) as written; (b) (proposal) the coder-facing check mode cuts each line at the first " - ", the cut `.shared/red.py` makes, whatever the repository's command prints; `cut` lists a problem for a code block in a cut answering TESTS and a test block in a cut answering CODE; (c) (proposal) the brief example becomes a form that prints no message (for pytest `-v --tb=no -rN`, lines `<id> PASSED`, which `.shared/red.py`'s reading of the brief baseline must then match), and each block's ruling holds only its kind's section, mixed cuts staying allowed.
Route: load-bearing (F9 and P19 brief contract, S5 cut problems), D-76.

**G-117** After a PLAN verdict the divvyer is handed the spec round alone (rows S5, R12). Medium.
Members: 3.36.
Where: `writing-design.md:41`, `:156`, `:207-208`.
Statement: the divvy cause is "the latest verdict TESTS or CODE, or the latest closed round"; after a PLAN verdict with a spec the spec round closes last, and a "No change." spec round affects nothing. Scenario: plan round 3 is entered, spec round 4 closes "No change."; the divvyer cuts nothing, and writing seals `written` without the plan revision's code.
Options: (a) as written; (b) (proposal) after a PLAN or SPEC verdict the cause is every round closed since that verdict, oldest first, newline-separated; (c) (proposal) the cause is the verdict file, the divvyer reading the rounds it led to.
Route: load-bearing (S5 `state` field `cause`, R12 divvyer input), D-77.

**G-118** The seal's fixed message meets the repository's `commit-msg` hook (row H33; cites G-10). Medium.
Members: 3.37.
Where: `writing-design.md:452-455`; `gauntlet-design.md:299`.
Statement: on a dirty tree `seal` commits `<slug>: final` with hooks run; a conventional-commit hook rejects it, the juror rules, and `seal` fails the same way until `stalled`, with no verdict able to change the message.
Options: (a) as written; (b) (proposal) the repository may set the final commit's first line in its `.archon/config.yaml` env as `GAUNTLET_FINAL_SUBJECT` (`<slug>` substituted, default `<slug>: final`); (c) (proposal) a seal failure whose failing hook is `commit-msg` is an owner case (an ask naming the hook, options reply or leave), never a juror case.
Route: load-bearing (H33; a new `GAUNTLET_*` name under (b)), D-78.

**G-119** Writing's `docket` is not handed `base` (row H28). Low.
Members: 3.39.
Where: `writing-design.md:124`, `:180`, `:504`, `:520`; `plan-review-design.md:391`.
Statement: `cap` counts the lines of `<slug>.iter.txt` above `base` and `open` prints `base`, but `case` and `docket` bind only `start`.
Options: (a) as written; (b) `case` and `docket` bind `base: $open.output.base`, as plan review's `docket` binds `$docket-in.output.base` (`plan-review-design.md:391`), and `stage.py docket` reads `INPUTS_BASE`.
Route: ask-user seam (one design's bindings; H28 unchanged).

## 9. Rulings

Date: 2026-11-05. Option letters and texts are those of section 8. Route under D-79: the owner ruled every group through the ask-user seam; no `/cad-decision-review` ran; the D-NN lines of CONTEXT.md stay the record of the load-bearing groups and carry the ruling. The drafted edits are reviewed once, closed, before their commit (D-79).

Source, verbatim: G-104, the owner's ruling. G-106, the owner delegated it and named no option; the orchestrator took (c), because the restore discards an agent's edits. Every other group but G-115, the owner delegated to the recommended option ("fine whatever"). G-115, the owner at the round-3 checkpoint, first verbatim: "yes, if no progress is made, stop, have the Defense analyze the reason, and report it to the user."; then through the ask-user seam the answers "Fresh analyst everywhere" (one fresh read-only agent writes the explanation, the same role in plan review, spec review and writing; the defense, speccer and reviser sessions are not used) and "Pause and ask" (the bench asks the owner and shows the explanation; the reply is recorded as a guard record that binds the next turn; the hearing continues, it does not cancel). These replace the delegated (b) (`IDLE = 5`).

| Group | Route | D-NN | Ruling | Source |
|---|---|---|---|---|
| G-104 | load-bearing | D-66 | (b) | owner |
| G-105 | load-bearing | D-67 | (b) | owner delegated to the recommended option |
| G-106 | load-bearing | D-68 | (c) | owner delegated, no option named; orchestrator took (c) |
| G-107 | load-bearing | D-69 | (c) | owner delegated to the recommended option |
| G-108 | load-bearing | D-70 | (b) | owner delegated to the recommended option |
| G-109 | load-bearing | D-71 | (b) | owner delegated to the recommended option |
| G-110 | ask-user seam | - | (c) | owner delegated to the recommended option |
| G-111 | load-bearing | D-72 | (b) | owner delegated to the recommended option |
| G-112 | ask-user seam | - | (b) | owner delegated to the recommended option |
| G-113 | load-bearing | D-73 | (b) | owner delegated to the recommended option |
| G-114 | load-bearing | D-74 | (b) | owner delegated to the recommended option |
| G-115 | load-bearing | D-75 | (b) as changed: docket case `idle` on the first iteration that tried no round, drew no answer and left the round file as it found it (`IDLE = 1`) in every loop, writing's included; a fresh read-only analyst writes the reason to `<slug>.idle.K.md`; the bench shows it; the reply is a guard record and the hearing continues | owner |
| G-116 | load-bearing | D-76 | (b) | owner delegated to the recommended option |
| G-117 | load-bearing | D-77 | (b) | owner delegated to the recommended option |
| G-118 | load-bearing | D-78 | (b) | owner delegated to the recommended option |
| G-119 | ask-user seam | - | (b) | owner delegated to the recommended option |
