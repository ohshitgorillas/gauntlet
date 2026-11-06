# Phase 1 decision reviews (D-11 to D-37)

Run on 2026-11-05 under D-05 (`/cad-decision-review` refute-then-adjudicate). One `cad-reviewer` refuted each D-NN line at the session default model; no cross-model reviewer is configured. The main session ruled each objection after grounding it against the files cited. Amendments are applied with the ruling in Task 2.

## D-22 (G-14)
- Objection 1: `ROADMAP.md:94` (Phase 7 criterion 2) checks for a node `mend-juror`. Under ruling (a) the node id is `juror` (`landing-design.md:109`), and `mend-juror` is only its `command:`.
  - Grounding: `sed -n 94p .planning/ROADMAP.md` shows "reaches `mend-juror`"; `landing-design.md:109` shows `- id: juror`.
  - Ruling: survives.
  - Amendment: reword `ROADMAP.md:94` to "reaches node `juror` (command `mend-juror`)" in the same commit as the design edits (D-02).

## D-11 (G-01)
- Objection 1, blocker: under (b), MCP `env` expands only from Archon's process environment, and codebase env reaches Codex nodes only (`mcp-servers.md:192-194`). The test command's home is the repository `env:` (`worktree-cut-design.md:186`, `:199`). Every writer, mender and juror is `provider: claude` (`writing-design.md:232`). So `$GAUNTLET_TEST_COMMAND` expands empty and `fence/checks.py:33-34` exits.
  - Grounding: `mcp-servers.md:192-194` (vendored doc) and `fence/checks.py:33-34` confirm both halves.
  - Ruling: survives.
- Objection 2, high: the only way to give (b) a value is a host-global export, a second home for the command that can differ from the repository's.
  - Ruling: survives; the same gap as objection 1.
- Objection 3, high: `${GAUNTLET_TEST_TIMEOUT:-900}` is not an expansion form the guide documents (`mcp-servers.md:210-212`), so the designed default cannot be written.
  - Ruling: survives.
- Amendment (replaces the ruling): the fences take no test value from MCP `env` and no `sh -c` launch line. A bash node, which sees the repository `env:`, writes the resolved values (test command, brief command, timeout with its 900 default, test base) once per tree run to a fixed file under `gauntlet/`. `fence/checks.py` reads that file from a path fixed relative to its root. F8-F11 launch as plainly as F1-F7, and the repository `env:` stays the one home. This uses only documented features: bash nodes see the repository env, and fence configs use plain `command`/`args`.

## D-12 (G-02)
- Objection 1, high: a test that "pins every config sets none" must read the pack's real config files, which `docs/testing.md` rule 15 (line 45) and rule 3 (line 16) forbid.
  - Grounding: confirmed at both lines.
  - Ruling: survives.
- Objection 2, medium: other routes can set the variable: an `sh -c` launch line, or a value inherited from Archon's environment (unmeasured).
  - Ruling: partial. The D-11 amendment removes `sh -c` launch lines; the inherited route stays open.
- Amendment (replaces the ruling with option (c)): `fence/files.py` `_root()` (line 32) and `fence/checks.py` refuse to start, exit 2, when realpath(`CLAUDE_PROJECT_DIR`) differs from realpath(cwd). PROBES.md P2 shows the two are equal when nothing sets the variable. This is tested through the scripts' entry points with `tmp_path`, inside policy, and covers every route. The false "overrides" clause is still removed from the designs.

## D-16 (G-06)
- Objection 1, high: with the plan review design amended to `include: screen`, spec-review step 7 rewrites an already-final file, leaving two writers and a wasted dispatch (1.3).
  - Ruling: survives.
- Objection 2, high: plan-review step 5 says "Needs steps 2 to 4" (`plan-review-design.md:436`). Under the amendment its YAML includes `screen`, which only spec-review step 5 builds, so includes fail at load.
  - Ruling: survives.
- Objection 3, medium: plan review's fixtures stub a bare `screen` node (`plan-review-design.md:338`). After the include they report missing and unused stubs, and dropping them would remove the only test of the SCREENED route.
  - Ruling: survives.
- Amendment: drop spec-review step 7. Plan-review step 5 builds `screen` as `include: screen` and needs spec-review step 5. Plan-review step 4 writes no screener role or fence. Plan review's fixtures are rewritten to stub the included node ids, and the SCREENED route fixture is kept.

## D-17 (G-07)
- Objection 1, high: ruling (c) does not say which step owns `brief`, and gauntlet:4 (`gauntlet-design.md:146`, `:155-157`), writing:8 (`writing-design.md:502`) and gauntlet:10 (`:372`) each add it.
  - Ruling: survives.
- Objection 2, medium: under D-30, writing:8 has one binding left on `gauntlet-tree.yaml`, so a separate dispatch for it is waste (1.3). gauntlet:4's `write` node also leaves `brief` unbound in the meantime.
  - Ruling: survives.
- Amendment (replaces the ruling with option (a)): gauntlet step 4 owns `paths` (including `brief`) and `write`'s `brief:` binding. Writing step 8 makes no edit to `gauntlet-tree.yaml`. Gauntlet step 10 lists only what it adds.

## D-29 (G-28)
- Objection 1, high: a check against `$tree.output.branch` runs only after the whole tree run, writing and mend included, so a wrong start point costs every paid phase.
  - Grounding: the tree's inputs (`worktree-cut-design.md:138-143`) carry no branch.
  - Ruling: survives.
- Objection 2, medium: the ruling does not say the check fails the run, and a mismatched branch replays foreign history at the mend.
  - Ruling: survives.
- Amendment: `gauntlet-tree` takes pin's `branch` as an input. Its first node compares it with `git branch --show-current` and fails the run, naming both, before copy-in. `cut` reads `branch` from `$tree.output`.

## D-30 (G-29)
- No objections. Grounding of the decision's own claims:
  - Codebase claim, "nothing reads the full baseline": confirmed. `grep -n 'baseline/<slug>.txt'` over the designs finds only the writer (`worktree-cut-design.md:49`, `:159`, `:200`), a pass-through field (`gauntlet-design.md:222`), and writing's note that it is unparsed (`writing-design.md:14`).
  - Library or API claim: the decision rests on none.

The rulings below were each grounded against the cited lines, which the main session read with `sed -n` or grep. An objection marked survives is grounded and changes the ruling, as the amendment states.

## D-13 (G-03)
- Objection 1, high: under (c), removing Bash from the `file` node also removes it from its inline spiker (PROBES.md P3: "Bash is disabled for this session, in subagents as well as here").
  - Ruling: survives.
- Objection 2, high: `denyWrite` cannot confine writes to scratch inside an unknown checkout. Deny beats allow (P1, run 2), and unlisted siblings stay writable (P1, run 1).
  - Ruling: survives.
- Objection 3, medium: only absolute paths were probed, and no substitution is documented in `sandbox:`.
  - Ruling: survives.
- Objection 4, medium: `filesystem.denyRead` is used in `docs/reference/archon/spike-sandbox-workflow.yaml:15` and is a deny list of known paths.
  - Ruling: survives.
- Objection 5, low: the speccer's fence still reads `approved/` and `scratch/`.
  - Ruling: survives.
- Amendment: the speccer and spiker share one node's Bash (P3). Confinement is by sandbox:
  - `denyWrite` the checkout root;
  - `allowWrite` a scratch folder outside the checkout;
  - `denyRead` `gauntlet/failed` and `gauntlet/specs/approved`;
  - `FENCE_HIDE` widened to `gauntlet/failed:gauntlet/scratch:gauntlet/specs/approved`.
  The path forms are probed before this ruling is applied (PROBES.md P4).
  Probe result (PROBES.md P4): the relative forms `'.'` and `'gauntlet/failed'` confine nothing, and no variable is substituted in `sandbox:` values. Only an absolute literal path works, which an unknown checkout cannot supply. The amendment cannot stand as written. P6 found that `./` and glob forms confine nothing either. Archon cannot name the run's checkout in `sandbox:` paths. The fence server can, because it resolves every path against `CLAUDE_PROJECT_DIR`, which Claude Code sets to the agent's cwd (PROBES.md P2).
- Amendment (replaces the sandbox amendment above):
  - Neither the speccer nor the spiker holds Bash, and neither node takes `sandbox:`.
  - Both read and write through `fence/files.py`. The spiker gets `FENCE_WRITE=gauntlet/scratch/<slug>`. `FENCE_READ` lists the folders each one may read, and leaves out `gauntlet/failed`, `gauntlet/specs/approved` and `tests/`; the speccer's list also leaves out `gauntlet/scratch`. Unlisted folders cannot be read, so `FENCE_HIDE` is not needed.
  - The spiker runs its experiments through a fence tool with cwd `gauntlet/scratch/<slug>`, as `checks.py` runs the test command. This replaces `spec-review-design.md:17` ("`checks.py` does not serve them").
  - Homes rows `gauntlet-design.md:348` and `spec-review-design.md:277` keep their fence wording, because no Bash read is left open.
  - Grounding: `mcp-servers.md:278` and `:492` document `mcp` plus `allowed_tools` with no Bash as "Sandbox to MCP only", where the agent "cannot touch the filesystem or run shell commands". `fence/test_files.py` and `fence/test_files_write.py` cover the fence's path confinement. PROBES.md P2 shows the root is the agent's cwd.

## D-14 (G-04)
- Objection 1, high: with no Bash, every bad marker costs one iteration that tries no round, and nothing counts those iterations, so the loop can reach 200 with no ask (`plan-review-design.md:121`, `:26`).
  - Ruling: survives.
- Objection 2, medium: the defense is not told which markers failed (`:306`).
  - Ruling: survives.
- Objection 3, low: `Task` is still named in Homes rows and role texts (`writing-design.md:530`; `plan-review-design.md:165`, `:170`; `spec-review-design.md:24`, `:239`, `:243`).
  - Ruling: survives.
- Amendment:
  - `defend`'s prompt carries `$LOOP_PREV.cite.output` (the unresolved markers and their reasons).
  - A repair-only iteration counts toward the stretch guard, so the owner is asked after 5.
  - `Task` becomes `Agent` everywhere it names the tool.

## D-15 (G-05)
- Objection 1, high: a prefix match still exits 1 on `**Verdict:** REJECTED` and on case slips, and a written-once review wedges every resume.
  - Ruling: survives.
- Objection 2, medium: plan-review step 3 still writes the standalone ledger, unordered against spec-review step 2.
  - Ruling: survives.
- Amendment:
  - The core matches verdicts after stripping markdown markup, case-insensitively.
  - A first line that still names no known verdict is an owner case (ask), never exit 1.
  - Plan-review step 3 writes no ledger body. Plan review's ledger is the Profile on the core, needing spec-review step 2.

## D-18 (G-08)
- Objection 1, medium: `$state.output.round.txt` reads `txt` as a nested field (`workflow-language.md:617`).
  - Ruling: survives; settled by the D-26 amendment, under which the ledger prints file paths.
- Objection 2, low: script nodes already get block inputs as `INPUTS_<NAME>` (`workflow-language.md:1703-1707`).
  - Ruling: survives.
- Amendment (narrows (b)): `$INPUTS.<name>` may appear in `with:` only on `include:` and `workflow:` nodes. Script nodes read block inputs from `INPUTS_<NAME>`, and the redundant bindings are dropped.

## D-19 (G-10)
- Objection 1, high: the target repository's commit-msg hooks run on the final commit's agent-written message, and no juror verdict can fix a rejected message.
  - Grounding: `/home/atom/dev/hqptuner/.git/hooks/commit-msg` exists.
  - Ruling: survives.
- Objection 2, medium: no step builds the ruled changes once step 9 is dropped, and seal cannot compute which rounds were approved (`gauntlet-design.md:356`).
  - Ruling: survives.
- Amendment (replaces the ruling with (b)):
  - `seal` makes no final commit on a clean tree.
  - The landing gate shows the plan summary and the approved revision summaries. `state` lists the approved rounds.
  - `landing-design.md:205` and `gauntlet-design.md:350` are reworded.
  - Gauntlet step 9 is dropped.

## D-20 (G-11)
- Objection 1, high: an ask before the vacancy cancel cannot change the outcome. The slot count survives a ruling (`plan-review-design.md:106`, `:27`).
  - Ruling: survives.
- Objection 2, medium: spec review has the same post-repair vacancy, and `state` is shared.
  - Ruling: survives.
- Objection 3, high: writing still gets `vacant` from the shared core with no node to act on it, so it idles to `max_iterations`.
  - Ruling: survives.
- Amendment:
  - `Profile.retire` becomes optional and writing sets none, so writing never sees `vacant`.
  - In plan review and spec review, the ledger reports the vacancy in `filing` (before any repair turn). `vacate` reads `$filing.output` and cancels without asking.
  - The gauntlet design states the route for a cancelled child run.

## D-21 (G-12), owner's ruling
- Objection 1, high: a standalone approval cannot be consumed by a later `gauntlet-run`; it re-hears, then fails at `enter`.
  - Ruling: survives; answered by the D-27 amendment (reuse of a fresh approval).
- Objection 2, medium: a standalone phase needs `worktree: enabled: false`. Under `include:` that key is dropped with a load-time warning, shown by `archon validate workflows` and `archon workflow list --json` on every load (`workflow-language.md:1569`, `:2969`).
  - Grounding: confirmed at both lines.
  - Ruling: does not survive. Probed on 2026-11-05 (PROBES.md P7): `archon validate workflows` reports the composer and the block `ok`, and `parseWarnings` is `null` for both in `archon workflow list --json`. The only trace is one stderr log line per load, `"msg":"include.workflow_level_fields_dropped"` with `"droppedFields":["worktree"]`. No gate reads it. The key's drop is intended, because `gauntlet-run` declares its own `worktree:`. Nothing goes to the owner.
- Objection 3, medium: a direct-use description lets the chat router pick a single phase for a whole-run request (`workflow-language.md:1740`).
  - Ruling: partial. Descriptions can name `gauntlet-run` as the whole-run pick.

## D-23 (G-16)
- Objection 1, blocker: a node output cannot reach an MCP server's env, so the fence cannot be narrowed per slug.
  - Ruling: survives.
- Objection 2, high: `FENCE_ONCE` blocks Clerk from editing its own draft (`fence/files.py:217`, `:232`).
  - Ruling: survives.
- Objection 3, high: no node runs between the choice of slug and the write.
  - Ruling: survives.
- Objection 4, medium: a failing slug check has no route the owner can clear.
  - Ruling: survives.
- Amendment: Clerk writes no file. Each turn outputs the draft text and the slug. A script node writes `gauntlet/tasks/<slug>.md`, refusing a slug taken by another run and feeding the refusal to Clerk's next turn. Clerk's fence becomes read-only. This uses documented features only.

## D-24 (G-21)
- Objection 1, medium: `docket` also needs `start`, because its cap counts `run_rounds`.
  - Ruling: survives.
- Objection 2, medium: a `with:` binding from a sealed loop body to an outer node is undocumented. `loop-nodes.md:617-619` allows outer `$nodeId.output` refs "in body prompts" only.
  - Ruling: survives.
- Amendment: every in-loop ledger mode (`state`, `docket`) takes `start`. The binding form is probed before this ruling is applied (PROBES.md P5). If the probe fails, `docket-in` writes the start to the ledger's own run file and every mode reads it.
  Probe result (PROBES.md P5): a body `with:` binds from an outer node, so the ruling (a) stands and the fallback is not needed. P5 bound the whole `$outer.output`. The field form `$docket-in.output.start` is the generic binding that `workflow-language.md:547` documents.

## D-25 (G-22)
- Objection 1, high: no node can follow `bench`, so the ending ruling is written one iteration late.
  - Ruling: survives; settled by the D-28 amendment (an `ended` state that runs script nodes only).
- Objection 2, medium: `handoff` reading `$close.output.file` is wrong or dead.
  - Ruling: survives.
- Amendment: only `enter` reads `$close.output.file`. `handoff` builds the approved path as spec review's `handoff.ts` does.

## D-26 (G-23)
- Objection 1, high: YAML-built names like `<slug>.$filing.output.round.txt` parse as nested reads and break the bindings, and `plan-review-design.md:419` forbids nodes building file names.
  - Ruling: survives.
- Objection 2, low: block inputs already reach every script as `INPUTS_TASK`.
  - Ruling: survives.
- Amendment (replaces the ruling): `.shared/rounds.py` derives the slug from `INPUTS_TASK` itself, and `state` prints the round file paths. `cite` and `screen` bind `$filing.output.file` and `$ready.output.file`. No slug output or slug binding exists.

## D-27 (G-25)
- Objection 1, high: with (b), a rerun after a DEFECTIVE ruling reuses the defective plan.
  - Ruling: survives.
- Objection 2, medium: a stale approval is reused after the task changes.
  - Ruling: survives.
- Amendment: an approval records the hash of the task file it was approved against. The ledger reuses an approval only while that hash matches. When `fail` writes a DEFECTIVE record, it moves the slug's approved plan and spec aside, so a rerun re-hears them.

## D-28 (G-26)
- Objection 1, high: an unconditional `bench` asks every round.
  - Ruling: survives.
- Objection 2, high: reading `$LOOP_PREV.bench` costs a paid round after approval.
  - Ruling: survives.
- Objection 3, medium: (b) did not choose between those two forms.
  - Ruling: survives.
- Amendment:
  - `bench` stays conditional. `record` writes the owner's answer from `$LOOP_PREV.bench` in the next iteration, and the ledger's `state` returns `owed: ended` once the latest ruling ends the case.
  - Every agent node is already gated on `owed`, so the extra iteration runs script nodes only.
  - `until_bash` tests `$filing.output.owed` (`filing` always runs), assigned unquoted per `loop-nodes.md:667-670`.

## D-31 (G-30)
- Objection 1, medium: `timeout ... 0` disables the timeout (GNU coreutils `man timeout`).
  - Ruling: survives.
- Amendment: the run-start guard (D-32) refuses a `GAUNTLET_TEST_TIMEOUT` that is not a positive integer. The node `timeout` stays omitted.

## D-32 (G-31)
- Objection 1, high: the guard and the fences read different envs. Moot under the D-11 amendment: the fences read the file a bash node writes from the same repository env.
  - Ruling: refuted by D-11's amendment.
- Objection 2, medium: an uncommitted `.archon/config.yaml` passes the checkout guard but is absent from the tree cut from HEAD (`worktree-cut-design.md:25`, `:35`).
  - Ruling: survives.
- Objection 3, medium: both `GAUNTLET_TEST_COMMAND` and `GAUNTLET_TEST_BRIEF_COMMAND` are needed (`writing-design.md:107`, `landing-design.md:62`).
  - Ruling: survives.
- Objection 4, medium: the check must not sit in a guard that standalone phases share.
  - Ruling: survives.
- Amendment: `gauntlet-run`'s own guard, never the shared working-folder check, refuses a run when:
  - either variable is blank;
  - `GAUNTLET_TEST_TIMEOUT` is set but is not a positive integer;
  - or `.archon/config.yaml` has uncommitted changes.

## D-35 (G-40)
- Objection 1, low: the role still names "or the repository's testing policy", a source outside the fence.
  - Ruling: survives.
- Amendment: ruling (a), and the test-writer role names `docs/testing.md` alone, as the rest of the pack does.

## D-36 (G-41)
- Objection 1, high: a zero-code route exists. Set the coder's `FENCE_TEST_COMMAND` to the brief command, as the test writer's already is (`writing-design.md:273`, `:508`, `:14` "reused unchanged").
  - Ruling: survives.
- Objection 2, high: a names-only mode would have to parse runner output, which `writing-design.md:527` forbids.
  - Ruling: survives.
- Objection 3, medium: messages still leak assertion literals.
  - Ruling: survives; the brief command prints ids only.
- Objection 4, medium: the `commit` tool returns hook output, which can include pytest tracebacks (`writing-design.md:73`).
  - Ruling: survives.
- Objection 5, low: without tracebacks the coder loses frames inside its own code.
  - Ruling: partial. That is the cost of the design's stated blindness to tests; the juror holds the full run.
- Amendment (replaces the ruling):
  - The coder's and `mend-code`'s fence-checks run the brief command, with no change to `checks.py`.
  - The `commit` tool returns git's exit and the names of failing hooks, never the hooks' output.

## D-33 (G-32)
- Objection 1, high: an ask at `cut` comes too late. `cut` depends on `tree`, so the gate fires only after writing and the mend have run, when it can no longer change what the tree was cut from.
  - Grounding: `worktree-cut-design.md:114-115` shows `id: cut`, `depends_on: [pin, tree]`.
  - Ruling: survives.
- Objection 2, high: the checkout often holds unrelated dirty or untracked files, which `landing-design.md:9` and `:278` treat as normal. Asking on them stops the run on a non-issue (CLAUDE.md 1.4).
  - Grounding: `landing-design.md:278` says "Unrelated uncommitted files in the checkout stay as they are."
  - Ruling: partial. The check cannot tell related edits from unrelated ones, and edits that reviewers read are the defect in finding 1.53. A wait before any paid phase, which the owner can clear by committing, is not a stop. Ignored files and `gauntlet/` stay out of the trigger.
- Objection 3, medium: the run-start `guard` is the right place, before intake and both reviews have been paid for.
  - Grounding: `gauntlet-design.md:54` shows `id: guard`, "once per run, in the checkout, before any phase".
  - Ruling: survives.
- Amendment (replaces the ruling):
  - The run-start `guard` prints `dirty`: the tracked paths that `git status --porcelain` reports changed, plus untracked paths that are not ignored, with `gauntlet/` excluded.
  - When `dirty` is non-empty, an `ask` after `guard` names the paths and says they will not reach the tree. Its options are `go on` and `leave`.
  - `pin` and `cut` drop `uncommitted`. `worktree-cut-design.md:23` is reworded to point at the guard's ask.

## D-34 (G-33)
- Objection 1, medium: the checkout root is already inside `task`. A second source from `pin` can disagree with it under a symlinked path, which breaks `copy-in`'s relative-path rule.
  - Grounding: `worktree-cut-design.md:140` says `task` is the "Absolute path of gauntlet/tasks/<slug>.md in the checkout", and `:139` makes `slug` a tree input. `gauntlet-intake-design.md:158` resolves the file route with `realpath -e`, and `:214` builds the talk route's path with no resolution.
  - Ruling: survives.
- Amendment (replaces the ruling):
  - Drop the tree's `checkout` input.
  - `copy-in` (`worktree-cut-design.md:153`) and `paths` (`gauntlet-design.md:156`) take the checkout root as `$INPUTS.task` with its trailing `/gauntlet/tasks/$INPUTS.slug.md` removed.
  - `pin`'s `output_format` stays as it is.

## D-37 (G-50)
- Objection 1, high: `retry` cannot rerun anything. Under G-47 and G-48, `retest` and `recheck` run only after a committed mend. Under G-46, `pose` ends "done" only on a committed mend.
  - Grounding: RULINGS.md G-46, G-47 and G-48. `landing-design.md:172` holds `pose`'s end rule.
  - Ruling: survives.
- Objection 2, high: `accept` ends the repair red and unreviewed. That breaks the Homes bans at `landing-design.md:370-371`, and `handoff` then prints "Mended on ...: no new failure.", which is false.
  - Grounding: `landing-design.md:370` bans "a red shown at the gate", `:371` bans "a mend that ends unreviewed", and `:193-196` hold the `handoff` lines.
  - Ruling: survives. `accept` is dropped, and `leave` stays the way out of a red the owner will not have mended.
- Objection 3, medium: `retry` writes no reply file. The stall count "verdicts since the latest reply file >= 5" therefore stays true, and `ask` fires on every later iteration.
  - Grounding: `landing-design.md:175-178` hold the stall condition, and `:104-106` show that `hear` writes a file only on `reply`.
  - Ruling: survives.
- Objection 4, medium: under D-02, text that contradicts the ruling must change in the same commit. `gauntlet-design.md:16` and `landing-design.md:9` say the owner answers "with guidance or leave".
  - Grounding: `sed -n 16p` of `gauntlet-design.md` and `sed -n 9p` of `landing-design.md`. RUN-11 (`REQUIREMENTS.md:47`) and `ROADMAP.md:89` hold once `accept` is dropped.
  - Ruling: survives, for those two lines.
- Amendment (replaces the ruling):
  - `repair`'s `ask` offers `reply`, `retry` and `leave`.
  - On `retry`, `hear` writes `gauntlet/mend/<slug>.reply.<n>.txt` holding `retry`, which resets the stall count. The next iteration then runs `retest` with no mender. G-47 and G-48 gain "or the latest decision was `retry`".
  - `pose` also ends "done" when a `retry` rerun is not red and no mend is uncommitted, which amends G-46.
  - In `handoff`, a repair with no committed mend prints "Rerun on $onto.output.head after retry: no new failure."
  - Homes row `landing-design.md:373` lists all three ask conditions and the three options.
  - `gauntlet-design.md:16` and `landing-design.md:9` read "with guidance, a rerun or leave".

# Pass 2 decision reviews (D-38 to D-59)

Run on 2026-11-05 under D-05. One `cad-reviewer` (route `cadence:cad-reviewer`, session default; no cross-model reviewer configured) refuted each D-NN line and its ruling. The returns are saved unchanged as `reviews/dr2/D-NN.json`, 49 objections in all. Each anchor was read with `sed -n` and holds the quoted text. The main session grounded each objection and ruled it. Rulings made by the owner (D-43, D-48) are amended only where the amendment keeps the owner's choice. D-43 stands as the owner ruled it; two of its objections stay open.

Library/API grounding: `docs/reference/archon/workflow-language.md:671` (the `agents:` keys: no server list), `:1187-1192` (`if_skipped` is literal data), `:2276` and `:2305` (fan-out `join` defaults to `all_done`; `all_success` fails the node and is not documented to stop opening children), `:94`, `:1143` and `:1311` (no doc says a repository `env:` reaches a `script:` node), `loop-nodes.md:696-697` and `:930`; `git check-ignore -h` (no revision option).

## D-38 (G-51)
- Objection 1, high: the trigger "a failed record exists" fires on every later run of the slug, because `gauntlet/failed/<slug>.txt` is never removed (`gauntlet-design.md:401`). `fail` already sets the files aside, so the trigger adds nothing.
  - Ruling: survives.
- Objection 2, high: plan and spec files share names (`gauntlet/plans/<slug>.N.txt`, `gauntlet/specs/<slug>.N.txt`, `plan-review-design.md:166`, `spec-review-design.md:192`), so one flat `failed/<slug>.approved/` collides, and a second set-aside lands on the first.
  - Ruling: survives.
- Objection 3, medium: the list leaves out `<slug>-summary.N.md` (`plan-review-design.md:39`).
  - Ruling: survives.
- Objection 4, medium: the hash is recorded only by `enter`, after approval (`spec-review-design.md:105`), so a task edited during an unfinished hearing is never detected.
  - Ruling: survives.
- Objection 5, medium: phase blocks would read and write `gauntlet/failed/`, against `gauntlet-design.md:114`, `:363`, `:401` and H24; a hash-change set-aside makes a never-failed slug look failed to Clerk.
  - Ruling: survives.
- Amendment (replaces the ruling):
  - `fail` alone writes `gauntlet/failed/`. It moves the slug's round, review, ruling, cite and summary files, and its approved files, into `gauntlet/failed/<slug>.<n>/plans/` and `.../specs/`, where n is the next free number.
  - The block's first script node records `<folder>/<slug>.task.sha256` at round 1, when absent. When the recorded hash differs from the task file's, it moves that folder's slug files into `<folder>/stale/<slug>.<n>/`. It never reads `gauntlet/failed/`.
  - There is no failed-record trigger. A rerun after `fail` starts at round 1 because `fail` emptied the folders.
  - The Homes rows `gauntlet-design.md:401`, H24 and the P20 row name the numbered folders and the `stale/` folder.

## D-39 (G-52)
- Objection 1, high: the collision in `<slug>.approved/` still stands on a second defect.
  - Ruling: survives; closed by the D-38 amendment's numbered folders.
- Objection 2, medium: the fixed name `<slug>.txt` keeps the failed-record trigger true for good.
  - Ruling: survives; closed by D-38 dropping that trigger.
- Objection 3, low: the Homes row `:401` ("written once") and H24 (`cp -n`) are not amended.
  - Ruling: survives.
- Amendment (replaces the ruling): `fail` writes the verdict to `gauntlet/failed/<slug>.<n>/verdict.txt` and copies it over `gauntlet/failed/<slug>.txt`, which Clerk reads as the latest verdict. `:401` and H24 read "rewritten by `fail` on each defect; the history in the numbered folders".

## D-40 (G-54)
- Objection 1, high: the guard's ask writes `<slug>.ruling.N.txt`, which marks round N tried (`plan-review-design.md:98`). `repairs` counts only rounds above the latest tried round (`:119`), so the guard never fires again on plan N.
  - Ruling: survives.
- Objection 2, medium: once repaired and cited, plan N is skipped by `state` as tried (`:106`), so the defense rewrites it as N+1 unheard.
  - Ruling: survives.
- Amendment (replaces the ruling): the guard's ask is recorded in `<slug>.guard.N.txt`. This file does not count as tried. `repairs` counts cite lines for round N written after the latest guard record. The guard reads `repairs` from state whatever the iteration wrote. FENCE_DENY of the defense and the speccer adds `*.guard.*.txt`.

## D-41 (G-55)
- Objection 1, high: every docket case is read only in an iteration that wrote a review (`spec-review-design.md:115`, `plan-review-design.md:136`), so `cap` never fires in the iterations G-55 is about.
  - Ruling: survives.
- Objection 2, medium: `state` runs twice per iteration (`plan-review-design.md:302`, `:334`; spec `:390`, `:422`) and once in `docket-in`, so "a line per `state` call" counts double.
  - Ruling: survives.
- Objection 3, medium: `<slug>.iter.txt` matches the defense's FENCE_WRITE `gauntlet/plans/*.txt` (`:229`) and the speccer's (`spec-review-design.md:283`).
  - Ruling: survives.
- Objection 4, medium: the cap logic would sit in `.shared/rounds.py`, which writing's revision hearing also calls (`writing-design.md:80`).
  - Ruling: survives.
- Amendment (replaces the ruling): mode `filing` alone appends one line per iteration to `<folder>/<slug>.iter.txt`. `cap` is exempt from the new-review gate, as the guard is (D-40). FENCE_DENY of the defense and the speccer adds `*.iter.txt`, and P20 lists the file. The counter runs for the plans and specs profiles only; the revisions profile keeps stage's own cap.

## D-42 (G-60)
- Objection 1, high: no per-sub-agent server list exists (`workflow-language.md:671`), so (c) is the ruling's real branch. Its extra Opus turns per round may cost more than the confinement buys once D-43 is settled.
  - Grounding: `:671` lists `description`, `prompt`, `model`, `tools`, `disallowedTools`, `skills`, `maxTurns`. G-60 (finding 2.26) was raised while `fence-spike` served `run_command` (`bash -c`, `spec-review-design.md:410`); D-43 removes that tool. With the fence route standing, `fence-scratch` and `fence-spike` give their holder only reads of the `fence-scratch` list, writes in `gauntlet/scratch`, and the command fixed in the fence with cwd in scratch. That list leaves out `tests`, `gauntlet/failed` and `gauntlet/specs/approved`, as the speccer's own list does (`:283-284`, `:288`).
  - Ruling: survives. The first branch is dead, and (c) buys no confinement the speccer's session lacks, at a node turn per spike request.
- Objection 2, medium: (c) as written leaves `file` with no output for a spike request, no "spike pending" state, one spiker in place of parallel ones, and a `$LOOP_PREV` read of a skippable node (the G-26/G-72 pattern).
  - Grounding: `loop-nodes.md:696-697`.
  - Ruling: survives; closed by dropping (c).
- Amendment (replaces the ruling):
  - The spiker stays an inline `agents:` sub-agent of the speccer node, and `speccer.mcp.json` names the three servers, as now (`spec-review-design.md:279`).
  - Archon has no per-sub-agent server list, so the speccer's session reaches `fence-scratch` and `fence-spike` too. `:253` and the Homes row `:520` say so, in place of "the speccer ... runs no command itself"; the speccer's role text still sends experiments to spikers.
  - No `denied_tools` entry is added.

## D-43 (G-61, owner's ruling)
- Objection 1, blocker: the spiker writes experiment files and the fixed-command tool runs them, so agent-written code runs unconfined. The shell has moved into the file's contents (2.27 again; `spec-review-design.md:520` rests on the prompt alone).
  - Grounding: the ruling's text (`CONTEXT.md:60`) runs files the spiker wrote; a useful spike executes agent-written code.
  - Ruling: does not move the ruling. The owner chose this route (RULINGS.md:62, :76): the spiker holds no shell, and a file it writes runs only under the command fixed in the fence, with cwd in its scratch folder, under the fence's timeout and process-group kill. The Homes row `:520` names that fence as the confinement, not the prompt.
- Objection 2, high: "as `checks.py` runs the test command" reads `gauntlet/settings.json`, which only the tree run's `settings` node writes, in phase 4 (`worktree-cut-design.md:50`). Spec review runs in phase 3 in the checkout, or standalone (D-21), with no settings file.
  - Ruling: survives; open. Where the fixed command comes from in phase 3 and in a standalone run is not yet designed.
- Objection 3, medium: one fixed command cannot answer the arbiter's `measure` requests or bite measurements in an arbitrary toolchain (`spec-review-design.md:17`, `:24`).
  - Ruling: survives; open. How a fixed command serves `measure` requests and bite measurements is not yet designed.
- Amendment: none. The ruling stands as the owner gave it: `run_command` goes and the spiker holds no shell. The fixed command's source and its reach (objections 2 and 3) stay open, and no design line states them until they close.

## D-44 (G-64)
- Objection 1, low: P6's writer is `put.ts` through nodes `put-open` and `put` (`gauntlet-intake-design.md:137`, `:197-203`), not `put` alone (`REVIEW-pass2.md:422`).
  - Ruling: survives.
- Amendment: P6 Writer reads "`put.ts`, nodes `put-open` and `put`".

## D-45 (G-66)
- Objection 1, low: contract row H19 (`contracts.md:35`) keeps `depends_on: [copy-in, baseline]`.
  - Ruling: survives.
- Amendment: H19 takes `[copy-in, baseline, settings]` in the same commit.

## D-46 (G-67)
- Objection 1, medium: the Homes row `landing-design.md:492` and `:17` still say the whole `gauntlet/` is copied.
  - Ruling: survives.
- Objection 2, medium: H40 (`contracts.md:56`) says the same.
  - Ruling: survives.
- Amendment: `:17`, `:492` and H40 name the skipped files.

## D-47 (G-68)
- Objection 1, medium: `landing-design.md:327` and H39 (`contracts.md:55`) still put the last-round stop at `onto` only.
  - Ruling: survives.
- Objection 2, medium: no fixture covers the new route (`:331`, `:512`; `docs/testing.md:53-55`).
  - Ruling: survives.
- Objection 3, low: `merge` counts a move by `HEAD != onto.head` (`:288`), so a move that still fast-forwards stops the last round for nothing.
  - Ruling: survives.
- Amendment: `:327` and H39 follow the ruling, and a fixture `gate-moved-last` is added to `:331` and Order step 6. `merge` counts a move only when the checkout's `HEAD` is no longer an ancestor of the branch (`git merge-base --is-ancestor`), in every round.

## D-48 (G-69, owner's ruling)
- Objection 1, high: `remend` is a fixed `yes`/`no` per include `with:` (`gauntlet-design.md:100-112`). No fixed pattern over four rounds gives exactly two re-mends whatever the timing.
  - Ruling: survives.
- Objection 2, medium: `landing-design.md:7`, `:220`, `:228`, `:503` and H23/H39 still fix three rounds.
  - Ruling: survives.
- Amendment (keeps the owner's four rounds): no round is passed `remend`. `onto` re-mends when the checkout moved and fewer than two re-mends are recorded in `made`. A third needed re-mend fails `onto`, naming the move. The listed lines, `contracts.md:39` and `:55` follow.

## D-49 (G-72)
- No objection. Load-bearing claims grounded:
  - an `until_bash` that reads a node its own `when:` can skip fails the group (`loop-nodes.md:696-697`, `:930`): confirmed.
  - `all_done` runs whatever the deps' outcome (`workflow-language.md:325`): confirmed.
- Ruling stands.

## D-50 (G-73)
- Objection 1, medium: with `if_skipped: ""`, the new node cannot tell a skipped `put` from one that ran and accepted, so a stale refusal returns.
  - Grounding: `workflow-language.md:1187-1192`.
  - Ruling: survives.
- Amendment: `put`'s binding takes `if_skipped: "<skipped>"`. The node prints put's refusal whenever put ran, even when empty, and put-open's only when put printed `<skipped>`.

## D-51 (G-78)
- Objection 1, low: P19 (`contracts.md:80`) and node `settings`' `"test"` key (`worktree-cut-design.md:168`, `:50`) still promise the dropped test command. `fence/checks.py` runs the brief command (`worktree-cut-design.md:15`).
  - Ruling: survives.
- Amendment: the `"test"` key goes from `settings`, `:50` and P19.

## D-52 (G-79)
- Objection 1, high: the guard is a `script:` node (`gauntlet-design.md:54-56`). The design says whether `env:` reaches a script node is unmeasured (`:142-143`), and no Archon doc says it does. So the blank check moves the G-79 defect instead of removing it.
  - Ruling: survives.
- Objection 2, medium: "guard only" contradicts D-54's check in `settings`.
  - Ruling: survives; settled with D-54 below.
- Amendment (replaces the ruling): `stage.py` reads `gauntlet/settings.json`. The blank check moves into a bash node `env-check` of `gauntlet-run`, before any phase, since bash nodes see `env:` (`worktree-cut-design.md:33`). `guard` keeps its other checks. `:142-143` is reworded.

## D-53 (G-80)
- Objection 1, high: the new check has no legal home (`gauntlet-intake-design.md:281`, `plan-review-design.md:430`, `spec-review-design.md:525`), and putting it in `requireIgnored` refuses standalone phases over a non-issue.
  - Ruling: survives.
- Objection 2, medium: the global excludes file also applies in the tree (same user and host), so refusing it is an over-refusal.
  - Ruling: survives.
- Objection 3, medium: git has no query for ignore rules at `HEAD` (`git check-ignore -h`), so the check would become a text match outside git's matcher.
  - Ruling: survives.
- Amendment (replaces the ruling):
  - `requireIgnored` takes an option `committed`, which only `gauntlet-run`'s guard passes. With it, `git check-ignore -v gauntlet/` names the rule's source.
  - A rule from `.git/info/exclude` or the global excludes file passes; worktrees share both.
  - A rule from a `.gitignore` passes only when that file is tracked and `git diff --quiet HEAD -- <file>` holds. Otherwise the guard says to commit it.
  - The Homes row `:281` names the option.

## D-54 (G-81)
- Objection 1, high: `baseline` depends on `[guard, branch-check]` only (`worktree-cut-design.md:181`), so it runs beside `settings` and the check in `settings` cannot stop it.
  - Ruling: survives.
- Objection 2, high: the check fires in the tree run, after the paid phases, though the cause is visible at run start (D-32, `CONTEXT.md:49`).
  - Ruling: survives.
- Objection 3, medium: P11 (`contracts.md:72`, `worktree-cut-design.md:201`) already requires the config committed, so refusing an ignored or uncommitted config enforces a contract; it is no stop on a technicality.
  - Ruling: survives; the ruling's reason for (c) is withdrawn.
- Objection 4, medium: the check conflicts with D-52's single home.
  - Ruling: survives.
- Amendment (replaces the ruling):
  - `gauntlet-run`'s `env-check` (D-52) also refuses when `.archon/config.yaml` is untracked, ignored or differs from `HEAD`, naming P11.
  - With the config committed, its `env:` reaches the tree run's bash nodes (`worktree-cut-design.md:33`), so `settings` adds no check.
  - `baseline` depends on `settings` and reads the brief command from `gauntlet/settings.json`.

## D-55 (G-82)
- No objection. Load-bearing claims grounded:
  - the row says only `pin.py` derives the slug (`worktree-cut-design.md:217`): confirmed.
  - `rounds.py` derives it from `INPUTS_TASK` (`spec-review-design.md:90`): confirmed.
- Ruling stands.

## D-56 (G-83)
- Objection 1, medium: `cut` still prints `base` from `$pin.output` (`worktree-cut-design.md:130`), and H17, `gauntlet-design.md:14`, `worktree-cut-design.md:7` and `:230` still name it.
  - Ruling: survives.
- Objection 2, medium: landing's `repin` (`landing-design.md:253`), `land/scripts/pin.py` (`:343-344`) and `.shared/pin.py` still carry `base`, which nothing reads (`:259`).
  - Ruling: survives.
- Amendment: `base` goes from `pin`, `cut`, `repin`, `.shared/pin.py`, `land/scripts/pin.py`, H16, H17, S14, S15 and the lines named, with their tests.

## D-57 (G-88)
- Objection 1, high: carried code waves running first break "test waves first" (`writing-design.md:28`, `:200`, `:158`).
  - Ruling: survives.
- Objection 2, medium: `next` is still derived from the latest cut (`:152-153`), so the kind and the wave can differ, and carried waves can go unrun.
  - Ruling: survives.
- Objection 3, medium: the drop rule matches steps only, so carried test blocks are never dropped (`:26`).
  - Ruling: survives.
- Objection 4, medium: dropping a whole block drops the steps that do not overlap (`:160`).
  - Ruling: survives.
- Amendment (replaces the ruling):
  - One wave per iteration, test waves before code waves, the carried wave before the new wave of the same kind; each wave keeps its own ruling.
  - `next` is the kind of the wave handed out.
  - A carried block loses only the specs (tests blocks) or steps (code blocks) a newer cut holds. A block left empty is dropped.

## D-58 (G-93)
- Objection 1, medium: with `max_parallel: 1`, a block that stops on `contest` or `commit-failed` leaves uncommitted edits, and the next block's `fence-checks` runs over them. `join` defaults to `all_done` (`workflow-language.md:2276`), and no join is documented to stop opening children.
  - Ruling: partial. The leftover state predates the ruling, but the ruling claims to cure it.
- Objection 2, low: `writing-design.md:537` and A9 (`contracts.md:158`) still say `max_parallel: 2`.
  - Ruling: survives.
- Amendment: the fanned-out include starts with a bash node that ends the block, with no writer session, when the tree holds edits outside the block's `paths`. It prints outcome `blocked` naming them; the next cut carries the block. `:537` and A9 read `max_parallel: 1`.

## D-59 (G-98)
- Objection 1, high: the juror runs before the mend (`landing-design.md:110-111`) and the reviewer after it (`:160-161`), so one file per iteration serves one of them only.
  - Ruling: survives.
- Objection 2, medium: a bare `git log -p` dumps the whole history (1.3); the roles judge the branch past the checkout's `HEAD` (`:413`, `:449`).
  - Ruling: survives.
- Amendment (replaces the ruling): node `changes`, after `hear`, writes `gauntlet/mend/<slug>.changes.<n>.txt` from `git -C <tree> log -p $onto.output.head..$INPUTS.branch` for the juror. Node `mended`, after `recheck`, writes `<slug>.mended.<n>.txt` from the same range for the reviewer. The prompts name their file.

Cost: 22 `cad-reviewer` dispatches at the session default (no tier or effort applied to `cad-reviewer`; no cross-model arm configured), about 0.87M subagent tokens (873,987) by the returns' own counts (D-45's close carries no figure; its return reported 26,512).

## Rulings after application

Made by the main session (3.2) on 2026-11-05, after the executors applied the pass-2 rulings and reported these gaps. Each is the one fix that keeps its ruling's aim; the alternatives fail or reopen a gap already ruled.

- D-58 (G-93): nothing starts the cut that carries a `blocked` block unless a juror case opens in the same wave. A coder's leftover edits outside every test block's paths end the test cut `blocked`, no case opens, and `state` moves on to `test` and `seal`, whose `git add -A` commits the leftover edits.
  - Grounding: `writing-design.md:151` (the juror case is read only for a contest or commit-failed), `:28`, `:135-136`.
  - Amendment: a `blocked` outcome in the latest blocks file, newer than the latest verdict, is a juror case, as `contest` and `commit-failed` are, its grounds the paths outside the block. The juror's `TESTS` or `CODE` verdict starts the cut that carries the block. The juror case precedes `test` and `seal` in `state`, so no seal runs over a blocked wave. A forced cut alone would leave the leftover edits in the tree.
- D-40 (G-54): a guard record resets only `repairs`, and the stretch counts the tried rounds since the last ruling plus `repairs`. Once 11 rounds are tried since the ruling, every repair-only iteration brings the stretch to 12 and asks the owner again until a review arrives (1.4).
  - Grounding: `plan-review-design.md:25`, `:28`, `:109`, `:129`, `:146`; `spec-review-design.md:70`, `:121`, `:144` (the shared `.shared/rounds.py`).
  - Amendment: a guard record resets the stretch as a ruling does. The stretch counts tried rounds with N > `since` and N at or above the latest guard record's round, plus `repairs`. Attempts, `NON-RESPONSIVE` and `cap` go on, as now. Both profiles take the rule through `.shared/rounds.py`; rows H28, H29 and P20 follow.
- D-43 (G-61), objections 2 and 3: where the fixed command comes from, and how it serves `measure` requests and bite measurements.
  - Grounding: `spec-review-design.md:17`, `:24`, `:318-325`, `:548`; objection 1's ruling already accepts that a file the spiker writes runs under the fixed command.
  - Amendment: `fence/spike.py` holds the command as a constant, `bash run.sh`, run with cwd in the folder under `timeout -k 10 600 nice -n 10`, its process group killed on timeout. It reads no `gauntlet/settings.json`, so it runs in phase 3 and in a standalone spec review (objection 2). The spiker writes `run.sh` in its folder, so one fixed command runs any toolchain and serves `measure` requests and bite measurements (objection 3). The owner's ruling stands: the spiker holds no shell, and the agent supplies no command. Rows F12 and P14 follow.
