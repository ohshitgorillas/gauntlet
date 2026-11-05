# Phase 1 pass-1 rulings

Date: 2026-11-05. Option letters are those of `REVIEW-pass1.md` section 10.

Authority. The owner ruled G-12 and G-45 through the ask-user seam. For the other 48 groups the owner answered: "This is utterly illegible to me, I have no clue what I am being asked to judge, and highly suspect that most of these are not questions but actually just asking for permission to take the obvious route." Under CLAUDE.md 3.2 ("Take the proper fix unasked, and name each such choice in the report"), the main session took the proper fix for those 48. Each is named below as `main session (3.2)`. The 27 load-bearing ones go through `/cad-decision-review` under D-05.

| Group | D-NN | Ruling | By |
|---|---|---|---|
| G-01 | D-11 | (b) the documented route: MCP `env` values expanded from Archon's process environment (`mcp-servers.md:192-194`), never `command`/`args`; the test fences F8-F11 move to it | main session (3.2) |
| G-02 | D-12 | (b) every fence config sets no `CLAUDE_PROJECT_DIR` (PROBES.md P2: a config value wins), stated as a pack rule and pinned by a fence test; the false "overrides" clause is removed | main session (3.2) |
| G-03 | D-13 | (c) the speccer gets no Bash; the spiker alone holds Bash, under a sandbox whose `denyWrite` lists the paths it must not write (PROBES.md P1). The Homes rows `gauntlet-design.md:348` and `spec-review-design.md:277` are reworded to say Bash reads are not fenced | main session (3.2) |
| G-04 | D-14 | (c) the cite check runs as a script node and the defense holds no Bash; every `Task` in `allowed_tools` becomes `Agent` in all designs | main session (3.2) |
| G-05 | D-15 | (b) plan review's ledger is the shared `Profile` form on `.shared/rounds.py` with prefix verdict matching; plan-review step 5 needs spec-review step 2 | main session (3.2) |
| G-06 | D-16 | (b) spec-review step 7 stands, needs plan-review steps 4 and 5; the plan review design is amended to use the shared `screen` and drop its own screener role and fixtures | main session (3.2) |
| G-07 | D-17 | (c) each step that writes `gauntlet-tree.yaml` lists only the fields it adds | main session (3.2) |
| G-08 | D-18 | (b) the home rule allows `$INPUTS.<name>` in prompts, `bash:` and `with:` | main session (3.2) |
| G-09 | - | (b) a timeout already present in the brief or head run is not red | main session (3.2) |
| G-10 | D-19 | (a) every `seal` makes the `<slug>: final` commit (`--allow-empty` when the tree is clean), listing the plan summary and the summaries of approved revision rounds only; gauntlet step 9 is dropped as a restatement | main session (3.2) |
| G-11 | D-20 | (b)+(c) writing drops `vacate`; plan review computes vacancy in `filing`, before `defend`, and asks the owner before cancelling; the gauntlet design states the route for a cancelled child run | main session (3.2) |
| G-12 | D-21 | (b) intake, plan review and spec review are usable standalone and as blocks of `gauntlet-run` (`PROJECT.md:31`, `ROADMAP.md:61`); the designs are changed to match, reversing their "Not for direct use" descriptions and giving each standalone phase what it needs to run on its own; the copy list is rewritten to what the designs then state | owner |
| G-13 | - | (a) `enter` strips the `Revises:` and `Answers:` lines when copying | main session (3.2) |
| G-14 | D-22 | (a) node ids `juror` and `review`; `gauntlet-design.md:184` reworded | main session (3.2) |
| G-15 | - | (a) intake's Homes row is scoped to intake's own nodes | main session (3.2) |
| G-16 | D-23 | (b) Clerk's write fence is narrowed to the chosen slug's file, and a script node checks the slug is free before the first turn | main session (3.2) |
| G-17 | - | (b) a second guard message for a tracked file, naming `git rm --cached` | main session (3.2) |
| G-18 | - | (b) a byte-identical occupied target is taken as the task | main session (3.2) |
| G-19 | - | (c) Clerk outputs the slug on the turn it writes the draft | main session (3.2) |
| G-20 | - | (b) `cite.py` exits 0 and prints unresolved markers; the ledger owes the defense until none remain | main session (3.2) |
| G-21 | D-24 | (a) `filing` and `ready` pass `start: $docket-in.output.start` in both blocks | main session (3.2) |
| G-22 | D-25 | (b) the shared core's `close`; the ending ruling is written before the loop ends; plan review's `enter` and `handoff` read `$close.output.file` | main session (3.2) |
| G-23 | D-26 | (a) the block's first node prints the slug from `INPUTS_TASK`; later nodes bind `$<node>.output.slug` | main session (3.2) |
| G-24 | - | (b) plan review's sworn-in reviewer reads the latest plan on the arbiter's rule | main session (3.2) |
| G-25 | D-27 | (b) the ledger returns "already approved" and the block hands off the existing approved file with no hearing | main session (3.2) |
| G-26 | D-28 | (b) the `until_bash` forms `loop-nodes.md:667-697` give: reference assigned unquoted, guarded, never reading a wait its own `when:` can skip | main session (3.2) |
| G-27 | - | (a) `report` passes READY or INVALID | main session (3.2) |
| G-28 | D-29 | (a) `cut` takes `branch` from `$tree.output`; pin's predicted name is checked against it | main session (3.2) |
| G-29 | D-30 | (a) the full baseline file and its pass-through fields are dropped; `baseline` writes the brief file only and the Homes row names it | main session (3.2) |
| G-30 | D-31 | (b) no node `timeout` on test nodes; the inner `timeout -k` bounds the process | main session (3.2) |
| G-31 | D-32 | (a) a blank test command is refused, checked by the guard at run start before any paid phase | main session (3.2) |
| G-32 | D-33 | (b) the cut asks the owner when the checkout has uncommitted or untracked changes | main session (3.2) |
| G-33 | D-34 | (a) `pin` prints the checkout root | main session (3.2) |
| G-34 | - | (b) `copy-in` fails naming a missing input | main session (3.2) |
| G-35 | - | (b) the narrower rule of `gauntlet-design.md:343` replaces `worktree-cut-design.md:197` | main session (3.2) |
| G-36 | - | (b) each juror trigger is bounded by "newer than the latest verdict"; a `stalled` or `cap` reply opens no juror case | main session (3.2) |
| G-37 | - | (b) `state` carries the replaced cut's unrun waves into the next cut | main session (3.2) |
| G-38 | - | (b) `cap` counts loop iterations, so the ask fires before 200 | main session (3.2) |
| G-39 | - | (b) `ask` is false when `end` is set | main session (3.2) |
| G-40 | D-35 | (a) `docs/testing.md` added to the test writer's `FENCE_READ` | main session (3.2) |
| G-41 | D-36 | (b) a coder-facing mode of the check tool returns test names and messages only | main session (3.2) |
| G-42 | - | (a) `record` passes `move: $state.output.move` | main session (3.2) |
| G-43 | - | (a) `state` prints `cause` for `revise` too | main session (3.2) |
| G-44 | - | (b) a resume always reruns `test-tree` on the rebased tip | main session (3.2) |
| G-45 | - | new option (c): when the checkout has moved past the branch's base, landing rebases the branch onto the checkout's new head, reruns the tests (and the repair when red) and then lands. Mechanism (owner, at the plan-3 Task 2 structural checkpoint, choice 1 of 3): when `land` finds the checkout moved, it starts a second tree run that runs block `mend` only (rebase, tests, repair) on the existing tree, then asks the land-or-leave gate again; the check repeats if the checkout moves again. Amended by the owner after the executor checkpoint of 2026-11-05 (an unbounded repeat needs a `workflow:` node in a `loop_group` body, rejected at load: `workflow-language.md:2543-2544`): landing re-mends at most 2 times, each round an `include`d block under its own id that checks the checkout, re-mends on a move and asks the land-or-leave gate again; a third move stops the run, naming the move | owner |
| G-46 | - | (b) `pose` ends "done" only on a `committed` mend; the UNSOUND list names an uncommitted mend | main session (3.2) |
| G-47 | - | (b) `retest` runs only after a committed mend | main session (3.2) |
| G-48 | - | (b) `retest`/`recheck` gated on a committed mend; `review` gated on recheck not red | main session (3.2) |
| G-49 | - | (b) `pose` always prints the latest run file and review file | main session (3.2) |
| G-50 | D-37 | (b) `repair`'s ask adds `retry` and `accept`; the Homes row `landing-design.md:373` lists all three ask conditions | main session (3.2) |
