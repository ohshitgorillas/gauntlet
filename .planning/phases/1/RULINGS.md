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

## Pass 3 rulings (REVIEW-pass3.md, G-104 to G-119)

Date: 2026-11-05. Option letters are those of `REVIEW-pass3.md` section 8; section 9 there holds the same rulings with their routes.

Authority. Under D-79 the owner rules every group and no `/cad-decision-review` runs. The owner ruled G-104. For G-106 the owner delegated the ruling and named no option; the orchestrator took (c), because the restore discards an agent's edits. For 13 of the other 14 groups the owner delegated to the recommended option ("fine whatever"); the owner then changed G-115 at the round-3 checkpoint (first iteration that tried no round, IDLE = 1, a fresh analyst's reason shown to the owner; the answers "Fresh analyst everywhere" and "Pause and ask", given through the ask-user seam). The drafted edits get one closed review before they are committed (D-79).

| Group | D-NN | Ruling | By |
|---|---|---|---|
| G-104 | D-66 | (b) what is owed is read from the files alone: docket's owner case from the latest tried round's review with no ruling or guard record after it; `cite.py` exit 0 on a missing plan; landing owes repair while the latest `mended` file has no SOUND review after it, and `handoff` checks that before "no new failure" | owner |
| G-105 | D-67 | (b) `rounds.state` takes the hearing's first round and reads `ended` only from a ruling at or after it; writing's `stage.py` passes the round after the latest closed one | owner delegated (recommended option) |
| G-106 | D-68 | (c) the commit tool adds only changed paths, answers "nothing" on none and retries once after a hook changed files; `result` saves `gauntlet/write/<slug>.leftover.<move>.patch`, named in the juror case, then restores the tree to `HEAD` after a block that did not commit; `contest` and `commit-failed` blocks carried | owner delegated, no option named; orchestrator (restore discards an agent's edits) |
| G-107 | D-69 | (c) `vacate` leaves the body: `docket` case `vacant`, the loop ends on it through `until_bash`, and a `cancel:` node after the group fires on it | owner delegated (recommended option) |
| G-108 | D-70 | (b) D-61 applied with the homes REVIEW-pass3.md G-108 names | owner delegated (recommended option) |
| G-109 | D-71 | (b) one slug function in `.shared/pin.py` imported by `pin`, `rounds.py` and `from-file`, named the one derivation; `cut` hands off `slug`, the landing rounds binding `$cut.output.slug` | owner delegated (recommended option) |
| G-110 | - | (c) `plan` declares `default: ""`; the slug sentence names the standalone limit (the owner's file is named in kebab-case), no check | owner delegated (recommended option) |
| G-111 | D-72 | (b) the guard reads the rule from what the tree will hold; `env-check` refuses a repository with no remote configured, the remote `worktree.remote` names (`origin` when unset), configuration only; `pin`'s exit 2 goes. Amended by the D-79 review: `env-check` checks no base branch, because Archon takes it from `--base`, then `worktree.baseBranch`, then the stored default branch, then the remote's live symbolic HEAD (`ls-remote --symref`, `docs/reference/archon/cli.md:1746`), and never reads the local `refs/remotes/origin/HEAD` (`docs/reference/archon/cli.md:438-455`) | owner delegated (recommended option) |
| G-112 | - | (b) `show` binds the reply `if_skipped: "<skipped>"`; `put` refuses a draft with slug "" ("The draft has no slug. Give one.") | owner delegated (recommended option) |
| G-113 | D-73 | (b) the reporter's prompt names the round file and the summary file; a row for the reporter's inputs | owner delegated (recommended option) |
| G-114 | D-74 | (b) `cite.py` is the one judge; each unresolved marker and reason appended to `<slug>.cite.N.txt`, whose latest entry the ledger's cited test reads and the guard's attention quotes | owner delegated (recommended option) |
| G-115 | D-75 | (b) as changed by the owner at the round-3 checkpoint, which answered "Fresh analyst everywhere" and "Pause and ask" after the first answer ("yes, if no progress is made, stop, have the Defense analyze the reason, and report it to the user."): docket case `idle` holds on the first iteration that tried no round, drew no answer and left the round file as it found it (`IDLE = 1`) in every profile, writing included (there, an iteration that writes no file), counted from `<slug>.iter.txt` lines holding round, owed, guard-record count and repairs; node `why` has one fresh read-only agent, the `analyst`, the same role in plan review, spec review and writing (not the defense, the speccer or the reviser), write the reason to `<slug>.idle.K.md`; the bench asks the owner and shows it; the owner's reply is recorded as a guard record that binds the next turn, and the hearing continues, it does not cancel | owner |
| G-116 | D-76 | (b) the coder-facing check mode cuts each line at the first " - "; `cut` rejects a block of the other kind | owner delegated (recommended option) |
| G-117 | D-77 | (b) after a PLAN or SPEC verdict the cause is every round closed since it, oldest first | owner delegated (recommended option) |
| G-118 | D-78 | (b) `GAUNTLET_FINAL_SUBJECT` in the repository's env sets line 1 (`<slug>` substituted, default `<slug>: final`) | owner delegated (recommended option) |
| G-119 | - | (b) `case` and `docket` bind `base: $open.output.base`; `stage.py docket` reads `INPUTS_BASE` | owner delegated (recommended option) |

## D-79 review of the pass-3 drafts

Date: 2026-11-05. One closed review read the whole draft diff of G-104 to G-119 (D-79 step 3): per group, does the edit close its scenario, and does it add a high or medium defect. It wrote no amendment and reported no low finding. The findings were never written to a file; this section is their record, as the orchestrator gave them.

Clean, no change: G-106, G-107, G-108, G-109, G-110, G-112, G-113, G-114, G-116, G-117, G-119.

Medium fixes applied (D-79 step 4):

| Group | Fix |
|---|---|
| G-104, hearings | "with no agent turn" deleted from the fixture lines of `plan-review-design.md` and `spec-review-design.md`, and the matching claims in the plan review ledger text deleted |
| G-105 | `since`, `attempts`, `non_responsive` and `stretch` (and owed `owner`) are counted from `first` (`spec-review-design.md`, `.shared/rounds.py` `state`) |
| G-104, landing | in `hear`, the group's first iteration is a retry only when no review of n or higher exists for the latest mend (`landing-design.md`, node `hear`) |
| G-111 | the manual answers it, so no experiment ran (CLAUDE.md 1.9). `docs/reference/archon/cli.md:438-455` gives the order Archon takes the base branch from: `--base`, then `worktree.baseBranch`, then the registered codebase's stored default branch, then the remote's live symbolic HEAD (`ls-remote --symref` on `worktree.remote`, `cli.md:1746`); it never reads the local `refs/remotes/origin/HEAD`. The base-branch and `origin/HEAD` clauses are deleted from `gauntlet-design.md` (node `env-check`, Homes row "The run-start checks"), `worktree-cut-design.md` (the "Base branch" bullet, the "Remote" bullet, the `baseBranch` comment) and `contracts.md` (H1, P11); `env-check` checks the remote `worktree.remote` names, `origin` when unset. D-72 and the G-111 row above are amended the same way |

G-118, checked and unchanged: no repository on this host runs commitlint or a `commit-msg` body line limit, so `GAUNTLET_FINAL_SUBJECT` (b) stands as drafted.

## Owner-control ruling (D-80 to D-96; the owner-control design, approved at `ae9c7d0`)

Date: 2026-11-07. Authority. The owner approved `docs/superpowers/specs/2026-11-07-owner-control-design.md` and, in the regather of this phase, confirmed D-80 and ruled D-81 to D-96. D-81 makes the application of that design one owner ruling: one commit holds the seven designs, `contracts.md`, the planning lines it contradicts (D-96, D-02) and this section. No group below is re-ruled; each row says what the owner-control design does to a ruling already made. The drafted edits got one closed review before the commit (D-79, D-84); its answers are in "D-79 review of the owner-control draft".

Moot groups (D-81): the owner-control design rewrites the subject of the group, so the ruling is closed and is not re-ruled.

| Group | D-NN | Status | By |
|---|---|---|---|
| G-14 | D-22 | moot: node `juror` goes with the juror (D-87, D-88); the mend's agent nodes are `amicus`, `mend-code`, `mend-tests`, `review` and `final` (`contracts.md` H34) | D-81 (owner-control) |
| G-16 | D-23 | moot: Clerk writes no file and `items.py` writes the draft state and the item file (D-86; `contracts.md` F5, S8) | D-81 (owner-control) |
| G-19 | - | moot: Clerk's `{ slug, reply, draft }` protocol goes with the task file (D-86) | D-81 (owner-control) |
| G-36 | - | moot: the juror triggers go; the amicus cases and their triggers are the writing design's Terms "Amicus" (D-87) | D-81 (owner-control) |
| G-45 | - | moot as to the land-or-leave gate: block `land` holds no gate, the owner's land is the answer at the review before landing (D-92); the re-mend run, `gauntlet-remend`, and the two-re-mend bound stand (D-47, D-48 carried below) | D-81 (owner-control) |
| G-51 | D-38 | moot: node `fail` and the failed record go (D-89); the item-file hash set-aside in the hearing ledgers stands on the item file | D-81 (owner-control) |
| G-52 | D-39 | moot: node `fail` and `gauntlet/failed/<slug>.txt` go (D-89) | D-81 (owner-control) |
| G-67 | D-46 | moot as to its file list: the re-mend run's `copy-in` skips the first mend's direction, amicus, final, review, reply, grounds, changes, mended and rebased files (`contracts.md` H40, P9) | D-81 (owner-control) |
| G-73 | D-50 | moot: the refusal channel is `items.py` mode `state` and node `latest` (D-86) | D-81 (owner-control) |
| G-75 | - | moot: `put` is re-specified in `items.py`, refusing a slug taken by another run's item file or unlike the run's first | D-81 (owner-control) |
| G-87 | - | moot: the juror goes; a block outside its paths is an amicus case (D-87) | D-81 (owner-control) |
| G-93 | D-58 | moot as to the juror's verdict starting the cut that carries a blocked block; `max_parallel: 1` and the `blocked` case stand (D-58 carried below) | D-81 (owner-control) |
| G-106 | D-68 | moot as to the juror case: the leftover patch is named in the amicus case's files (D-68 carried below) | D-81 (owner-control) |
| G-112 | - | moot: intake's `show` binds the reply `if_skipped: ""` with the opening reply from `clerk` (D-86; `contracts.md` A14) | D-81 (owner-control) |
| G-117 | D-77 | moot as to the juror's verdict as the divvy cause; the cause after a revision is every round closed since the latest direction, oldest first (D-77 carried below, owner ruling 2026-11-07) | D-81 (owner-control) |

Rulings that stand (D-81), not moot and not void:

| Group | D-NN | Status | By |
|---|---|---|---|
| G-05 | D-15 | stands, owner ruling 2026-11-07: plan review's ledger is the shared `Profile` form on `.shared/rounds.py` with prefix verdict matching (`contracts.md` S9); the owner-control design changes only the key it hashes, the item file's hash in place of the task hash (`plan-review-design.md`, ledger table) | owner (2026-11-07) |

Void rulings (D-85), recorded against their groups. A void ruling is not re-ruled; the owner-control design supersedes it.

| Ruling | Group | Status | By |
|---|---|---|---|
| D-22 | G-14 | void: node ids `juror` and `review` (the juror goes) | D-85 (owner-control) |
| D-37 | G-50 | void: `repair`'s `retry` and `accept` options; the mend's `ask` offers discuss, rework-code, rework-tests, again, back-to-planning, leave and (case `review`) land | D-85 (owner-control) |
| D-38 | G-51 | void as a `fail` rule; its hearing-ledger half (set aside on a changed item file) stands | D-85 (owner-control) |
| D-39 | G-52 | void: `fail` records no second verdict | D-85 (owner-control) |
| D-58, after-application amendment | G-93 | void: "the juror's verdict starts the cut that carries the block"; the owner's `tests` or `code` direction does | D-85 (owner-control) |
| D-59, juror half | G-98 | void: the juror reading the changes file; the `mended` file for `mend-review` stays and so does the `changes` file for the amicus and the review before landing | D-85 (owner-control) |
| D-13, `gauntlet/failed/` clause | G-03 | void: no failed-task folder exists, so no fence hides or reads it | D-85 (owner-control) |
| D-43, `gauntlet/failed/` clause | G-61 | void: as D-13's clause | D-85 (owner-control) |

Carried rulings (D-85), re-anchored on the amicus case and the direction file.

| Ruling | Group | Re-anchor | By |
|---|---|---|---|
| D-47, D-48 | G-68, G-69 | four landing rounds, `land` to `land-4`, two re-mends at most; the owner meets a new review in each re-mend run | D-85 (owner-control) |
| D-57 | G-88 | carried unrun waves, one wave per iteration, each wave with its own direction text | D-85 (owner-control) |
| D-58 | G-93 | a `blocked` outcome is an amicus case, its grounds the paths outside the block | D-85 (owner-control) |
| D-68 | G-106 | the leftover patch named in the amicus case's files; the commit tool and the restore stand | D-85 (owner-control) |
| D-78 | G-118 | `GAUNTLET_FINAL_SUBJECT` sets line 1 of the final commit; each stage seals with its own subject (D-93) | D-85 (owner-control) |
| D-76, second half | G-116 | carried, owner ruling 2026-11-07: `stage.py cut` rejects a code block in a cut answering a direction `tests` and a test block in a cut answering a direction `code`, keyed on the direction in place of the verdict; the first half (the coder-facing check mode cutting at " - ") stands | owner (2026-11-07) |
| D-77 | G-117 | carried, owner ruling 2026-11-07: after a revision the divvy cause is every round closed since the latest direction, oldest first, re-anchored on the direction file in place of the verdict | owner (2026-11-07) |

Other rulings (D-85): D-19 (G-10) and D-23 (G-16) were superseded before owner-control (`contracts.md` H33, F5). D-49 (G-72) and D-50 (G-73) fall with the intake rewrite (D-86). D-20 (G-11) and D-21 (G-12) stand.

Decisions applied by the commit (D-80 to D-96): D-80 the design is folded in as edits and stays an approved source; D-81 one ruling, one commit; D-82 `contracts.md` edited, R7 and R8 removed, H3, H13, H14, H21, H24, H25, H31, H34, P6, S8, S12 and the other affected rows rewritten; D-83 the "left to the builder" items settled in the designs with rows H42 to H51 (the item file, the amicus, the direction file, the review before landing, stages, the escalation key, the plan-step grammar, the paths mark, the stage marker, the back-to-planning command); D-84 the round-4 brief; D-85 the old rulings above; D-86 intake on the item file; D-87 writing without the juror; D-88 landing without `mend-juror`; D-89 back to planning in place of `fail` and `kill`; D-90 every task-path contract on the item file; D-91 the two scope checks and the stage marker; D-92 the review before landing in the tree run; D-93 unrolled stages; D-94 the escalation key and its carrier; D-95 the amicus as one shared included block, `amicus/`; D-96 the planning lines (REQUIREMENTS RUN-01, RUN-06 to RUN-13, ROLE-01, ROLE-02, the Out of Scope rows and LAND-01; ROADMAP phases 3 to 7; PROJECT.md's Active and Out of Scope lines and its shared-layer line).

## D-79 review of the owner-control draft

Date: 2026-11-07. One closed review read `git diff HEAD` of the whole draft at `78b9ff6` (D-79 step 3, the diff half of round 4, D-84): seven reviewers, one per design, `contracts.md` and the planning lines with the designs they cite. Per decision that touches a design: does the edit close what the decision states (Q1), and does it add a high or medium defect (Q2). Each reviewer's return is saved under `reviews/d79-oc-<design>.md`. Reviewer text is data. Only high and medium fixes were applied (D-79 step 4), each as the smallest edit the reviewer named, and four points went to the owner (below).

Clean, Q1 yes and Q2 none, no change: D-80 (gauntlet, intake, landing, spec-review, worktree-cut, writing), D-81 (all seven), D-83 (gauntlet, intake, spec-review, worktree-cut, writing), D-85 (gauntlet, intake, landing, spec-review), D-86 (gauntlet, plan-review, spec-review), D-87 (gauntlet, writing), D-90 (all seven), D-91 (gauntlet, intake, landing, worktree-cut, writing), D-92 (gauntlet, writing), D-93 (landing, plan-review), D-94 (plan-review, worktree-cut), D-95 (gauntlet, landing, writing), D-96 (all seven).

### Answers that were not clean, and the fix applied

| Design | Decision | Answer | Fix applied |
|---|---|---|---|
| intake | D-86 Q1 (a) | no: `put` checks only the points Clerk lists; an empty `$ARGUMENTS` leaves the check checking nothing | `put` refuses "a sentence of the statement quoted by no point"; with an empty `$ARGUMENTS` the owner's first reply becomes the statement (`INPUTS_REPLY`, `points` from the turn that settles it) |
| intake | D-86 Q1 (b) | no: no refusal for a change to an item already approved | `put` refuses "a changed field of an approved item" |
| intake | D-86 Q1 (c) | no: a deferred file with the same slug always conflicts with the first run's item file at `from-file` | the deferred file is `gauntlet/deferred/<slug>-later.md` (intake, gauntlet, `contracts.md` H42) |
| intake | D-86 Q2 high | `until_bash` reads `phase` before the last `answer` is applied, so `answer` waits on a done state with no options and fails | `when: "$latest.output.phase != 'done'"` on node `answer` |
| intake | D-86 Q2 medium | a refused `put` leaves no trace for mode `state`, so the owner approves a stale proposal | `put` "recording only the refusal, which mode state reads" |
| intake | D-86 Q2 medium | mode `check` applies the no-code rule to the owner's own file, so the back-to-planning rerun stops at `from-file` | "the cap and the no-code rule excepted" (mode `check`, node `from-file`) |
| intake | D-85 Q2 | the rewrite brings back the defects D-49 and D-50 closed | the three fixes above |
| gauntlet | D-82, D-88 Q2 medium | the mend's node `review` is named `mend-review` in the node list (`gauntlet-design.md`, H34) | `review` in both node lists |
| gauntlet | D-89 Q2 high | `back.py` leaves `gauntlet/write/` and `gauntlet/revisions/` records of landed stages, so the rerun's `record` meets differing files | `back.py` also moves the slug's files in `gauntlet/write/` and `gauntlet/revisions/` into `stale/<slug>.<m>/` (Back to planning, `back.py`, H24) |
| gauntlet | D-89 Q2 medium | `back` binds `items: $cut.output.items`, a tree path | `items: $spec-review.output.items` |
| gauntlet | D-93 Q2 high | stage k's copy of `<slug>.iter.txt` grows, so `record` exits 1 on any plan of 2 or more stages | `record` copies `gauntlet/write/<slug>.*` except `<slug>.iter.txt` (`landing-design.md` node `record`, P5) |
| landing | D-82 Q2 medium | H34 still says `repair` runs when `confirm` is red or `unreviewed` | the clause deleted from H34 |
| landing | D-88 Q2 high | a `discuss` answer turns a red case into `review` in iteration 2 | `pose` keeps the case and its files after a `discuss` answer |
| landing | D-88 Q2 high | `recheck` binds `head` from a skipped `test-head` | `head: { from: $test-head.output.file, if_skipped: "" }` |
| landing | D-88 Q2 medium | the mender roles are written for a red only | `mend-code`: "Do what the owner's direction says, changing code only; make pass any failing tests a run file names"; `mend-tests`: ", and only where the checkout's HEAD changed what they test" deleted |
| landing | D-89 Q1 | no: `handoff` names `amicus.<n>.md` with the direction's n, a file that does not exist | `amicus.<m>.md`, m the highest n below that direction's |
| landing | D-92 Q1 | no: the `final` answer never reaches the owner | `pose` lists `gauntlet/mend/<slug>.final.<k>.txt` for case `review` |
| landing | D-92 Q2 medium | `final` runs again on every `discuss` turn | `&& $LOOP_PREV.ask.output.decision != 'discuss'` on node `final` |
| plan-review | D-80 Q1 | no: no citation of the owner-control design | "(owner-control design, section 3)" after Plan grammar, "(section 4)" after Escalation rules |
| plan-review | D-87 Q1 | no: the analyst role is said to be shared with writing | " and writing" deleted |
| plan-review | D-89 Q2 medium (two) | the defense never reads the plan whose first stages landed; the prosecutor gets no direction | the defense reads the highest-numbered `stale/<slug>.<m>/approved/<slug>.txt`; the prosecutor reads the direction file when given and the prompt carries `direction $INPUTS.direction` |
| plan-review | D-91 Q2 medium (three) | a plan with no step lines raises no problem; `scope` skipped after a resume leaves no marks for `enter`; no marks for an entered plan revision | "no step line" and "a line starting `Step ` that does not match the grammar" are problems; `scope` depends on `[filing, cite]` with `none_failed_min_one_success`; the Homes row names `scope.py` over an entered plan revision |
| plan-review | G-05 | no: the subject of G-05 survives the draft | owner ruling 3 below |
| spec-review | D-89 Q2 medium | "moved the slug's files there" points at `gauntlet/back/` | "into `<folder>/stale/<slug>.<n>/`" |
| spec-review | D-94 Q1 | no: a standalone spec review reads a stale or absent rules file | spec review has its own bash node `rules`, `swear-in` depends on it; the sentence about the earlier plan review's file is deleted; H47 aligned |
| worktree-cut | D-82 Q2 medium | H7 pins "from stage 2" | "from stage 2" deleted in H7 |
| worktree-cut | D-89, D-93 Q2 high | `copy-in` skips the earlier records at stage 1 of a replanned run | "From stage 2 ($INPUTS.stage above 1)" and "stage 2 and later only" deleted; the Homes row says "when present" |
| writing | D-82 Q2 medium | A30 says `until_bash` ends the group on any other decision | "any other decision ends the discussion" |
| writing | D-83 Q2 medium | an empty-text `rework-code` on a flaky red reaches `seal` over a red run | "no run since the latest wave or cut: test." |
| writing | D-85 Q1, Q2 medium | cause after a revision is the latest closed round | owner ruling 1 below |
| writing | D-87 Q2 high | `$case.output.move.md` reads field `move`, then `md` | `case` outputs `record` (the amicus record's tree path); `record: $case.output.record` |
| writing | D-87 Q2 medium | `discuss` is offered on the idle case, which `state` does not hold open | `discuss` only when state's next is amicus |
| writing | D-93 Q2 medium | the divvy prompt carries no stage | `stage $INPUTS.stage` in the divvy prompt |
| writing | `stage.py cut` | the rule rejecting a block of the other kind than the direction is carried by no decision | owner ruling 2 below; the lines stay as drafted |

### Owner rulings on the four open points (2026-11-07)

| Point | Ruling | Applied |
|---|---|---|
| 1. Writing D-85 Q2 (D-77) | D-77(b) is carried, re-keyed on the direction | `writing-design.md` (state, divvy cause): "after a revision, every round closed since the latest direction, oldest first"; D-77 moved from the void table to the carried table above; CONTEXT.md D-85 lists D-77 as carried; G-117's moot row says so; `contracts.md` S5 |
| 2. `stage.py cut` | D-76's second half is carried on the direction: a code block in a cut answering direction `tests`, and a test block in a cut answering direction `code`, are rejected. The reviewer's deletion is not applied | `writing-design.md` `stage.py cut` stays as drafted; D-76 second half moved to the carried table; CONTEXT.md D-85; `contracts.md` S5 |
| 3. G-05 | stands, not moot: D-15 stands with the item hash in place of the task hash | G-05 left the moot table for the "Rulings that stand" table; G-05 dropped from D-81's "at least" list in CONTEXT.md |
| 4. Intake D-86 | every fix the intake review names is applied, the empty-`$ARGUMENTS` rule included | see the intake rows above |

Two choices of the executor, named under CLAUDE.md 3.2. The `INPUTS_REPLY` carrier for the empty-`$ARGUMENTS` rule is the smallest wiring the reviewer's sentence needed (`talk`'s `put` gets `reply:` and `points: $turn.output.points`); the reviewer named the rule, not the carrier. The deferred-file rename was applied at every place that names the file, not only at the two the reviewer cited.

## Pass 4 rulings (REVIEW-pass4.md, G-120 to G-128)

Date: 2026-11-08. Option letters are those of `REVIEW-pass4.md` section 2; section 3 there holds the same rulings with their routes.

Authority. Under D-79 the owner rules every group and no `/cad-decision-review` runs. The owner ruled all nine groups in one question through the ask-user seam, each group with option (b) as the recommendation, and answered verbatim: "All as recommended". The drafted edits get one closed review before they are committed (D-79).

| Group | D-NN | Ruling | By |
|---|---|---|---|
| G-120 | D-99 | (b) `docket` answers `none`, nothing asked, when `owed` is `ended`, listed with `vacant` ahead of every owner case and every bound | owner ("All as recommended") |
| G-121 | D-100 | (b) `owed` is `owner` also for an unanswered `guard` or `idle` ask, read from the counts and from `<slug>.idle.K.md` (`cap` not carried); writing's `enter` runs off the approve ruling on file | owner ("All as recommended") |
| G-122 | - | (b) the leftover patch is written with `git diff --binary HEAD` and `--binary` on each new-file diff | owner ("All as recommended") |
| G-123 | - | (b) writing's `record` binds `decision` and `text` in the string form `$LOOP_PREV.bench.output.<field>`, as plan review's `record` does | owner ("All as recommended") |
| G-124 | D-101 | (b) the home states `close`'s `file` and `summary` as the bare `<slug>.N.txt` and `<slug>-summary.N.md` | owner ("All as recommended") |
| G-125 | D-102 | (b) an entered plan revision gets scope marks (`marks` of `scope.py`, run by writing's `stage.py state` into `gauntlet/write/<slug>.scope.rev<M>.txt`), read by the stage cut, the divvyer and the review before landing | owner ("All as recommended") |
| G-126 | D-103 | (b) node `final` stays; the final file joins the amicus's file list in a new node `files` after `final` | owner ("All as recommended") |
| G-127 | - | (b) gauntlet `## Order` steps 3 and 4 swapped so no step needs a later one; the plan and spec review `guard.ts` steps name the intake design's step 3 | owner ("All as recommended") |
| G-128 | D-104 | (b) the mend saves its uncommitted edits as `gauntlet/mend/<slug>.leftover.<k>.patch` and restores the tree to the committed tip, as writing does | owner ("All as recommended") |

Two choices of the executor, named under CLAUDE.md 3.2. G-125: the proposal said `enter` runs `scope.py`; a pack script is reached only by `mcp:` or a `.shared/` import (gauntlet-intake design, Homes row "Reaching a pack file from a run in any repository"), so `scope.py`'s function `marks` is imported by writing's `stage.py state` and the marks sit in `gauntlet/write/`, where `enter` (the only writer of `approved/`) is not a second writer. G-121: "unanswered" for `idle` is read as the file `<slug>.idle.K.md` for K one above the guard-record count, which an answer makes stale.

Closed review of the pass-4 draft (`reviews/closed-4.md`): Q1 yes for G-120 to G-128; Q2 one medium, G-125 (a text-only step revision carried no `Stage <k>:` line, so `marks` put the step in stage 1). Fixed inside ruled option (b): `plan-review-design.md` Terms "Plan grammar" (the one home) now requires the line above every step a revision holds, and `scope.py` `marks(..., revision=True)` takes a revision's stage lines as given; `writing-design.md` `stage.py` and the reviser prompt point to it.

## Pass 5 rulings (REVIEW-pass5.md, G-129 to G-131)

Date: 2026-11-08. Option letters are those of `REVIEW-pass5.md` section 2; section 3 there holds the same rulings with their routes.

Authority. Under D-79 the owner rules every group and no `/cad-decision-review` runs. The owner ruled each group in its own question through the ask-user seam and answered verbatim, option (b) each time. The drafted edits get one closed review before they are committed (D-79).

| Group | D-NN | Ruling | By |
|---|---|---|---|
| G-129 | D-105 | (b) the change is judged where only the agent could have made it: writing's `result` saves and restores every uncommitted change after a wave, the mend checks the tree once after the mender and `pose` reads that check, and each brief-command run ends with the two restore commands | owner ("(b) Check after agent (Recommended)") |
| G-130 | D-106 | (b) `stage.py result` writes `stage` into each blocks record, and node `changes` prints this stage's blocks files, which `final` is handed in place of the glob | owner ("(b) Stage field (Recommended)") |
| G-131 | D-107 | (b) the home states that the set-aside keeps `approved/` as a subfolder, `test_back.py` pins it, and the defense reads `<slug>.txt` and each `<slug>.rev<N>.txt` of the stale `approved/` folder in order of N | owner ("(b) Layout + revisions (Recommended)") |

Choices of the executor, named under CLAUDE.md 3.2: G-129, the mend's check is a new node `leftover` (`when` the iteration ran a mender, before `retest`), which takes over the patch and restore D-104 placed in `pose`; G-130, `stage` sits in every block record of a wave and `changes` prints the matching files as `blocks`; G-131, the layout sentence sits in `runtime-model-design.md`, "Hearing state". Closed-review fixes (reviews/closed-5.md), named under 3.2: the committed block's leftover patch reaches the owner through the review before landing (`changes` prints `leftovers`, `final-review` says per patch whether the branch carries the work), not through a new amicus case; `fence/checks.py` restores only the paths a run made and leaves every path dirty before the run, so no writer edit is deleted and the owner's rejected option (c) is not used.

## Pass 6 rulings (REVIEW-pass6.md, G-132 to G-137)

Date: 2026-11-08. Option letters are those of `REVIEW-pass6.md` section 2; section 3 there holds the same rulings with their routes. After this round no pass-7 read runs (D-108).

Authority. Under D-79 the owner rules every group and no `/cad-decision-review` runs. The owner ruled all six groups in one question through the ask-user seam, each group with option (b) as the recommendation, and answered verbatim: "All as recommended". The drafted edits get one closed review before they are committed (D-79).

| Group | D-NN | Ruling | By |
|---|---|---|---|
| G-132 | D-109 | (b) `next` is `vacant` as soon as twelve LEADING reviews exist, whoever owes the round; otherwise the author when `owed` is the author; otherwise the reviewer slot | owner ("All as recommended") |
| G-133 | - | (b) the commit tool asks `git status --porcelain -z -uall -- <listed paths>`, so a new file in a new directory is a change | owner ("All as recommended") |
| G-134 | D-110 | (b) a new node `settle` of the mend, before `rebase` and `always_run`, saves a failed mender's uncommitted edits as a patch and restores the tree; `pose` counts it as `commit-failed` | owner ("All as recommended") |
| G-135 | - | (b) node `baseline` ends with the two restore commands on every exit path, the fifth site of the brief-command restore | owner ("All as recommended") |
| G-136 | - | (b) `record` writes `direction.N.md` with N the next free move, the N of the amicus record `docket` named, and `close` hands off that record | owner ("All as recommended") |
| G-137 | - | (b) with `plan` "" the first cut's cause is the approved spec file and its approved revisions, stage 1 only | owner ("All as recommended") |

Choices of the executor, named under CLAUDE.md 3.2: G-134, the patch is `gauntlet/mend/<slug>.settle.<s>.patch` (`s` numbered as `hear` numbers its files, settle patches counted), not `leftover.0.patch`, so a second failure resume cannot overwrite the first, `settle` prints the owed patch (nothing numbered above it) on every resume so a resume that failed before `pose` loses nothing (the one medium of `reviews/closed-6.md`), and `settle` touches nothing while a rebase is in progress in the tree, so the owner's conflict resolution is not restored away; G-136, N is one above the highest move because the amicus record is no move; G-137, the cause is `INPUTS_SPEC` and its approved revisions as tree paths. G-132 and G-133 pins sit in the fixtures and suite descriptions the options name.

Closed review of the pass-6 draft (`reviews/closed-6.md`): Q1 yes for G-132 to G-137; Q2 one medium, G-134 (a settle patch written on a resume that then failed before `pose`, a `rebase` conflict, was lost to the next resume, which found a clean tree and printed `file` ""). Fixed inside ruled option (b): `runtime-model-design.md` "Commit model", "The mend's uncommitted edits" (the one home) numbers the patch as `hear` numbers its files and keeps it owed until a numbered file above it exists; `settle` prints the owed patch on every resume; `landing-design.md` node `hear` counts settle patches in `n`; the fixture `settled` pins the second resume.
