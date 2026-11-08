Status: proposed.

# Gauntlet

## Why

Gauntlet is one run, `gauntlet-run`, started by one command: `archon workflow run gauntlet-run`, with the owner's message and an optional `--input file=<path>`, or the same text typed in the Archon web UI. Every phase runs inside that run, in order, and each phase hands its result to the next. The owner answers the run-start ask (when the checkout holds changes that will not reach the tree) and the pauses of intake, plan review and spec review on that run's id, and the pauses of writing, the mend and the review before landing on the id of the tree run, the child run the cut starts in the tree, or of the re-mend run, the child run landing starts in a second tree when the checkout has moved; `archon workflow get <run id> --json` gives it at `.metadata.approval.childRunId`. Landing itself, block `land`, holds no agent and no wait. No `gauntlet-run` node goes back to an earlier phase; the re-mend run repeats only block `mend`, in a second tree, and the owner's back to planning ends the run cleanly and prints the command that starts the next plan review (this file's "Back to planning"). This file covers how the phases join. Each phase's own design covers its inside, and nothing here restates it. The owner-control design (`2026-11-07-owner-control-design.md`) is the approved source of the item file, the amicus, the review before landing and stages; the designs it names are cited below as its homes.

The phases, in run order:

1. **Intake** (`gauntlet-intake-design.md`). Turns what the owner wants done into the item file, `gauntlet/items/<slug>.md`, from a file the owner wrote or through a conversation with Clerk that ends on the owner's approval of each item. Its hand-off is node `handoff` of the intake design (H3).
2. **Plan review** (`plan-review-design.md`). The defense decides whether the item file needs a plan and writes one, each step citing the Ids of the items it serves, in stages when one part must land before the next can start. The prosecutor tries it round by round, and the owner approves the plain-English summary. Its hand-off is node `handoff` of the plan review design (H4); `plan` is `""` when no plan is needed.
3. **Spec review** (`spec-review-design.md`). The speccer decides whether tests need speccing and writes the specs. The arbiter tries them, and the owner approves them or confirms that nothing is testable. Its hand-off is node `handoff` of the spec review design (H5).
4. **Worktree cut** (`worktree-cut-design.md`). Once per stage of the approved plan (this file's "Stages"), cuts one worktree from the checkout's `HEAD`, copies the approved files in and records the brief test baseline. Its hand-off is node `cut` (H17), the last fields from the tree run's `handoff` (H18).
5. **Writing** (the writing design). Runs in the tree, as block `write` of the tree run, after the baseline, for one stage. Test writers write the tests from the approved specs, then code writers write the code. On every red, contest, blocked block, failed commit or idle iteration the amicus briefs the owner, who chooses the next pass or back to planning. A wrong plan or spec is revised inside writing, as an approved revision, when the owner's direction asks for it. Its hand-off is node `handoff` of block `write` (H21), read by the tree run's `mend` and `handoff`, `outcome` `written` or `planning`, `summary` being the plan summary and the summaries of the approved revisions.
6. **Mend** (`landing-design.md`). Runs in the tree, as block `mend` of the tree run, after `write`, when writing hands off `written`. It reads the checkout's `HEAD` with `git -C <checkout>`, rebases the tree's branch onto it, reruns the brief test command when the checkout has moved past base, and then meets the owner, on the id of the run the mend executes in: the amicus briefs the owner on a red, a mender's contest or failed commit and an unsound mend, and the review before landing (the landing design) briefs the owner on a landable tree. The owner chooses to discuss, run again with a direction (a code or test mender commits the mend on top of the branch's last commit, and a reviewer reads every mend), go back to planning, leave, or land. Its hand-off is node `handoff` of block `mend` (H22), read by the tree run's `handoff`, `outcome` `ready`, `left` or `planning`.
7. **Landing** (`landing-design.md`). Runs in the checkout as block `land` of `gauntlet-run`, after `cut`, when the tree run hands off `ready`, and reaches a tree only with `git -C <worktree>`, `archon complete` and the re-mend run. It checks that the tree's branch still fast-forwards the checkout. When the checkout has moved past it, landing re-mends: it starts the re-mend run `gauntlet-remend` in a second tree, which runs block `mend` only (rebase, tests, repair, and the review and the owner again) on a branch pinned at the tip of the branch of the tree the round lands, the first tree's for round 1. It re-mends within the landing rounds' bound (`runtime-model-design.md`, "Loop shape and bounds"), each round an `include` of `land` under its own id (`land` to `land-4`). On the owner's land, given at the review, it fast-forwards the checkout, copies the landed tree's records into the checkout's `gauntlet/` and removes every tree it made and their branches. It runs git, Archon's CLI and one script, and no agent and no wait. Its hand-off is node `handoff` of block `land`, `outcome` `landed`, `left`, `planning` or `moved`, the last fields feeding the next round.

The run ends at the last round of block `land` that runs (`land`, `land-2`, `land-3` or `land-4`, of the last stage) when every stage lands, after `cut` or the round when the owner leaves (`left`), and at node `back`, completed and not cancelled, when the owner goes back to planning (`planning`). A cancelled phase block ends the run cancelled at its own node: plan review's and spec review's node `vacate`, after the hearing, cancels when every slot is retired (`runtime-model-design.md`, "Loop shape and bounds", Vacancy), with no node past it run; writing has no `vacate`. A tree run that ends cancelled fails `gauntlet-run`'s node `tree`, so `cut` and everything after it is not reached; the tree and its branch stay; the resume is `runtime-model-design.md`'s, "Resume and rerun".

### Stages

The owner-control design's staged plans (D-93): the plan names the parts that must land one before the next as stages, in landing order (plan review design, "Plan grammar"), and a plan with no such dependency is one stage. Each stage is written in its own tree, meets the owner through the amicus and lands before the next stage's tree is cut. `loop_group` bodies reject a `workflow:` node (`workflow-language.md:1732-1734`, `:2543-2544`), so the stage sequence takes the unrolled bounded form (`runtime-model-design.md`, "Loop shape and bounds"), each stage with its own node ids.

- **The bound**: `STAGES = 3`. This is the one statement of it; the plan review design's `scope.py` enforces this bound by name, listing a plan with more stages as a problem the prosecutor rejects to the planner, so the run never meets one: a plan over the bound is replanned in fewer stages, and no node of the run counts past it.
- **The ids**: stage 1 keeps the bare ids, `pin`, `tree`, `cut`, `land`, `land-2`, `land-3`, `land-4`; stage 2 is `s2-pin`, `s2-tree`, `s2-cut`, `s2-land`, `s2-land-2`, `s2-land-3`, `s2-land-4`; stage 3 is `s3-` and the same names. Node `pin` of stage 1 prints `stages`, the plan's stage count.
- **The order**: stage `k` after the first starts when stage `k-1` landed (node `done`, below) and `$pin.output.stages >= k`. Its `pin` creates its branch at the checkout's `HEAD` as the checkout then stands, so its tree holds the earlier stages' code; its `tree` takes `stage: k`; its `copy-in` brings the earlier stages' revisions and writing records (worktree cut design). Each stage's four land rounds are its own, `made` included.
- **What a stage seals and shows**: each stage seals with a final commit of its own (`runtime-model-design.md`, "Commit model"), and its review before landing is scoped to its own plan steps and items (landing design).

### Back to planning

The owner's `back-to-planning` choice, at the amicus in writing, in the mend or at the review before landing, ends the tree run with outcome `planning` and the paths of two tree files: the owner's direction (`Rework: planning`, `Landed: <n>` and the owner's words) and the amicus record (writing design, "Direction"). `cut` hands them on, and node `back` of that stage, a script node of `gauntlet-run` in the checkout (`gauntlet-run/scripts/back.py`), runs when `cut` hands off `planning`:

- it copies the two files into the checkout as `gauntlet/back/<slug>.<n>.amicus.md` and `gauntlet/back/<slug>.<n>.direction.md`, `n` the next free number;
- it sets aside every file of the slug in `gauntlet/plans/`, `gauntlet/specs/`, `gauntlet/write/` and `gauntlet/revisions/`, `approved/` included, into the `stale/<slug>.<n>/` folder of each (the set-aside of `runtime-model-design.md`, "Hearing state"), so the rejected plan and specs are not handed back by `owed: approved` and plan review hears the item file again from round 1; stages already landed stay landed in the checkout;
- it prints the command for the next plan review, the one command of this design, `archon workflow run gauntlet-run --input file=<checkout>/gauntlet/items/<slug>.md --input amicus=<checkout>/gauntlet/back/<slug>.<n>.amicus.md --input direction=<checkout>/gauntlet/back/<slug>.<n>.direction.md`, for the owner to copy into the terminal, and ends. The run completes; it is not cancelled (contracts A32: a `cancel:` node would end it cancelled). The owner starts the printed run and it carries on as any run does: intake finds the item file already in place and checks it, plan review takes `amicus` and `direction` beside the item file and the defense plans only the work not yet landed (plan review design), and the later phases follow.


The copies the phase designs once held, each resolved (D-06; rulings in `.planning/phases/1/RULINGS.md`):

- Standalone phase workflows: intake, plan review and spec review are each a workflow started on its own and a block of `gauntlet-run`. Each description invites direct use and names `gauntlet-run` as the pick for a whole run, so Archon's router picks a phase only for that phase's work. Resolved by G-12: this design's "Phase files, standalone and as blocks"; each phase file's `description:` in the intake design's `intake/intake.yaml`, the plan review design's `plan-review/plan-review.yaml` and the spec review design's `spec-review/spec-review.yaml`.
- `worktree: enabled: false`: 4, in `intake/intake.yaml`, `plan-review/plan-review.yaml`, `spec-review/spec-review.yaml` and `gauntlet-run/gauntlet-run.yaml`. A phase run on its own needs it; under `include:` Archon drops a composed file's `worktree:` with one stderr log line, `include.workflow_level_fields_dropped`, and no validation warning (PROBES.md P7). Resolved by G-12: this design's `gauntlet-run/gauntlet-run.yaml` (the run's head) and "Phase files, standalone and as blocks"; the `worktree:` key of `intake/intake.yaml`, `plan-review/plan-review.yaml` and `spec-review/spec-review.yaml` in their designs.
- Working-folder guard nodes in the checkout: 4, `gauntlet-run/scripts/guard.ts` and `intake/scripts/guard.ts`, `plan-review/scripts/guard.ts` and `spec-review/scripts/guard.ts`, all on `.shared/working-folder.ts`. A phase run on its own needs its guard; in a run the phase guard repeats the run guard's ignore check, which is a git query. The run's own guard adds the `committed` ignore check (G-80) and the dirty listing (G-32), and node `env-check` the test-settings and config checks (G-31, G-79, G-81); no phase guard holds them. `gauntlet-tree/scripts/guard.ts` and `gauntlet-remend/scripts/guard.ts` run in a worktree. Resolved by G-12: this design's `gauntlet-run/scripts/guard.ts`; the intake design's `.shared/working-folder.ts` and `intake/scripts/`; node `guard` of the plan review and spec review designs.
- Hand-off contracts: 3 `handoff` nodes, each declaring an `output_format` that names every field it prints. Resolved by G-12: this design's "Phase files, standalone and as blocks"; node `handoff` of the intake and plan review designs; the spec review design's `spec-review/scripts/handoff.ts` and node `handoff`. Resolved again by D-81: the hand-offs read `items` in place of `task`, and the tree run and cut add `outcome`, `direction`, `amicus` and `summary` (this file's modules `gauntlet-tree/gauntlet-tree.yaml` and `write/write.yaml`).
- `$INPUTS` left of a `when:` comparison: none. Intake's `route` prints the input as an output and `from-file` and `ground` read `$route.output.file`. Resolved by G-12: the intake design's nodes `route`, `from-file` and `ground`; this design's "Intake's routing reads a node output".
- Inline `script:` hand-offs that print an input: none. Plan review's and spec review's `handoff` read `INPUTS_<NAME>` from the environment. Resolved by G-12: node `handoff` of the plan review design; the spec review design's `spec-review/scripts/handoff.ts`.
- Writers of the tree's `gauntlet/plans/approved/` and `gauntlet/specs/approved/`: `copy-in` for `<slug>.txt` and `<slug>-summary.md`, and writing's `enter` for `<slug>.rev<N>.txt`. Resolved by G-12 and G-108: the worktree cut design's Homes row "Approved files in the tree"; node `enter` of this design's `write/write.yaml` (writing's signature). Resolved again by D-81: the plan's `<slug>.scope.txt` is written by plan review's `enter` and copied by `copy-in`.
- Places a node runs in the tree: 2, the tree run and, for the mend only, the re-mend run (G-45), each in its own tree. An agent runs in its run's checkout, and no node field sets another folder. An `include:` block has no checkout of its own. `isolation:`, valid only on a `workflow:` node, gives a child run its parent's checkout or a fresh worktree on a new branch cut from base, never an existing tree; the re-mend run's tree is a new worktree on a branch pinned at the tip of the branch of the tree the round lands, the first tree's for round 1. `fence/files.py` and `fence/checks.py` root at `CLAUDE_PROJECT_DIR`, the agent's own folder: no fence config sets it, and both servers exit 2 at start when its real path differs from the real path of their working folder (PROBES.md P2). Writing and the mend are therefore blocks of `gauntlet-tree`, and the mend again a block of `gauntlet-remend`, never of `gauntlet-run`. Resolved by G-02: the intake design's `fence/` module and `intake/clerk.mcp.json`.
- Fences that read the checkout outside intake: 4 (their values: the plan review design, section `plan-review/defense.mcp.json`): `plan-review/defense.mcp.json`, `plan-review/prosecutor.mcp.json`, `plan-review/reporter.mcp.json` and `plan-review/analyst.mcp.json`. The servers of `spec-review/speccer.mcp.json`, which the speccer and its spikers both reach (D-42), list their readable folders and none holds `gauntlet/specs/approved/` or `tests/`. The spiker holds no shell: a file it writes in `gauntlet/scratch/<slug>/` runs only under the command fixed in `fence/spike.py`, with cwd in that folder (D-43). `fence/files.py` applies `FENCE_DENY` to writes only. Resolved by G-03 and, for the failed-record clause, D-81 (no failed-task folder exists): this design's "Checkout fences outside intake"; the spec review design's `spec-review/speccer.mcp.json`, `spec-review/arbiter.mcp.json`, `spec-review/reporter.mcp.json`, `spec-review/analyst.mcp.json`; `FENCE_HIDE` itself stays for the coder's fence (writing design).
- Role files writing would reuse: none. Commands resolve only from a workflow's own `commands/`, so writing has its own `write/commands/`. Resolved by G-12: the writing design's "Why" (its roles line); this design's Homes row "Writing's roles".
- Comparisons of a test run against the brief baseline: 1, `.shared/red.py`, imported by `red` of `write/scripts/stage.py` and by `mend/scripts/verify.py`. Resolved by G-12: this design's `.shared/red.py` and Homes row "Whether a test run is red"; the landing design's `mend/scripts/verify.py`.
- Copies of the tree's records in the checkout: landing's `record` is the only writer, and writes revisions and writing's round records there. Resolved by G-12: the landing design's node `record`; this design's Homes row "The tree's records in the checkout".

The tree holds none of these yet. The only parts built are `fence/` and `spec-review/commands/arbiter.md`.

## Modules

### `gauntlet-run/gauntlet-run.yaml` (the run's head)

The one workflow the owner starts. It declares the run's inputs, checks the working folder and the repository's test settings once, asks the owner about changes that will not reach the tree, and includes the three earlier phases in order. The worktree cut design gives the nodes `pin`, `tree` and `cut` of stage 1 and the description. This module fills the phases' entry, which the worktree cut design leaves open, and the nodes after the cut: the stage chain (heading "Stages"), landing and `back`.

```yaml
name: gauntlet-run
inputs:
  file:
    default: ""
    description: Path of an item file the owner wrote. Blank sends the run's message to Clerk.
  amicus:
    default: ""
    description: Path of the amicus record a back to planning printed (gauntlet/back/<slug>.<n>.amicus.md), or "".
  direction:
    default: ""
    description: Path of the owner's direction a back to planning printed (gauntlet/back/<slug>.<n>.direction.md), or "".
worktree:
  enabled: false                       # the run's one worktree setting; the phase files declare it too and Archon drops theirs under include:

nodes:
  - id: guard                          # once per run, in the checkout, before any phase
    runtime: bun
    script: guard
    output_format: { type: object, properties: { file: { type: string }, amicus: { type: string }, direction: { type: string }, dirty: { type: string } }, required: [file, amicus, direction, dirty] }

  - id: env-check                      # once per run, in the checkout, before any phase; a bash node sees the repository's env:
    depends_on: [guard]
    bash: <exit 1 naming the cause on stderr when GAUNTLET_TEST_BRIEF_COMMAND is unset or blank (the one required
          test variable), when GAUNTLET_TEST_TIMEOUT is set but not a positive integer, when .archon/config.yaml
          of the checkout is untracked, ignored or differs from HEAD (its env: reaches the tree run only when committed),
          when the repository has no remote configured (git remote get-url <remote> fails, <remote> being worktree.remote
          of .archon/config.yaml, origin when unset); each message names the fix. Configuration only: no network call, so
          a remote that is configured but unreachable still fails node tree (worktree cut design)>

  - id: dirty                          # the owner, only when the checkout holds changes that will not reach the tree
    depends_on: [env-check]
    when: "$guard.output.dirty != ''"
    wait:
      form: select
      attention: "These paths hold changes that will not reach the tree: $guard.output.dirty"
      options: [ { id: go-on, label: Go on }, { id: leave, label: Leave } ]

  - id: stop                           # leave at the run-start ask
    depends_on: [dirty]
    when: "$dirty.output.decision == 'leave'"
    cancel: "You left the run at the run-start ask. Commit, stash or ignore the listed paths, then start a new gauntlet-run."

  - id: intake
    depends_on: [guard, env-check, dirty, stop]
    trigger_rule: none_failed_min_one_success
    include: intake
    with: { file: $guard.output.file }

  - id: plan-review
    depends_on: [intake]
    include: plan-review
    with: { items: $intake.output.items, amicus: $guard.output.amicus, direction: $guard.output.direction }

  - id: spec-review
    depends_on: [plan-review]
    include: spec-review
    with: { items: $plan-review.output.items, plan: $plan-review.output.plan }

  # pin, tree, cut: as the worktree cut design gives them; pin depends on [spec-review].
  # cut also prints outcome, direction, amicus and summary from $tree.output; its output_format adds
  # outcome (enum: ready, left, planning), direction (string), amicus (string) and summary (string), all required.

  - id: land                           # phase 7, stage 1, round 1, in the checkout
    depends_on: [cut]
    when: "$cut.output.outcome == 'ready'"
    include: land
    with: { slug: $cut.output.slug, round: land, stage: 1, worktree: $cut.output.worktree,
            branch: $cut.output.branch, summary: $cut.output.summary }

  - id: land-2                         # round 2, only when round 1 found the checkout moved
    depends_on: [land]
    when: "$land.output.outcome == 'moved'"
    include: land
    with: { slug: $cut.output.slug, round: land-2, stage: 1, worktree: $land.output.worktree,
            branch: $land.output.branch, summary: $cut.output.summary, made: $land.output.made }

  - id: land-3                         # round 3, only when round 2 found the checkout moved
    depends_on: [land-2]
    when: "$land-2.output.outcome == 'moved'"
    include: land
    with: { slug: $cut.output.slug, round: land-3, stage: 1, worktree: $land-2.output.worktree,
            branch: $land-2.output.branch, summary: $cut.output.summary, made: $land-2.output.made }

  - id: land-4                         # round 4, the last: a move found by its merge stops the run
    depends_on: [land-3]
    when: "$land-3.output.outcome == 'moved'"
    include: land
    with: { slug: $cut.output.slug, round: land-4, stage: 1, worktree: $land-3.output.worktree,
            branch: $land-3.output.branch, summary: $cut.output.summary, made: $land-3.output.made }

  - id: done                           # stage 1's end: how it ended, whichever round or phase ended it
    depends_on: [cut, land, land-2, land-3, land-4]
    trigger_rule: all_done
    runtime: bun
    script: <print { end, direction, amicus }: end "landed" when the last round that ran handed off landed; "left" when cut or
            that round handed off left; "planning" when cut or that round handed off planning, direction and amicus from the
            one that did, "" otherwise; the rounds read as INPUTS_LAND, INPUTS_LAND_2, INPUTS_LAND_3 and INPUTS_LAND_4>
    with: { cut: $cut.output, land: { from: $land.output, if_skipped: "" }, land_2: { from: $land-2.output, if_skipped: "" },
            land_3: { from: $land-3.output, if_skipped: "" }, land_4: { from: $land-4.output, if_skipped: "" } }
    output_format: { type: object, properties: { end: { type: string, enum: [landed, left, planning] }, direction: { type: string }, amicus: { type: string } }, required: [end, direction, amicus] }

  - id: back                           # the run's end for the owner's back to planning, completed and not cancelled
    depends_on: [done]
    when: "$done.output.end == 'planning'"
    runtime: uv
    script: back                       # gauntlet-run/scripts/back.py (heading "Back to planning")
    with: { slug: $cut.output.slug, items: $spec-review.output.items, direction: $done.output.direction, amicus: $done.output.amicus }

  # s2-pin, s2-tree, s2-cut, s2-land, s2-land-2, s2-land-3, s2-land-4, s2-done, s2-back and the s3- set: nodes `pin` to `back` again
  #   under those ids (heading "Stages"), each stage's pin on [done] of the stage before with
  #   when: "$done.output.end == 'landed' && $pin.output.stages >= <k>" ($s2-done for stage 3), its tree with stage: <k>,
  #   its rounds and `done` and `back` on its own `cut`.
```

The description is the worktree cut design's, with writing, the mend and landing named among the phases it takes the work through.

The run's message (`$ARGUMENTS`) reaches Clerk unchanged, because an included block runs inside the run. The pauses of intake, plan review and spec review are answered on the run's own id, and writing's, the mend's and the review before landing's on the tree run's id, or on the re-mend run's id for the mend of a second tree. A failed phase fails the run; what a resume does is `runtime-model-design.md`'s, "Resume and rerun". A back to planning ends the run at `back`, completed; the tree and its branch stay where they are, for the owner to inspect or remove with `archon complete <branch> --force`. An owner's leave at the mend's ask, in either run, ends the run with every tree and branch kept the same way; a leave at the mend of the tree run ends it after `cut`, with no node past `cut` run but `done`.

### `gauntlet-run/scripts/back.py`

Node `back`: the run's end on the owner's back to planning (heading "Back to planning" gives what it does). Runs in the checkout. Imports `slug` from `.shared/pin.py`; standard library only. Replaces nothing.

```python
# /// script
# requires-python = ">=3.12"
# ///
# Env: INPUTS_SLUG, INPUTS_ITEMS (absolute path of gauntlet/items/<slug>.md in the checkout), INPUTS_DIRECTION, INPUTS_AMICUS
#   (absolute tree paths of the owner's direction and the amicus record).
# n = the next free number of gauntlet/back/<slug>.<n>.direction.md. Copies the two files to gauntlet/back/<slug>.<n>.direction.md
#   and gauntlet/back/<slug>.<n>.amicus.md (cp -n semantics; differing target: exit 1 naming both paths). Moves every file of the
#   slug in gauntlet/plans/, gauntlet/specs/, gauntlet/write/ and gauntlet/revisions/, approved/ included, into
#   gauntlet/plans/stale/<slug>.<m>/, gauntlet/specs/stale/<slug>.<m>/, gauntlet/write/stale/<slug>.<m>/ and
#   gauntlet/revisions/stale/<slug>.<m>/, m the next free number of each.
# stdout: the command, one line:
#   the command of the heading "Back to planning", naming INPUTS_ITEMS and the two copied files
def main() -> int: ...
```

Suite: `gauntlet-run/tests/test_back.py`, run as `docs/testing.md` states with the folder `gauntlet-run/tests`. It drives `main` against a real folder under `tmp_path`. It pins: the two files copied under the next free number; the slug's plan and spec files, approved ones included, moved to `stale/`; the printed command naming the three paths; a second back to planning on the slug taking the next number.

### `gauntlet-run/scripts/guard.ts`

The run's own guard, which runs in the checkout before any phase. It runs the shared working-folder check with option `committed`, which only this guard passes (the intake design's `.shared/working-folder.ts`), and lists the checkout's dirty paths. The listing lives in this script and never in `.shared/working-folder.ts`, because the phases run on their own and share that check. The checks of the test variables and of `.archon/config.yaml` run in node `env-check`, a bash node, because the repository's `env:` is measured to reach bash nodes (the worktree cut design, Why, the measured `env:` bullet) and no Archon doc says it reaches a `script:` node. It also passes the run's `file`, `amicus` and `direction` inputs on as outputs, so the blocks receive them as node references. `intake/scripts/guard.ts`, `plan-review/scripts/guard.ts` and `spec-review/scripts/guard.ts` are the phases' own guards, each the two lines of `gauntlet-tree/scripts/guard.ts`.

```typescript
import { requireIgnored } from "../../.shared/working-folder.ts";
requireIgnored({ committed: true });
// stdout: { "file": process.env.INPUTS_FILE ?? "", "amicus": process.env.INPUTS_AMICUS ?? "", "direction": process.env.INPUTS_DIRECTION ?? "",
//   "dirty": <newline-separated paths> }; amicus and direction are both set or both "" (one set alone: exit 1 naming it)
//   dirty: the tracked paths git status --porcelain reports changed, plus untracked paths that are not ignored,
//   gauntlet/ excluded; "" when none. Node `dirty` asks the owner when it is not empty.
```

### Phase files, standalone and as blocks: `intake/intake.yaml`, `plan-review/plan-review.yaml`, `spec-review/spec-review.yaml`

Each phase file is the workflow its own design gives. It runs on its own (`archon workflow run intake --input file=<path>`, and likewise `plan-review` and `spec-review` with their inputs) and `gauntlet-run` includes it as a block, with these properties:

- `description:` begins `Gauntlet <phase>.`, invites direct use for that phase's work and names `gauntlet-run` as the workflow for a whole run, so the chat router does not pick a single phase for a whole-run request.
- `worktree: { enabled: false }`, which a standalone run needs. Under `include:` Archon drops it with one stderr log line, `include.workflow_level_fields_dropped`, and no validation warning (PROBES.md P7); `gauntlet-run` declares its own.
- Its own `guard` node (`<phase>/scripts/guard.ts`, the shared working-folder check). A node that depends on nothing else depends on `guard`: intake's `route`, and plan review's and spec review's `docket-in`, plus spec review's `policy`. In a run the run's guard has already passed, so the phase guard repeats a git query that passes.
- `inputs:` and `returns: handoff` stay as the block's signature. The `handoff` node declares an `output_format` that names every field it prints; the fields are the phase design's (H3 to H5).
- `$INPUTS.<name>` appears in prompts, in `bash:` bodies, and in `with:` on `include:` and `workflow:` nodes only. A `script:` node reads `INPUTS_<NAME>` from the environment and binds no block input in its `with:`. No `when:` reads `$INPUTS`.

Writing's block, `write/write.yaml`, the mend's block, `mend/mend.yaml`, and landing's block, `land/land.yaml`, are blocks only, included by `gauntlet-tree` (writing, the mend), `gauntlet-remend` (the mend) and `gauntlet-run` (landing, once per round). Their descriptions say "Not for direct use"; they carry no `worktree:` key and no `guard` node, and follow the `$INPUTS` and `returns:` rules above.

Intake's routing reads a node output:

```yaml
  - id: route                          # intake's entry node, after its own guard
    depends_on: [guard]
    runtime: bun
    script: route                      # intake/scripts/route.ts: stdout { "file": process.env.INPUTS_FILE ?? "" }
    output_format: { type: object, properties: { file: { type: string } }, required: [file] }

  - id: from-file
    depends_on: [route]
    when: "$route.output.file != ''"
    # the rest as the intake design gives it

  - id: ground
    depends_on: [route]
    when: "$route.output.file == ''"
    # the rest as the intake design gives it
```

### `gauntlet-tree/gauntlet-tree.yaml` (writing's host)

The tree run, as the worktree cut design gives it, with writing included after the baseline and the mend after writing. Its `handoff` node becomes `paths`, which also prints the slug, the checkout, the stage and the brief baseline's path; a new `handoff` adds writing's and the mend's results. This step owns every field of `paths` and `write`'s `with:`, `brief` included. The description names writing and the mend. Every agent that works in the tree after the cut runs in this run. The tree run takes `stage` (the cut design's input) and runs one stage.

```yaml
nodes:
  # guard, branch check, settings, copy-in, baseline: as the worktree cut design gives them

  - id: paths                          # the cut design's handoff script, plus slug, checkout, stage and brief
    depends_on: [copy-in, baseline, settings]
    runtime: bun
    script: <print { slug, checkout, worktree, branch, items, plan, spec, stage, brief } as the cut design's handoff does;
            slug from INPUTS_SLUG, checkout from INPUTS_ITEMS with its trailing /gauntlet/items/<slug>.md removed,
            stage from INPUTS_STAGE, brief the tree path of gauntlet/baseline/<slug>.brief.txt>
    output_format: <object: slug, checkout, worktree, branch, items, plan, spec, brief (strings), stage (integer), all required>

  - id: write                          # phase 5
    depends_on: [paths]
    include: write
    with: { slug: $paths.output.slug, items: $paths.output.items, plan: $paths.output.plan,
            spec: $paths.output.spec, brief: $paths.output.brief, stage: $paths.output.stage }

  - id: mend                           # phase 6
    depends_on: [write]
    when: "$write.output.outcome == 'written'"
    include: mend
    with: { slug: $paths.output.slug, checkout: $paths.output.checkout, branch: $paths.output.branch,
            brief: $paths.output.brief, stage: $paths.output.stage, summary: $write.output.summary }

  - id: handoff                        # the tree run's returns:
    depends_on: [paths, write, mend]
    trigger_rule: none_failed_min_one_success
    runtime: bun
    script: <print { worktree, branch, items, plan, spec } from $paths.output and summary from $write.output;
            mend ran: outcome, direction and amicus from $mend.output; else outcome, direction and amicus from $write.output
            (outcome "planning" when writing handed off planning)>
    output_format: <object: worktree, branch, items, plan, spec, outcome, direction, amicus, summary (strings), all required;
                   outcome enum: ready, left, planning; the outcome carries the result of the review before landing>
```

### `mend/mend.yaml` (the mend's signature)

The mend block's signature and its hand-off. Every other node is the landing design's. It runs in a tree, so every path it reads or writes is in that tree, and it reads the checkout only by `git -C $INPUTS.checkout rev-parse HEAD`. Its waits are answered on the id of the run that includes it, the tree run's or the re-mend run's. Its agent nodes are `amicus` (the shared block of the writing design), `mend-code`, `mend-tests`, `review` and `final`, the review before landing, running the roles `amicus`, `mend-code`, `mend-tests`, `mend-review` and `final-review`. Its only writes are the rebase of the tree's branch, the mend's commits and its files in the tree's `gauntlet/mend/`.

```yaml
name: mend
description: >-
  Gauntlet mend, included by gauntlet-tree and gauntlet-remend only. Not for direct use.
inputs:
  slug: { description: The item file's slug. }
  checkout: { description: Absolute path of the owner's checkout. }
  branch: { description: The tree's branch. }
  brief: { description: Absolute tree path of gauntlet/baseline/<slug>.brief.txt. }
  stage: { description: The stage this tree wrote, counted from 1. }
  summary: { description: The plan summary and the approved revision summaries. }
returns: handoff

nodes:
  # every node but handoff: the landing design's

  - id: handoff
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [ready, left, planning] }
        direction: { type: string }    # absolute tree path of the Rework: planning direction; "" otherwise
        amicus: { type: string }       # absolute tree path of the amicus record of that direction; "" otherwise
      required: [outcome, direction, amicus]
```

### `write/write.yaml` (writing's signature)

The writing block's signature, its node `enter` and its hand-off. Every other node is the writing design's. It runs in the tree, so every path it reads or writes is in the tree. Its agents start their own sessions, primed from files.

```yaml
name: write
description: >-
  Gauntlet writing, included by gauntlet-tree only. Not for direct use.
inputs:
  slug: { description: The item file's slug. }
  items: { description: Absolute tree path of gauntlet/items/<slug>.md. }
  plan: { default: "", description: Absolute tree path of gauntlet/plans/approved/<slug>.txt, or "". }
  spec: { default: "", description: Absolute tree path of gauntlet/specs/approved/<slug>.txt, or "". }
  brief: { description: Absolute tree path of gauntlet/baseline/<slug>.brief.txt. }
  stage: { description: The stage to write, counted from 1. }
returns: handoff

nodes:
  # every node but enter and handoff: the writing design's

  - id: enter                          # the only writer of approved revisions in the tree
    bash: <cp -n the revision the owner approved at bench to gauntlet/<plans|specs>/approved/<slug>.rev<N>.txt, its
          "Revises:" and "Answers:" lines left out,
          N one above the highest present for that file, 1 when none; target present: exit non-zero naming it>

  - id: handoff
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [written, planning] }
        direction: { type: string }    # absolute tree path of the Rework: planning direction; "" when written
        amicus: { type: string }       # absolute tree path of the amicus record of that direction; "" when written
        summary: { type: string }      # the plan summary, then each approved revision summary in order of N, blank-line separated; "" when planning
      required: [outcome, direction, amicus, summary]
```

### Approved revisions

`gauntlet/plans/approved/<slug>.rev<N>.txt` and `gauntlet/specs/approved/<slug>.rev<N>.txt`, written by `enter` in the tree, copied into the checkout by `record` on landing. Each holds only its revision: the clauses it changes, each as it now reads. The approved plan or spec is `<slug>.txt` with every revision applied in order of N. Every agent in writing that needs an approved plan or spec is handed `<slug>.txt` and each of its revisions in order of N. A change too large for a revision is the owner's `back-to-planning`.

### `write/write.yaml` (the final commit and the summaries)

Node `seal` is the writing design's module node; its commit rules and message are `runtime-model-design.md`'s, "Commit model". The writers' own commits keep their messages, and so do the mend's. The review before landing shows the commit messages to the owner and landing never rewrites them. It also shows the plan summary and the summaries of the approved revision rounds, which writing's `state` lists and its hand-off `summary` carries (the owner approved those rounds; a round sent back is not listed).

### `land/land.yaml` (landing's signature)

The landing block's signature and its hand-off. Every other node is the landing design's. It runs in the checkout and reaches a tree only with `git -C $INPUTS.worktree`, `archon complete` and its node `retree`, which starts the re-mend run. It has no wait and no agent node: the owner's land is the answer given at the review before landing, in the tree run or the re-mend run. Its only writes in the checkout are the fast-forward merge and the record copy. It writes nothing in a tree. `gauntlet-run` includes it four times per stage, under the ids `land`, `land-2`, `land-3` and `land-4` (stage-prefixed after stage 1); each round takes the previous round's `worktree`, `branch` and `made`.

```yaml
name: land
description: >-
  Gauntlet landing, included by gauntlet-run only. Not for direct use.
inputs:
  slug: { description: The item file's slug. }
  round: { description: "The id of the include node that runs this round: land, land-2, land-3 or land-4, with the stage's prefix after stage 1." }
  stage: { description: The stage this round lands, counted from 1. }
  worktree: { description: Absolute path of the tree this round lands. }
  branch: { description: The branch of that tree. }
  summary: { description: The plan summary and the approved revision summaries, handed to the re-mend run. }
  made: { default: "", description: "The branches of the trees earlier rounds left behind, one per line. Landing removes them with the landed tree." }
returns: handoff

nodes:
  # every node but handoff: the landing design's

  - id: handoff
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [landed, left, planning, moved] }
        worktree: { type: string }
        branch: { type: string }
        made: { type: string }
        direction: { type: string }    # a re-mend that ended in planning: the direction's absolute tree path; "" otherwise
        amicus: { type: string }       # the amicus record of that direction; "" otherwise
      required: [outcome, worktree, branch, made, direction, amicus]
```

The checkout's tracked files change only by the fast-forward merge of `runtime-model-design.md`, "Commit model", after the owner chose land at the review before landing: the writers' commits, the final commit when `seal` made one, and the mend's commits on top of them reach the checkout as they stand.

On leave, and on any stop, every tree and its branch stay.

### `.shared/red.py` (red against the brief baseline)

The one rule for whether a test run is red. Standard library only. `write/scripts/stage.py`'s `red` and the mend's `mend/scripts/verify.py` import it as the planning ledger imports `.shared/rounds.py`, and compute no comparison themselves. Replaces the comparison inside `stage.py`'s `red`.

```python
def cut(text: str) -> str: ...
# Each line cut at its first " - ", the rest of the line dropped; listing and fence/checks.py's FENCE_CUT mode (writing
#   design) use it, so the coder's check output and red read the same text.

def listing(text: str) -> dict[str, str]: ...
# One line per test, "PASSED <id>", "FAILED <id>" or "ERROR <id>", after cut; other lines ignored.
# Returns id -> "PASSED" | "FAILED" | "ERROR".

def red(run: str, brief: str, head: str = "") -> bool: ...
# run, brief, head: test-run texts, first line as their writers give it, then the brief command's output.
# True when run timed out and neither brief nor head timed out; or a test FAILED or ERROR in run is failing in neither
#   brief nor head; or run exits non-zero with no failing line while brief exited 0 and head, when given, exited 0.
# A failure in brief or head that passes in run is not red, and a timeout already present in brief or head is not red.
#   head "": no head check.
```

Suite: `.shared/tests/test_red.py`, run as `docs/testing.md` states with the folder `.shared/tests`.

### `fence/files.py` (hidden paths)

Adds `FENCE_HIDE`: paths no tool reads, lists, searches or writes, inside readable folders included. Replaces nothing; every other `FENCE_*` list keeps its meaning.

```python
HIDE = _folders("FENCE_HIDE")   # entries as in FENCE_READ, name patterns included
# A path inside a HIDE entry is refused by every tool, read and write alike:
#   PermissionError(f"{path}: hidden (FENCE_HIDE)")
# list_directory, find_files and grep never show a hidden path, nor a folder holding only hidden paths.
# Unset: nothing hidden.
```

Suite: `fence/test_files_hide.py`, run as `docs/testing.md` states with the folder `fence`.

### Checkout fences outside intake

`plan-review/defense.mcp.json`, `plan-review/prosecutor.mcp.json`, `plan-review/reporter.mcp.json` and `plan-review/analyst.mcp.json` set no `FENCE_HIDE`, and every other `FENCE_*` value is as their phase designs give it (no checkout folder is hidden from them: owner-control keeps no failed-task folder). `spec-review/speccer.mcp.json` sets no `FENCE_HIDE` either: the `FENCE_READ` of each of its servers lists the folders the speccer and its spikers may read, and `gauntlet/specs/approved` and `tests` are not among them. `FENCE_HIDE` stays in `fence/files.py` for the coder's fence (writing design).

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| How a phase enters the run | `include:` of the phase's workflow: in `gauntlet-run.yaml`, node ids `intake`, `plan-review`, `spec-review` and `land`; in `gauntlet-tree.yaml`, node ids `write` and `mend`; in `gauntlet-run.yaml`, `land` is included four times per stage, under the ids `land`, `land-2`, `land-3` and `land-4` for stage 1 and the same under the `s2-` and `s3-` prefixes after it (heading "Stages"); in `gauntlet-remend.yaml`, node id `mend`; in `write` and `mend`, node id `amicus` (writing design) | a phase run as a `workflow:` child (the cut's `tree` node and landing's `retree` node excepted); a phase's nodes copied into `gauntlet-run.yaml` or `gauntlet-tree.yaml`; a phase description that does not name `gauntlet-run` for a whole run |
| Phase order | the `depends_on` chain in `gauntlet-run.yaml`: `guard`, `env-check`, `dirty` and `stop`, `intake`, `plan-review`, `spec-review`, `pin`, `tree`, `cut`, then `land` on `ready` and `land-2`, `land-3` and `land-4` each only after the round before hands off `moved`, then `done`, and `back` on `planning`; stage 2 and 3 repeat the chain from `pin` after `done` (heading "Stages"); in `gauntlet-tree.yaml`: `guard`, `branch-check`, `settings`, `copy-in` and `baseline`, `paths`, `write`, `mend` on `written`, `handoff` | a phase depending on any node but the one before it; any `gauntlet-run` node or phase sending the run back to an earlier phase (the re-mend run, which repeats only block `mend` in a second tree, is no such node, and `back` ends the run) |
| The run's inputs | `gauntlet-run.yaml`'s `file`, `amicus` and `direction` inputs and the run's message | an input declared for the run anywhere else; a phase reading the run's input except through `with:` |
| Run-owned settings (`worktree`, `container`, `budget`, `evidence_policy`) | `gauntlet-run.yaml`; `gauntlet-tree.yaml` for the tree run | any of them in a phase file, but `worktree: { enabled: false }` in the standalone phase files `intake/intake.yaml`, `plan-review/plan-review.yaml` and `spec-review/spec-review.yaml` |
| The working-folder check | `requireIgnored` in `.shared/working-folder.ts`, called with option `committed` by node `guard` of `gauntlet-run` in the checkout, once per run, ahead of every phase; by the `guard` node of each standalone phase (`intake/`, `plan-review/`, `spec-review/`); by node `guard` of `gauntlet-tree` in the tree and of `gauntlet-remend` in the second tree | a guard node or `guard.ts` in `write/`, `mend/` or `land/`; a second statement of the check; option `committed` passed by any other guard |
| The run-start checks (test settings, an `.archon/config.yaml` untracked, ignored or differing from `HEAD`, a configured remote, the checkout's dirty paths) | node `env-check` of `gauntlet-run`, a bash node, for the test settings, the config and the remote `worktree.remote` names, `origin` when unset (configuration only, no network call); `gauntlet-run/scripts/guard.ts` and node `dirty` for the dirty paths | the shared working-folder check; any phase's guard; a `GAUNTLET_*` variable read by a `script:` node |
| The hand-off between phases | each phase's `returns: handoff` node, whose `output_format` declares every field, read by the next node's `with:` or script as `$<phase>.output.<field>`; writing's read by the tree run's `mend` and `handoff`, the mend's by its `handoff` | a phase reading another phase's inner node, a file or a path the previous phase did not hand off |
| Inputs inside a phase block | `$INPUTS.<name>` in prompts, in `bash:`, and in `with:` on `include:` and `workflow:` nodes; `INPUTS_<NAME>` in scripts; a node output in `when:` | `$INPUTS` in a `when:`; `$INPUTS.<name>` in an inline `script:`; a block input bound in the `with:` of a script node |
| Where the owner answers | `gauntlet-run`'s id for the run-start `dirty` ask, intake, plan review and spec review; the tree run's id for writing's `bench` and the mend's `ask` (the review before landing included), the re-mend run's id for the mend's `ask` in a second tree | any pause of writing or the mend placed in `gauntlet-run`; a pause of landing anywhere: block `land` holds none |
| Agents and writes in the tree after the cut | blocks of `gauntlet-tree`, the tree run: `write` and `mend`; block `mend` of `gauntlet-remend`, the re-mend run, in a second tree | an agent node in `land/` or in any other `gauntlet-run` block after `cut`; a rebase, test run or commit in a tree from `gauntlet-run`; a node field, sub-run or fence root set to reach an existing tree from another run |
| A wrong plan or spec found in writing | an approved revision, tried and approved inside writing's one loop, when the owner's direction asks for it | intake, plan review or spec review run again but by the owner's back to planning; `<slug>.txt` edited, moved or copied whole |
| Writing to the tree's `approved/` folders | the worktree cut design's Homes row "Approved files in the tree" (`copy-in` of the tree run, and writing's `enter` for `<slug>.rev<N>.txt`); in a second tree, `copy-in` of the re-mend run (landing design) | any agent or other node writing there; any other file name there; a revision in the checkout but landing's record copy |
| Reading the approved plan or spec in writing | `<slug>.txt` and each `<slug>.rev<N>.txt` in order of N | an agent handed `<slug>.txt` alone once a revision exists |
| Ending the run for the owner's back to planning | the owner's `back-to-planning` choice at the amicus (writing design) or the review before landing (landing design), handed off as `outcome` `planning` with the direction and the amicus record; node `back` of the stage prints the command and sets the slug's plan and spec files aside (heading "Back to planning") | a node failing or cancelling the run for it; a line-count or size threshold; an agent choosing to end the run; Gauntlet removing the tree or its branch |
| The back-to-planning files and command | `gauntlet-run/scripts/back.py`: `gauntlet/back/<slug>.<n>.amicus.md` and `.direction.md` in the checkout, and the one command it prints; read by plan review's block inputs `amicus` and `direction` (plan review design) | any other writer of `gauntlet/back/`; a second statement of the command; a plan review that edits or deletes either file |
| Stages | this design's heading "Stages": the bound, the node ids, the order and the per-stage `done` node; the plan marker is the plan review design's (`Plan grammar`), the cut per stage the worktree cut design's, the stage's writing the writing design's, its review and landing the landing design's | a second statement of the bound or the ids; a stage cutting its tree before the stage before it landed; a node count past the bound |
| The item file | the intake design's `intake/scripts/items.py`: `gauntlet/items/<slug>.md`, deferred items in `gauntlet/deferred/<slug>-later.md`, the hand-off `items` | any phase deriving a path from another file; a phase reading `gauntlet/intake/` |
| Whether a test run is red, and the cut at ` - ` | `.shared/red.py`, called by writing's `stage.py red` and the mend's `mend/scripts/verify.py`; its `cut` also by `fence/checks.py`'s `FENCE_CUT` mode | any other comparison of test listings; a listing parsed in `write/`, `mend/` or `land/`; another cut of a test line |
| The final commit | `runtime-model-design.md`, heading "Commit model"; the node is writing's `seal` | a final commit on a clean tree; any other message on the final commit; a message rewritten in landing |
| The summaries shown with the review before landing | writing's `state` (the approved rounds) and its hand-off `summary`: the plan summary, then each approved revision summary in order of N | a round the owner sent back listed; any other node composing them |
| Commits on the tree's branch past the writers' commits and `seal` | `runtime-model-design.md`, heading "Commit model"; the mender is named by the owner's direction, each mend read by `review` (role `mend-review`) | any other commit past `seal`; a reset, amend, squash or dropped commit on the branch, the rebase excepted |
| Landing on the checkout | `runtime-model-design.md`, heading "Commit model"; the node is landing's `merge`, in the round whose tree the owner chose to land at the review before landing; what counts as a move of the checkout is that node's | any other Gauntlet write to the checkout's tracked files, branch or `HEAD`; a squash or merge commit; a push or PR |
| The tree's records in the checkout | landing's record copy of the landed tree into the checkout's `gauntlet/`, after the merge | any other writer; a copy before the merge or on leave |
| Removing the trees and their branches | landing's last node, `archon complete <branch> --force` for every tree landing made, after the record copy | Gauntlet removing them on `back`, leave or any stop |
| Refusing a read inside a readable folder | `FENCE_HIDE` in `fence/files.py` | any other read check; `FENCE_DENY` widened to reads |
| Rounds, verdict parsing and the owner's cases in writing | `.shared/rounds.py`, with writing's verdicts in a `write/scripts/ledger.py` `Profile` (spec review design) | any of it computed in a `write/` node, prompt or command |
| Steering screening in writing | the `screen` workflow (spec review design), included by writing | any other steering check before a reviewer reads a round file |
| What each writer can see | `fence/files.py` (plan review design), through writing's `*.mcp.json` and the mend's `mend/mend-code.mcp.json` and `mend/mend-tests.mcp.json` | any other confinement of the test writers to `tests/` or of the code writers away from `tests/` |
| Writing's roles | `write/commands/<role>.md`; the amicus in `amicus/commands/amicus.md` (writing design) | a `write/` node using or restating a role file of `plan-review/` or `spec-review/`; a `write/` node resuming a session of another block |

## Order

1. The run's head: `gauntlet-run/gauntlet-run.yaml` (name, inputs, worktree, nodes `guard`, `env-check`, `dirty`, `stop`, `intake`, `plan-review`, `spec-review`), `gauntlet-run/scripts/guard.ts`, `gauntlet-run/fixtures/dirty.stubs.yaml` (`dirty` asks, `go-on`, `intake` reached) and `gauntlet-run/fixtures/dirty-leave.stubs.yaml` (`leave`, `stop` cancels, `intake` not reached). Needs the intake design's `.shared/working-folder.ts` and the three phase blocks. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
2. Back to planning: `gauntlet-run/scripts/back.py`, `gauntlet-run/tests/test_back.py`. Needs the worktree cut design's `.shared/pin.py` (its step 1). Agent: `builder`.
3. Writing in the tree run: `gauntlet-tree/gauntlet-tree.yaml` (nodes `paths`, `write`, `handoff`, the description; `paths` prints `checkout`, `stage` and `brief` and `write` binds `brief` and `stage`), `gauntlet-tree/fixtures/tree.stubs.yaml`, `gauntlet-tree/fixtures/planning.stubs.yaml` (writing hands off `planning`, `handoff` reached). Needs the worktree cut design's tree run and the writing design's `write/write.yaml`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
4. The stage chain and the run's end: `gauntlet-run/gauntlet-run.yaml` (`cut`'s `outcome`, `direction`, `amicus` and `summary`, nodes `done` and `back`, the stage-prefixed nodes, the description), `gauntlet-run/fixtures/cut.stubs.yaml`, `gauntlet-run/fixtures/planning.stubs.yaml` (the tree run hands off `planning`, `back` runs, the run completes), `gauntlet-run/fixtures/staged.stubs.yaml` (stage 1 lands, stage 2 cut and landed). Needs steps 1, 2 and 3 and the worktree cut design's step 3. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
5. Hidden paths in the fence: `fence/files.py` (`FENCE_HIDE`), `fence/test_files_hide.py`. Needs the plan review design's step 1. Agent: `builder`.
6. Red rule: `.shared/red.py`, `.shared/tests/test_red.py`. Writing's `write/scripts/stage.py` and the mend's `mend/scripts/verify.py` need it. Agent: `builder`.
7. The mend in the tree run: `gauntlet-tree/gauntlet-tree.yaml` (node `mend`, `handoff` prints the mend's `outcome`, `direction` and `amicus`, the description), `gauntlet-tree/fixtures/tree.stubs.yaml` (the mend hands off `ready`), `gauntlet-tree/fixtures/left.stubs.yaml` (the mend hands off `left`), `gauntlet-tree/fixtures/planning.stubs.yaml` (`mend` not reached). Needs step 3 and the landing design's `mend/mend.yaml`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
8. Landing in the run: `gauntlet-run/gauntlet-run.yaml` (nodes `land`, `land-2`, `land-3` and `land-4`, the description), `gauntlet-run/fixtures/landed.stubs.yaml` (landing hands off `landed`), `gauntlet-run/fixtures/left.stubs.yaml` (landing hands off `left`), `gauntlet-run/fixtures/mend-left.stubs.yaml` (the tree run hands off `left`, `land` not reached), `gauntlet-run/fixtures/moved.stubs.yaml` (`land` hands off `moved`, `land-2` hands off `landed`, `land-3` not reached), `gauntlet-run/fixtures/moved-twice.stubs.yaml` (`land` and `land-2` hand off `moved`, `land-3` hands off `landed`, `land-4` not reached), `gauntlet-run/fixtures/moved-thrice.stubs.yaml` (`land`, `land-2` and `land-3` hand off `moved`, `land-4` hands off `landed`). Needs steps 4 and 7 and the landing design's `land/land.yaml` (its step 6) and `gauntlet-remend/gauntlet-remend.yaml` (its step 5). `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
