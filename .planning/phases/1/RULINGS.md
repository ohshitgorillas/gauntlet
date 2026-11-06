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

## Pass 2 rulings (REVIEW-pass2.md, G-51 to G-103)

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
