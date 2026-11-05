Status: proposed.

# Gauntlet

## Why

Gauntlet is one run, `gauntlet-run`, started by one command: `archon workflow run gauntlet-run`, with the owner's message and an optional `--input file=<path>`, or the same text typed in the Archon web UI. Every phase runs inside that run, in order, and each phase hands its result to the next. The owner answers the run-start ask (when the checkout holds changes that will not reach the tree) and the pauses of intake, plan review, spec review and landing on that run's id, and the pauses of writing and the mend on the id of the tree run, the child run the cut starts in the tree, or of the re-mend run, the child run landing starts in a second tree when the checkout has moved; `archon workflow get <run id> --json` gives it at `.metadata.approval.childRunId`. No phase goes back to an earlier phase. This file covers how the phases join. Each phase's own design covers its inside, and nothing here restates it.

The phases, in run order:

1. **Intake** (`gauntlet-intake-design.md`). Turns the owner's task into `gauntlet/tasks/<slug>.md`, from a file the owner wrote or through a conversation with Clerk that ends on the owner's approval. Hands off `{ task }`.
2. **Plan review** (`plan-review-design.md`). The defense decides whether the task needs a plan and writes one. The prosecutor tries it round by round, and the owner approves the plain-English summary. Hands off `{ task, plan }`, with `plan` set to `""` when no plan is needed.
3. **Spec review** (`spec-review-design.md`). The speccer decides whether tests need speccing and writes the specs. The arbiter tries them, and the owner approves them or confirms that nothing is testable. Hands off `{ task, plan, spec, outcome }`.
4. **Worktree cut** (`worktree-cut-design.md`). Cuts one worktree from the checkout's `HEAD`, copies the approved files in and records the brief test baseline. Hands off `{ worktree, branch, base, task, plan, spec, outcome, verdict, line, summary }`, the last four from the tree run's `handoff`.
5. **Writing** (the writing design). Runs in the tree, as block `write` of the tree run, after the baseline. Test writers write the tests from the approved specs, then code writers write the code. A juror rules whether the tests, the code, the spec or the plan is wrong, or that the plan is defective. A wrong plan or spec is revised inside writing, as an approved revision; a defective plan ends the run. Hands off `{ outcome, verdict, summary }` to the tree run's `mend` and `handoff`, `summary` being the plan summary and the summaries of the approved revisions.
6. **Mend** (`landing-design.md`). Runs in the tree, as block `mend` of the tree run, after `write`, when writing hands off `written`. It reads the checkout's `HEAD` with `git -C <checkout>`, rebases the tree's branch onto it, reruns the brief test command when the checkout has moved past base, and mends a red on the rebased tree: a juror rules each red, a code or test mender commits the mend on top of the branch's last commit, and a reviewer reads every mend. The owner is asked, on the tree run's id, only when the juror rules defective or the mend stalls, and answers with guidance, a rerun or leave. It runs git, the brief test command, its verify script and, only in the repair, four agents. Hands off `{ outcome, line }`, `outcome` `ready` or `left`, to the tree run's `handoff`.
7. **Landing** (`landing-design.md`). Runs in the checkout as block `land` of `gauntlet-run`, after `cut`, when the tree run hands off `ready`, and reaches a tree only with `git -C <worktree>`, `archon complete` and the re-mend run. It checks that the tree's branch still fast-forwards the checkout. When the checkout has moved past it, landing re-mends: it starts the re-mend run `gauntlet-remend` in a second tree, which runs block `mend` only (rebase, tests, repair) on a branch pinned at the first tree's tip, then asks the owner. It re-mends at most twice, each round an `include` of `land` under its own id (`land`, `land-2`, `land-3`), and a third move stops the run, naming the move. It shows the owner the mend's test line, the plan summary and the approved revision summaries, the diff stat and the commit messages and waits for land or leave. On land it fast-forwards the checkout, copies the landed tree's records into the checkout's `gauntlet/` and removes every tree it made and their branches. It runs git, Archon's CLI and one script, and no agent. Hands off `{ outcome, worktree, branch, line, made }`, `outcome` `landed`, `left` or `moved`, the last four fields feeding the next round.

The run ends at the last round of block `land` that runs (`land`, `land-2` or `land-3`) when the tree run hands off `ready`, after `cut` when it hands off `left`, and at node `kill`, cancelled, when it hands off `defective`. A cancelled phase block ends the run cancelled at its own node: plan review's and spec review's `vacate` cancel when `filing` reports all twelve slots retired, with no node past it run and no record in `gauntlet/failed/`; writing has no `vacate`. A tree run that ends cancelled fails `gauntlet-run`'s node `tree`, so `cut` and everything after it is not reached; the tree and its branch stay, and `archon workflow resume <run id>` picks the run up at `tree`.

The copies the phase designs once held, each resolved (D-06; rulings in `.planning/phases/1/REVIEW-pass1.md`):

- Standalone phase workflows: intake, plan review and spec review are each a workflow started on its own and a block of `gauntlet-run`. Each description invites direct use and names `gauntlet-run` as the pick for a whole run, so Archon's router picks a phase only for that phase's work. Resolved by G-12: `gauntlet-design.md:138`, `gauntlet-intake-design.md:152`, `plan-review-design.md:242`, `spec-review-design.md:325`.
- `worktree: enabled: false`: 4, in `intake/intake.yaml`, `plan-review/plan-review.yaml`, `spec-review/spec-review.yaml` and `gauntlet-run/gauntlet-run.yaml`. A phase run on its own needs it; under `include:` Archon drops a composed file's `worktree:` with one stderr log line, `include.workflow_level_fields_dropped`, and no validation warning (PROBES.md P7). Resolved by G-12: `gauntlet-design.md:139`, `gauntlet-intake-design.md:157`, `plan-review-design.md:249`, `spec-review-design.md:332`.
- Working-folder guard nodes in the checkout: 4, `gauntlet-run/scripts/guard.ts` and `intake/scripts/guard.ts`, `plan-review/scripts/guard.ts` and `spec-review/scripts/guard.ts`, all on `.shared/working-folder.ts`. A phase run on its own needs its guard; in a run the phase guard repeats the run guard's ignore check, which is a git query. The run's own guard adds the run-start checks (G-31, G-32) that no phase guard holds. `gauntlet-tree/scripts/guard.ts` and `gauntlet-remend/scripts/guard.ts` run in a worktree. Resolved by G-12: `gauntlet-design.md:140`, `gauntlet-intake-design.md:165`, `plan-review-design.md:256`, `spec-review-design.md:339`.
- Hand-off contracts: 3 `handoff` nodes, each declaring an `output_format` that names every field it prints. Resolved: `gauntlet-design.md:141`, `gauntlet-intake-design.md:260`, `plan-review-design.md:413`, `spec-review-design.md:503`.
- `$INPUTS` left of a `when:` comparison: none. Intake's `route` prints the input as an output and `from-file` and `ground` read `$route.output.file`. Resolved: `gauntlet-intake-design.md:179`, `:186`.
- Inline `script:` hand-offs that print an input: none. Plan review's and spec review's `handoff` read `INPUTS_<NAME>` from the environment. Resolved: `plan-review-design.md:407`, `spec-review-design.md:495`.
- Writers of the tree's `gauntlet/plans/approved/` and `gauntlet/specs/approved/`: `copy-in` for `<slug>.txt` and `<slug>-summary.md`, and writing's `enter` for `<slug>.rev<N>.txt`. Resolved: `gauntlet-design.md:254`, `writing-design.md:366`.
- Places a node runs in the tree: 2, the tree run and, for the mend only, the re-mend run (G-45), each in its own tree. An agent runs in its run's checkout, and no node field sets another folder. An `include:` block has no checkout of its own. `isolation:`, valid only on a `workflow:` node, gives a child run its parent's checkout or a fresh worktree on a new branch cut from base, never an existing tree; the re-mend run's second tree is a new worktree on a branch pinned at the first tree's tip. `fence/files.py` and `fence/checks.py` root at `CLAUDE_PROJECT_DIR`, the agent's own folder: no fence config sets it, and both servers exit 2 at start when its real path differs from the real path of their working folder (PROBES.md P2). Writing and the mend are therefore blocks of `gauntlet-tree`, and the mend again a block of `gauntlet-remend`, never of `gauntlet-run`. Resolved by G-02: `gauntlet-intake-design.md:28`, `:122`.
- Fences that read the checkout outside intake: 3 set `FENCE_READ=.` and `FENCE_HIDE=gauntlet/failed`: `plan-review/defense.mcp.json`, `plan-review/prosecutor.mcp.json` and `plan-review/reporter.mcp.json`. `spec-review/speccer.mcp.json` and the spiker's server list their readable folders and none holds `gauntlet/failed/`, `gauntlet/specs/approved/` or `tests/`. `fence/files.py` applies `FENCE_DENY` to writes only. Resolved by G-03: `spec-review-design.md:281`-`:286`.
- Role files writing would reuse: none. Commands resolve only from a workflow's own `commands/`, so writing has its own `write/commands/`. Resolved: `writing-design.md:19`, `gauntlet-design.md:391`.
- Comparisons of a test run against the brief baseline: 1, `.shared/red.py`, imported by `red` of `write/scripts/stage.py` and by `mend/scripts/verify.py`. Resolved: `gauntlet-design.md:308`, `:380`, `landing-design.md:354`.
- Copies of the tree's records in the checkout: landing's `record` is the only writer, and writes revisions and writing's round records there. Resolved: `landing-design.md:265`, `gauntlet-design.md:385`.

The tree holds none of these yet. The only parts built are `fence/` and `spec-review/commands/arbiter.md`.

## Modules

### `gauntlet-run/gauntlet-run.yaml` (the run's head)

The one workflow the owner starts. It declares the run's input, checks the working folder and the repository's test settings once, asks the owner about changes that will not reach the tree, and includes the three earlier phases in order. The worktree cut design gives the nodes `pin`, `tree` and `cut` that follow, and the description. This module fills the phases' entry, which the worktree cut design leaves open.

```yaml
name: gauntlet-run
inputs:
  file:
    default: ""
    description: Path of a task file the owner wrote. Blank sends the run's message to Clerk.
worktree:
  enabled: false                       # the run's one worktree setting; the phase files declare it too and Archon drops theirs under include:

nodes:
  - id: guard                          # once per run, in the checkout, before any phase
    runtime: bun
    script: guard
    output_format: { type: object, properties: { file: { type: string }, dirty: { type: string } }, required: [file, dirty] }

  - id: dirty                          # the owner, only when the checkout holds changes that will not reach the tree
    depends_on: [guard]
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
    depends_on: [guard, dirty, stop]
    trigger_rule: none_failed_min_one_success
    include: intake
    with: { file: $guard.output.file }

  - id: plan-review
    depends_on: [intake]
    include: plan-review
    with: { task: $intake.output.task }

  - id: spec-review
    depends_on: [plan-review]
    include: spec-review
    with: { task: $plan-review.output.task, plan: $plan-review.output.plan }

  # pin, tree, cut: as the worktree cut design gives them; pin depends on [spec-review].
  # cut also prints outcome, verdict, line and summary from $tree.output; its output_format adds
  # outcome (enum: ready, left, defective), verdict (string), line (string) and summary (string), all required.

  - id: land                           # phase 7, round 1, in the checkout
    depends_on: [cut]
    when: "$cut.output.outcome == 'ready'"
    include: land
    with: { slug: $pin.output.slug, round: land, remend: "yes", worktree: $cut.output.worktree,
            branch: $cut.output.branch, line: $cut.output.line, summary: $cut.output.summary }

  - id: land-2                         # round 2, only when round 1 found the checkout moved while it waited
    depends_on: [land]
    when: "$land.output.outcome == 'moved'"
    include: land
    with: { slug: $pin.output.slug, round: land-2, remend: "yes", worktree: $land.output.worktree,
            branch: $land.output.branch, line: $land.output.line, summary: $cut.output.summary, made: $land.output.made }

  - id: land-3                         # round 3, the last: a move found here stops the run
    depends_on: [land-2]
    when: "$land-2.output.outcome == 'moved'"
    include: land
    with: { slug: $pin.output.slug, round: land-3, remend: "no", worktree: $land-2.output.worktree,
            branch: $land-2.output.branch, line: $land-2.output.line, summary: $cut.output.summary,
            made: $land-2.output.made }

  - id: fail                           # the only writer of the checkout's gauntlet/failed/
    depends_on: [cut]
    when: "$cut.output.outcome == 'defective'"
    bash: <cp -n $cut.output.verdict to gauntlet/failed/$pin.output.slug.txt of the checkout;
          target present: exit non-zero naming it, nothing copied. Then move the slug's approved plan and spec in the
          checkout (their files under gauntlet/plans/approved/ and gauntlet/specs/approved/: text, summary and recorded task hash)
          aside into the folder gauntlet/failed/$pin.output.slug.approved/, so a rerun on the slug re-hears them>

  - id: kill                           # the run's end on a defective plan
    depends_on: [fail]
    cancel: "The juror ruled the plan defective. The grounds are in the checkout's gauntlet/failed/, under the task's slug. Start a new gauntlet-run that names the slug."
```

The description is the worktree cut design's, with writing, the mend and landing named among the phases it takes the task through.

The run's message (`$ARGUMENTS`) reaches Clerk unchanged, because an included block runs inside the run. The pauses of intake, plan review, spec review and landing are answered on the run's own id, and writing's and the mend's on the tree run's id, or on the re-mend run's id for the mend of a second tree. A failed phase fails the run, and `archon workflow resume <run id>` picks the run up there. A defective plan cancels the run at `kill`; the tree and its branch stay where they are, for the owner to inspect or remove with `archon complete <branch> --force`. An owner's leave at the mend's ask, in either run, or at landing's gate ends the run with every tree and branch kept the same way; a leave at the mend of the tree run ends it after `cut`, with no node past `cut` run.

### `gauntlet-run/scripts/guard.ts`

The run's own guard, which runs in the checkout before any phase. It runs the shared working-folder check, then the run-start checks, which live in this script and never in `.shared/working-folder.ts`, because the phases run on their own and share that check. It also passes the run's `file` input on as an output, so the intake block receives it as a node reference. `intake/scripts/guard.ts`, `plan-review/scripts/guard.ts` and `spec-review/scripts/guard.ts` are the phases' own guards, each the two lines of `gauntlet-tree/scripts/guard.ts`.

```typescript
import { requireIgnored } from "../../.shared/working-folder.ts";
requireIgnored();
// Run-start checks, exit 1 naming the cause on stderr:
//   GAUNTLET_TEST_COMMAND or GAUNTLET_TEST_BRIEF_COMMAND unset or blank;
//   GAUNTLET_TEST_TIMEOUT set but not a positive integer;
//   .archon/config.yaml of the checkout with uncommitted changes.
// The variables are read from the environment; the repository's env: reaches bash nodes (worktree-cut-design.md:33),
//   and whether it reaches a script node is unmeasured.
// stdout: { "file": process.env.INPUTS_FILE ?? "", "dirty": <newline-separated paths> }
//   dirty: the tracked paths git status --porcelain reports changed, plus untracked paths that are not ignored,
//   gauntlet/ excluded; "" when none. Node `dirty` asks the owner when it is not empty.
```

### Phase files, standalone and as blocks: `intake/intake.yaml`, `plan-review/plan-review.yaml`, `spec-review/spec-review.yaml`

Each phase file is the workflow its own design gives. It runs on its own (`archon workflow run intake --input file=<path>`, and likewise `plan-review` and `spec-review` with their inputs) and `gauntlet-run` includes it as a block, with these properties:

- `description:` begins `Gauntlet <phase>.`, invites direct use for that phase's work and names `gauntlet-run` as the workflow for a whole run, so the chat router does not pick a single phase for a whole-run request.
- `worktree: { enabled: false }`, which a standalone run needs. Under `include:` Archon drops it with one stderr log line, `include.workflow_level_fields_dropped`, and no validation warning (PROBES.md P7); `gauntlet-run` declares its own.
- Its own `guard` node (`<phase>/scripts/guard.ts`, the shared working-folder check). A node that depends on nothing else depends on `guard`: intake's `route`, and plan review's and spec review's `docket-in`, plus spec review's `policy`. In a run the run's guard has already passed, so the phase guard repeats a git query that passes.
- `inputs:` and `returns: handoff` stay as the block's signature. The `handoff` node declares an `output_format` that names every field it prints:
  - intake: `{ task }`
  - plan review: `{ task, plan }`
  - spec review: `{ task, plan, spec, outcome }`
- `$INPUTS.<name>` appears in prompts, in `bash:` bodies, and in `with:` on `include:` and `workflow:` nodes only. A `script:` node reads `INPUTS_<NAME>` from the environment and binds no block input in its `with:`. No `when:` reads `$INPUTS`.

Writing's block, `write/write.yaml`, the mend's block, `mend/mend.yaml`, and landing's block, `land/land.yaml`, are blocks only, included by `gauntlet-tree` (writing, the mend), `gauntlet-remend` (the mend) and `gauntlet-run` (landing, three times). Their descriptions say "Not for direct use"; they carry no `worktree:` key and no `guard` node, and follow the `$INPUTS` and `returns:` rules above.

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

The tree run, as the worktree cut design gives it, with writing included after the baseline and the mend after writing. Its `handoff` node becomes `paths`, which also prints the slug, the checkout, and the brief baseline's path; a new `handoff` adds writing's and the mend's results. This step owns every field of `paths` and `write`'s `with:`, `brief` included. The description names writing and the mend. Every agent that works in the tree after the cut runs in this run.

```yaml
nodes:
  # guard, branch check, settings, copy-in, baseline: as the worktree cut design gives them

  - id: paths                          # the cut design's handoff script, plus slug, checkout and brief
    depends_on: [copy-in, baseline]
    runtime: bun
    script: <print { slug, checkout, worktree, branch, task, plan, spec, brief } as the cut design's handoff does;
            slug from INPUTS_SLUG, checkout from INPUTS_TASK with its trailing /gauntlet/tasks/<slug>.md removed,
            brief the tree path of gauntlet/baseline/<slug>.brief.txt>
    output_format: <object: slug, checkout, worktree, branch, task, plan, spec, brief (strings), all required>

  - id: write                          # phase 5
    depends_on: [paths]
    include: write
    with: { slug: $paths.output.slug, task: $paths.output.task, plan: $paths.output.plan,
            spec: $paths.output.spec, brief: $paths.output.brief }

  - id: mend                           # phase 6
    depends_on: [write]
    when: "$write.output.outcome == 'written'"
    include: mend
    with: { slug: $paths.output.slug, checkout: $paths.output.checkout, branch: $paths.output.branch,
            brief: $paths.output.brief }

  - id: handoff                        # the tree run's returns:
    depends_on: [paths, write, mend]
    trigger_rule: none_failed_min_one_success
    runtime: bun
    script: <print { worktree, branch, task, plan, spec } from $paths.output and verdict and summary from $write.output;
            mend ran: outcome and line from $mend.output; else outcome "defective" and line "">
    output_format: <object: worktree, branch, task, plan, spec, outcome, verdict, line, summary (strings), all required;
                   outcome enum: ready, left, defective>
```

### `mend/mend.yaml` (the mend's signature)

The mend block's signature and its hand-off. Every other node is the landing design's. It runs in a tree, so every path it reads or writes is in that tree, and it reads the checkout only by `git -C $INPUTS.checkout rev-parse HEAD`. Its waits are answered on the id of the run that includes it, the tree run's or the re-mend run's. Its only agent nodes are `juror`, `mend-code`, `mend-tests` and `review`, running the roles `mend-juror`, `mend-code`, `mend-tests` and `mend-review`. Its only writes are the rebase of the tree's branch, the mend's commits and its files in the tree's `gauntlet/mend/`.

```yaml
name: mend
description: >-
  Gauntlet mend, included by gauntlet-tree and gauntlet-remend only. Not for direct use.
inputs:
  slug: { description: The task's slug. }
  checkout: { description: Absolute path of the owner's checkout. }
  branch: { description: The tree's branch. }
  brief: { description: Absolute tree path of gauntlet/baseline/<slug>.brief.txt. }
returns: handoff

nodes:
  # every node but handoff: the landing design's

  - id: handoff
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [ready, left] }
        line: { type: string }         # the test line landing's gate shows; "" when left
      required: [outcome, line]
```

### `write/write.yaml` (writing's signature)

The writing block's signature, its node `enter` and its hand-off. Every other node is the writing design's. It runs in the tree, so every path it reads or writes is in the tree. Its agents start their own sessions, primed from files.

```yaml
name: write
description: >-
  Gauntlet writing, included by gauntlet-tree only. Not for direct use.
inputs:
  slug: { description: The task's slug. }
  task: { description: Absolute tree path of gauntlet/tasks/<slug>.md. }
  plan: { default: "", description: Absolute tree path of gauntlet/plans/approved/<slug>.txt, or "". }
  spec: { default: "", description: Absolute tree path of gauntlet/specs/approved/<slug>.txt, or "". }
  brief: { description: Absolute tree path of gauntlet/baseline/<slug>.brief.txt. }
returns: handoff

nodes:
  # every node but enter and handoff: the writing design's

  - id: enter                          # the only writer of approved revisions
    bash: <cp -n the revision the owner approved at bench to gauntlet/<plans|specs>/approved/<slug>.rev<N>.txt, its
          "Revises:" and "Answers:" lines left out,
          N one above the highest present for that file, 1 when none; target present: exit non-zero naming it>

  - id: handoff
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [written, defective] }
        verdict: { type: string }      # absolute tree path of the juror's defective ruling; "" when written
        summary: { type: string }      # the plan summary, then each approved revision summary in order of N, blank-line separated; "" when written is false
      required: [outcome, verdict, summary]
```

### Approved revisions

`gauntlet/plans/approved/<slug>.rev<N>.txt` and `gauntlet/specs/approved/<slug>.rev<N>.txt`, in the tree only. Each holds only its revision: the clauses it changes, each as it now reads. The approved plan or spec is `<slug>.txt` with every revision applied in order of N. Every agent in writing that needs an approved plan or spec is handed `<slug>.txt` and each of its revisions in order of N. A juror ruling that a change is too large for a revision is the verdict `defective`.

### `write/write.yaml` (the final commit and the summaries)

Node `seal` is the writing design's. It makes the `<slug>: final` commit only when the tree holds uncommitted changes, with `git commit -F -`, and makes no commit on a clean tree, the usual case once every writer has committed its own block. The writers' own commits keep their messages. The mend's commits sit on top of the branch's last commit with messages of their own. Landing shows the commit messages at the owner's gate and never rewrites them. The gate also shows the plan summary and the summaries of the approved revision rounds, which writing's `state` lists and its hand-off `summary` carries (the owner approved those rounds; a round sent back is not listed).

### `land/land.yaml` (landing's signature)

The landing block's signature and its hand-off. Every other node is the landing design's. It runs in the checkout and reaches a tree only with `git -C $INPUTS.worktree`, `archon complete` and its node `retree`, which starts the re-mend run. Its one wait, `gate`, the owner's land or leave, is answered on `gauntlet-run`'s id, once per round that reaches it. It has no agent node. Its only writes in the checkout are the fast-forward merge and the record copy. It writes nothing in a tree. `gauntlet-run` includes it three times, under the ids `land`, `land-2` and `land-3`; each round takes the previous round's `worktree`, `branch`, `line` and `made`.

```yaml
name: land
description: >-
  Gauntlet landing, included by gauntlet-run only. Not for direct use.
inputs:
  slug: { description: The task's slug. }
  round: { description: "The id of the include node that runs this round: land, land-2 or land-3." }
  remend: { description: "yes when this round may start a re-mend, no in the last round." }
  worktree: { description: Absolute path of the tree this round lands. }
  branch: { description: The branch of that tree. }
  line: { description: The mend's test line for that tree. }
  summary: { description: The plan summary and the approved revision summaries, shown at the gate. }
  made: { default: "", description: "The branches of the trees earlier rounds left behind, one per line." }
returns: handoff

nodes:
  # every node but handoff: the landing design's

  - id: handoff
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [landed, left, moved] }
        worktree: { type: string }
        branch: { type: string }
        line: { type: string }
        made: { type: string }
      required: [outcome, worktree, branch, line, made]
```

The checkout's tracked files change only by `git merge --ff-only <branch>`, after the owner chooses land. No squash and no merge commit: the writers' commits, `<slug>: final` when `seal` made one, and the mend's commits on top of them reach the checkout as they stand after the mend's rebase and repair, in the tree run or the re-mend run.

On leave, and on any stop, every tree and its branch stay.

### `.shared/red.py` (red against the brief baseline)

The one rule for whether a test run is red. Standard library only. `write/scripts/stage.py`'s `red` and the mend's `mend/scripts/verify.py` import it as the planning ledger imports `.shared/rounds.py`, and compute no comparison themselves. Replaces the comparison inside `stage.py`'s `red`.

```python
def listing(text: str) -> dict[str, str]: ...
# One line per test, "PASSED <id>", "FAILED <id>" or "ERROR <id>", text from " - " on dropped; other lines ignored.
# Returns id -> "PASSED" | "FAILED" | "ERROR".

def red(run: str, brief: str, head: str = "") -> bool: ...
# run, brief, head: test-run texts, first line as their writers give it, then the brief command's output.
# True when run timed out and neither brief nor head timed out; or a test FAILED or ERROR in run is failing in neither
#   brief nor head; or run exits non-zero with no failing line while brief exited 0 and head, when given, exited 0.
# A failure in brief or head that passes in run is not red, and a timeout already present in brief or head is not red.
#   head "": no head check.
```

Suite: `.shared/tests/test_red.py`, run as `docs/testing.md` states with the folder `.shared/tests`.

### `intake/scripts/ground.ts` and `intake/commands/clerk.md` (failed slugs)

The intake design's `ground` and Clerk, with one addition each, so a new task can name a slug whose run ended defective.

```typescript
// ground.ts — node `ground`: prints task-format.md, the names in gauntlet/tasks/, then the names in
// gauntlet/failed/ of the checkout (none when absent)
```

```
clerk.md, added rule: the owner's idea names a slug listed under gauntlet/failed/: read gauntlet/failed/<slug>.txt and
gauntlet/tasks/<slug>.md before the first reply. The new task takes a new slug.
```

The file route copies the owner's file verbatim and reads no failure record. Only Clerk reads `gauntlet/failed/`.

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

`plan-review/defense.mcp.json`, `plan-review/prosecutor.mcp.json` and `plan-review/reporter.mcp.json` each set `FENCE_HIDE=gauntlet/failed`, with every other `FENCE_*` value as their phase designs give it. `spec-review/speccer.mcp.json` sets no `FENCE_HIDE`: its `FENCE_READ` lists the folders the speccer may read, and `gauntlet/failed` is not among them.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| How a phase enters the run | `include:` of the phase's workflow: in `gauntlet-run.yaml`, node ids `intake`, `plan-review`, `spec-review` and `land`; in `gauntlet-tree.yaml`, node ids `write` and `mend`; in `gauntlet-run.yaml`, `land` is included three times, under the ids `land`, `land-2` and `land-3`; in `gauntlet-remend.yaml`, node id `mend` | a phase run as a `workflow:` child (the cut's `tree` node and landing's `retree` node excepted); a phase's nodes copied into `gauntlet-run.yaml` or `gauntlet-tree.yaml`; a phase description that does not name `gauntlet-run` for a whole run |
| Phase order | the `depends_on` chain in `gauntlet-run.yaml`: `guard`, `dirty` and `stop`, `intake`, `plan-review`, `spec-review`, `pin`, `tree`, `cut`, then `land` on `ready` and `land-2` and `land-3` each only after the round before hands off `moved`, `fail` and `kill` on `defective`, nothing on `left`; in `gauntlet-tree.yaml`: `guard`, `branch-check`, `settings`, `copy-in` and `baseline`, `paths`, `write`, `mend` on `written`, `handoff` | a phase depending on any node but the one before it; any node or phase sending the run back to an earlier phase |
| The run's inputs | `gauntlet-run.yaml`'s `file` input and the run's message | an input declared for the run anywhere else; a phase reading the run's input except through `with:` |
| Run-owned settings (`worktree`, `container`, `budget`, `evidence_policy`) | `gauntlet-run.yaml`; `gauntlet-tree.yaml` for the tree run | any of them in a phase file |
| The working-folder check | `requireIgnored` in `.shared/working-folder.ts`, called by node `guard` of `gauntlet-run` in the checkout, once per run, ahead of every phase; by the `guard` node of each standalone phase (`intake/`, `plan-review/`, `spec-review/`); by node `guard` of `gauntlet-tree` in the tree and of `gauntlet-remend` in the second tree | a guard node or `guard.ts` in `write/`, `mend/` or `land/`; a second statement of the check |
| The run-start checks (test settings, uncommitted `.archon/config.yaml`, the checkout's dirty paths) | `gauntlet-run/scripts/guard.ts` and node `dirty` | the shared working-folder check; any phase's guard |
| The hand-off between phases | each phase's `returns: handoff` node, whose `output_format` declares every field, read by the next node's `with:` or script as `$<phase>.output.<field>`; writing's read by the tree run's `mend` and `handoff`, the mend's by its `handoff` | a phase reading another phase's inner node, a file or a path the previous phase did not hand off |
| Inputs inside a phase block | `$INPUTS.<name>` in prompts, in `bash:`, and in `with:` on `include:` and `workflow:` nodes; `INPUTS_<NAME>` in scripts; a node output in `when:` | `$INPUTS` in a `when:`; `$INPUTS.<name>` in an inline `script:`; a block input bound in the `with:` of a script node |
| Where the owner answers | `gauntlet-run`'s id for the run-start `dirty` ask, intake, plan review, spec review and landing's `gate`; the tree run's id for writing and the mend's `ask`, the re-mend run's id for the mend's `ask` in a second tree | any pause of writing or the mend placed in `gauntlet-run`; any pause of landing placed in the tree run or the re-mend run |
| Agents and writes in the tree after the cut | blocks of `gauntlet-tree`, the tree run: `write` and `mend`; block `mend` of `gauntlet-remend`, the re-mend run, in a second tree | an agent node in `land/` or in any other `gauntlet-run` block after `cut`; a rebase, test run or commit in a tree from `gauntlet-run`; a node field, sub-run or fence root set to reach an existing tree from another run |
| A wrong plan or spec found in writing | an approved revision, tried and approved inside writing's one loop | intake, plan review or spec review run again; `<slug>.txt` edited, moved or copied whole |
| Writing to the tree's `approved/` folders | `copy-in` of the tree run for `<slug>.txt` and `<slug>-summary.md`, and `copy-in` of the re-mend run for the whole of the previous tree's `gauntlet/`; writing's `enter`, by `cp -n`, for `<slug>.rev<N>.txt` | any agent or other node writing there; any other file name there; a revision in the checkout but landing's record copy |
| Reading the approved plan or spec in writing | `<slug>.txt` and each `<slug>.rev<N>.txt` in order of N | an agent handed `<slug>.txt` alone once a revision exists |
| Ending the run on a defective plan | the juror's verdict `defective`, handed off as writing's `outcome`; `fail` records it; `kill` cancels the run | a node failing the run for it; a line-count or size threshold; Gauntlet removing the tree or its branch |
| The failed task record | `gauntlet/failed/<slug>.txt` of the checkout: the juror's defective ruling verbatim, written once by `fail`, read by Clerk; hidden from every other checkout role by `FENCE_HIDE=gauntlet/failed`, or by a `FENCE_READ` that lists no folder holding it | any other writer or content; any other phase or role reading it, the defense included; intake's file route reading it; a fence outside `intake/` with `FENCE_READ` covering `gauntlet/failed/` and no `FENCE_HIDE` for it |
| Whether a test run is red | `.shared/red.py`, called by writing's `stage.py red` and the mend's `mend/scripts/verify.py` | any other comparison of test listings; a listing parsed in `write/`, `mend/` or `land/` |
| The final commit | writing's `seal`: `<slug>: final`, made only when the tree holds uncommitted changes | a final commit on a clean tree; any other message on the final commit; a message rewritten in landing |
| The summaries shown at the gate | writing's `state` (the approved rounds) and its hand-off `summary`: the plan summary, then each approved revision summary in order of N | a round the owner sent back listed; any other node composing them |
| Commits on the tree's branch past the writers' commits and `seal` | the mend's group `repair`: `mend-code` or `mend-tests`, as the verdict of `juror` (role `mend-juror`) names, through the commit tool, each mend read by `review` (role `mend-review`) | any other commit past `seal`; a reset, amend, squash or dropped commit on the branch, the rebase excepted |
| Landing on the checkout | landing's `git merge --ff-only` of the landed tree's branch, in the round the owner answers land, with the checkout unmoved | any other Gauntlet write to the checkout's tracked files, branch or `HEAD`; a squash or merge commit; a push or PR |
| The tree's records in the checkout | landing's record copy of the landed tree into the checkout's `gauntlet/`, after the merge | any other writer; a copy before the merge or on leave |
| Removing the trees and their branches | landing's last node, `archon complete <branch> --force` for every tree landing made, after the record copy | Gauntlet removing them on `fail`, `kill`, leave or any stop |
| Refusing a read inside a readable folder | `FENCE_HIDE` in `fence/files.py` | any other read check; `FENCE_DENY` widened to reads |
| Rounds, verdict parsing and the owner's cases in writing | `.shared/rounds.py`, with writing's verdicts in a `write/scripts/ledger.py` `Profile` (spec review design) | any of it computed in a `write/` node, prompt or command |
| Steering screening in writing | the `screen` workflow (spec review design), included by writing | any other steering check before a reviewer reads a round file |
| What each writer can see | `fence/files.py` (plan review design), through writing's `*.mcp.json` and the mend's `mend/mend-code.mcp.json` and `mend/mend-tests.mcp.json` | any other confinement of the test writers to `tests/` or of the code writers away from `tests/` |
| Writing's roles | `write/commands/<role>.md` | a `write/` node using or restating a role file of `plan-review/` or `spec-review/`; a `write/` node resuming a session of another block |

## Order

1. The run's head: `gauntlet-run/gauntlet-run.yaml` (name, inputs, worktree, nodes `guard`, `dirty`, `stop`, `intake`, `plan-review`, `spec-review`), `gauntlet-run/scripts/guard.ts`, `gauntlet-run/fixtures/dirty.stubs.yaml` (`dirty` asks, `go-on`, `intake` reached) and `gauntlet-run/fixtures/dirty-leave.stubs.yaml` (`leave`, `stop` cancels, `intake` not reached). Needs the intake design's `.shared/working-folder.ts` and the three phase blocks. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
2. Failed slugs in intake: `intake/scripts/ground.ts` (the `gauntlet/failed/` listing). Needs the intake design's `ground`. Agent: `builder`.
3. Failed slugs in Clerk: `intake/commands/clerk.md` (the added rule). Needs the intake design's `clerk.md`. Agent: `role-author`.
4. Writing in the tree run: `gauntlet-tree/gauntlet-tree.yaml` (nodes `paths`, `write`, `handoff`, the description; `paths` prints `checkout` and `brief` and `write` binds `brief`), `gauntlet-tree/fixtures/tree.stubs.yaml`, `gauntlet-tree/fixtures/defective.stubs.yaml` (writing hands off `defective`, `handoff` reached). Needs the worktree cut design's tree run and the writing design's `write/write.yaml`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
5. The run's end: `gauntlet-run/gauntlet-run.yaml` (`cut`'s `outcome` and `verdict`, nodes `fail` and `kill`, the description), `gauntlet-run/fixtures/cut.stubs.yaml`, `gauntlet-run/fixtures/defective.stubs.yaml` (`fail` and `kill` run, the run cancelled). Needs steps 1 and 4 and the worktree cut design's step 3. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
6. Hidden paths in the fence: `fence/files.py` (`FENCE_HIDE`), `fence/test_files_hide.py`. Needs the plan review design's step 1. Agent: `builder`.
7. Failed slugs hidden outside intake: `plan-review/defense.mcp.json`, `plan-review/prosecutor.mcp.json`, `plan-review/reporter.mcp.json` (`FENCE_HIDE=gauntlet/failed`). Needs step 6 and those files as their phase designs give them. Agent: `workflow-builder`.
8. Red rule: `.shared/red.py`, `.shared/tests/test_red.py`. Writing's `write/scripts/stage.py` and the mend's `mend/scripts/verify.py` need it. Agent: `builder`.
9. The mend in the tree run: `gauntlet-tree/gauntlet-tree.yaml` (node `mend`, `handoff` prints the mend's `outcome` and `line`, the description), `gauntlet-tree/fixtures/tree.stubs.yaml` (the mend hands off `ready`), `gauntlet-tree/fixtures/left.stubs.yaml` (the mend hands off `left`), `gauntlet-tree/fixtures/defective.stubs.yaml` (`mend` not reached). Needs step 4 and the landing design's `mend/mend.yaml`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
10. Landing in the run: `gauntlet-run/gauntlet-run.yaml` (`cut`'s `line` and `summary`, nodes `land`, `land-2` and `land-3`, the description), `gauntlet-run/fixtures/landed.stubs.yaml` (landing hands off `landed`), `gauntlet-run/fixtures/left.stubs.yaml` (landing hands off `left`), `gauntlet-run/fixtures/mend-left.stubs.yaml` (the tree run hands off `left`, `land` not reached), `gauntlet-run/fixtures/moved.stubs.yaml` (`land` hands off `moved`, `land-2` hands off `landed`, `land-3` not reached), `gauntlet-run/fixtures/moved-twice.stubs.yaml` (`land` and `land-2` hand off `moved`, `land-3` hands off `landed`). Needs steps 5 and 9 and the landing design's `land/land.yaml` and `gauntlet-remend/gauntlet-remend.yaml` (its step 6). `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
