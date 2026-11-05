Status: proposed.

# Gauntlet

## Why

Gauntlet is one run, `gauntlet-run`, started by one command: `archon workflow run gauntlet-run`, with the owner's message and an optional `--input file=<path>`, or the same text typed in the Archon web UI. Every phase runs inside that run, in order, and each phase hands its result to the next. The owner answers the pauses of intake, plan review, spec review and landing on that run's id, and the pauses of writing on the id of the tree run, the child run the cut starts in the tree; `archon workflow get <run id> --json` gives it at `.metadata.approval.childRunId`. No phase goes back to an earlier phase. This file covers how the phases join. Each phase's own design covers its inside, and nothing here restates it.

The phases, in run order:

1. **Intake** (`gauntlet-intake-design.md`). Turns the owner's task into `gauntlet/tasks/<slug>.md`, from a file the owner wrote or through a conversation with Clerk that ends on the owner's approval. Hands off `{ task }`.
2. **Plan review** (`plan-review-design.md`). The defense decides whether the task needs a plan and writes one. The prosecutor tries it round by round, and the owner approves the plain-English summary. Hands off `{ task, plan }`, with `plan` set to `""` when no plan is needed.
3. **Spec review** (`spec-review-design.md`). The speccer decides whether tests need speccing and writes the specs. The arbiter tries them, and the owner approves them or confirms that nothing is testable. Hands off `{ task, plan, spec, outcome }`.
4. **Worktree cut** (`worktree-cut-design.md`). Cuts one worktree from the checkout's `HEAD`, copies the approved files in and records the test baseline. Hands off `{ worktree, branch, base, task, plan, spec, baseline, brief, uncommitted, outcome, verdict }`, the last two from writing.
5. **Writing** (the writing design). Runs in the tree, as block `write` of the tree run, after the baseline. Test writers write the tests from the approved specs, then code writers write the code. A juror rules whether the tests, the code, the spec or the plan is wrong, or that the plan is defective. A wrong plan or spec is revised inside writing, as an approved revision; a defective plan ends the run. Hands off `{ outcome, verdict }` to the tree run's `handoff`.
6. **Landing** (`landing-design.md`). Runs in the checkout as block `land` of `gauntlet-run`, after `cut`, when writing hands off `written`, and reaches the tree with `git -C <worktree>`. It rebases the tree's branch onto the checkout's `HEAD`, reruns the brief test command when the checkout has moved past base, and waits for the owner to land or leave. On land it fast-forwards the checkout, copies the tree's records into the checkout's `gauntlet/` and removes the tree and its branch. It runs git, the brief test command and Archon's CLI only, with no agent. Hands off `{ outcome }`, `landed` or `left`.

The run ends at block `land` when writing hands off `written`, and at node `kill`, cancelled, when it hands off `defective`.

The phase designs contain these copies:

- Standalone phase workflows: 3. The intake, plan review and spec review designs each write their phase as a workflow started on its own. Each description invites direct use, so Archon's router can pick a phase instead of the whole run. Only the worktree cut design's `gauntlet-run/gauntlet-run.yaml` joins phases, and it leaves the earlier phases' entry open.
- `worktree: enabled: false`: 4, in `intake/intake.yaml`, `plan-review/plan-review.yaml`, `spec-review/spec-review.yaml` and `gauntlet-run/gauntlet-run.yaml`. Under `include:`, Archon drops a composed file's `worktree:` with a load-time warning, because the run owns it.
- Working-folder guard nodes in the checkout: 3, `intake/scripts/guard.ts`, `plan-review/scripts/guard.ts` and `spec-review/scripts/guard.ts`, so the guard runs three times in one run. `gauntlet-tree/scripts/guard.ts` runs in the worktree, so it is not a copy.
- Hand-off contracts: 3 `handoff` nodes. Only intake's declares an `output_format`. Plan review's and spec review's declare none, but the cut reads `$spec-review.output.task`, `.plan` and `.spec`.
- `$INPUTS` left of a `when:` comparison: 2, on intake's `from-file` and `ground`. Archon rejects this form at load inside an `include:` block.
- Inline `script:` handoffs that print an input: 2, plan review's and spec review's `handoff`. Inside an `include:` block, `$INPUTS.<name>` in an inline script is a load error.
- Writers of the tree's `gauntlet/plans/approved/` and `gauntlet/specs/approved/`: the worktree cut design names `copy-in` the only one. Writing's revisions need a second.
- Places a node runs in the tree: 1, the tree run. An `include:` block has no checkout of its own, and a second `workflow:` node with `isolation: worktree` gets a second branch, cut from the repository's base branch. Writing is therefore a block of `gauntlet-tree`, not of `gauntlet-run`.
- Fences that can read the checkout's `gauntlet/failed/` outside intake: 4, with `FENCE_READ=.`: `plan-review/defense.mcp.json`, `plan-review/prosecutor.mcp.json`, `plan-review/reporter.mcp.json` and `spec-review/speccer.mcp.json`. `fence/files.py` applies `FENCE_DENY` to writes only, so no fence can refuse a read inside a readable folder.
- Role files writing would reuse: 4, `plan-review/commands/defense.md`, `plan-review/commands/prosecutor.md`, `spec-review/commands/speccer.md` and `spec-review/commands/arbiter.md`. Commands resolve only from a workflow's own `commands/`, so writing cannot call them.
- Comparisons of a test run against the brief baseline: 1, `red` of `write/scripts/stage.py` (writing design). Landing's verify needs a second, and named scripts resolve only from a workflow's own `scripts/`, so `land/` cannot call `stage.py`.
- Copies of the tree's records in the checkout: none designed. Landing's record copy is the first writer of revisions and writing's round records there.

The tree holds none of these yet. The only parts built are `fence/` and `spec-review/commands/arbiter.md`.

## Modules

### `gauntlet-run/gauntlet-run.yaml` (the run's head)

The one workflow the owner starts. It declares the run's input, checks the working folder once and includes the three earlier phases in order. The worktree cut design gives the nodes `pin`, `tree` and `cut` that follow, and the description. This module fills the phases' entry, which the worktree cut design leaves open.

```yaml
name: gauntlet-run
inputs:
  file:
    default: ""
    description: Path of a task file the owner wrote. Blank sends the run's message to Clerk.
worktree:
  enabled: false                       # the run's one worktree setting; no phase file declares worktree:

nodes:
  - id: guard                          # once per run, in the checkout, before any phase
    runtime: bun
    script: guard
    output_format: { type: object, properties: { file: { type: string } }, required: [file] }

  - id: intake
    depends_on: [guard]
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
  # cut also prints brief, outcome and verdict from $tree.output; its output_format adds
  # brief (string), outcome (enum: written, defective) and verdict (string), all required.

  - id: land                           # phase 6, in the checkout
    depends_on: [cut]
    when: "$cut.output.outcome == 'written'"
    include: land
    with: { slug: $pin.output.slug, worktree: $cut.output.worktree, branch: $cut.output.branch,
            base: $cut.output.base, brief: $cut.output.brief }

  - id: fail                           # the only writer of the checkout's gauntlet/failed/
    depends_on: [cut]
    when: "$cut.output.outcome == 'defective'"
    bash: <cp -n $cut.output.verdict to gauntlet/failed/$pin.output.slug.txt of the checkout;
          target present: exit non-zero naming it, nothing copied>

  - id: kill                           # the run's end on a defective plan
    depends_on: [fail]
    cancel: "The juror ruled the plan defective. The grounds are in the checkout's gauntlet/failed/, under the task's slug. Start a new gauntlet-run that names the slug."
```

The description is the worktree cut design's, with writing and landing named among the phases it takes the task through.

The run's message (`$ARGUMENTS`) reaches Clerk unchanged, because an included block runs inside the run. The pauses of intake, plan review, spec review and landing are answered on the run's own id, and writing's on the tree run's id. A failed phase fails the run, and `archon workflow resume <run id>` picks the run up there. A defective plan cancels the run at `kill`; the tree and its branch stay where they are, for the owner to inspect or remove with `archon isolation cleanup`. An owner's leave at landing ends the run with the tree and its branch kept the same way.

### `gauntlet-run/scripts/guard.ts`

The run's working-folder check, which runs in the checkout before any phase. It also passes the run's `file` input on as an output, so the intake block receives it as a node reference. Replaces `intake/scripts/guard.ts`, `plan-review/scripts/guard.ts` and `spec-review/scripts/guard.ts`, none of which is written.

```typescript
import { requireIgnored } from "../../.shared/working-folder.ts";
requireIgnored();
// stdout: { "file": process.env.INPUTS_FILE ?? "" }
```

### Phase files as blocks: `intake/intake.yaml`, `plan-review/plan-review.yaml`, `spec-review/spec-review.yaml`

Each phase file is the workflow its own design gives, with these changes so that `gauntlet-run` can include it:

- `description:` begins `Gauntlet <phase>, included by gauntlet-run only. Not for direct use.` and invites no direct use.
- No `worktree:` key.
- No `guard` node. A node that depended only on `guard` has no `depends_on` and becomes an entry node of the block: intake's `route`, and plan review's and spec review's `docket-in`, plus spec review's `policy`.
- `inputs:` and `returns: handoff` stay as the block's signature. The `handoff` node declares an `output_format` that names every field it prints:
  - intake: `{ task }`
  - plan review: `{ task, plan }`
  - spec review: `{ task, plan, spec, outcome }`
- `$INPUTS.<name>` appears only in prompts and `bash:` bodies. A `script:` reads `INPUTS_<NAME>` from the environment. No `when:` reads `$INPUTS`.

Writing's block, `write/write.yaml`, follows the same rules, with `gauntlet-tree` as the file that includes it. Landing's block, `land/land.yaml`, follows them with `gauntlet-run` as the file that includes it.

Intake's routing reads a node output:

```yaml
  - id: route                          # intake's entry node
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

The tree run, as the worktree cut design gives it, with writing included after the baseline. Its `handoff` node becomes `paths`, which also prints the slug, and the brief baseline's path as the writing design gives it; a new `handoff` adds writing's result. The description names writing.

```yaml
nodes:
  # guard, copy-in, baseline: as the worktree cut design gives them

  - id: paths                          # the cut design's handoff script, plus slug
    depends_on: [copy-in, baseline]
    runtime: bun
    script: <print { slug, worktree, branch, task, plan, spec, baseline } as the cut design's handoff does; slug from INPUTS_SLUG>
    output_format: <object: slug, worktree, branch, task, plan, spec, baseline (strings), all required>

  - id: write                          # phase 5
    depends_on: [paths]
    include: write
    with: { slug: $paths.output.slug, task: $paths.output.task, plan: $paths.output.plan,
            spec: $paths.output.spec, baseline: $paths.output.baseline }

  - id: handoff                        # the tree run's returns:
    depends_on: [paths, write]
    runtime: bun
    script: <print { worktree, branch, task, plan, spec, baseline, brief } from $paths.output and { outcome, verdict } from $write.output>
    output_format: <object: worktree, branch, task, plan, spec, baseline, brief, outcome, verdict (strings), all required;
                   outcome enum: written, defective>
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
  baseline: { description: Absolute tree path of gauntlet/baseline/<slug>.txt. }
returns: handoff

nodes:
  # every node but enter and handoff: the writing design's

  - id: enter                          # the only writer of approved revisions
    bash: <cp -n the revision the owner approved at bench to gauntlet/<plans|specs>/approved/<slug>.rev<N>.txt,
          N one above the highest present for that file, 1 when none; target present: exit non-zero naming it>

  - id: handoff
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [written, defective] }
        verdict: { type: string }      # absolute tree path of the juror's defective ruling; "" when written
      required: [outcome, verdict]
```

### Approved revisions

`gauntlet/plans/approved/<slug>.rev<N>.txt` and `gauntlet/specs/approved/<slug>.rev<N>.txt`, in the tree only. Each holds only its revision: the clauses it changes, each as it now reads. The approved plan or spec is `<slug>.txt` with every revision applied in order of N. Every agent in writing that needs an approved plan or spec is handed `<slug>.txt` and each of its revisions in order of N. A juror ruling that a change is too large for a revision is the verdict `defective`.

### `write/write.yaml` (the final commit's message)

Node `seal` is the writing design's, with one change: it commits with `git commit -F -`, the message on stdin. Line 1 is `<slug>: final`, then a blank line, then `gauntlet/plans/approved/<slug>-summary.md` when `plan` is not `""`, then each `gauntlet/revisions/<slug>-summary.<N>.md` in order of N, each separated by a blank line. The writers' own commits keep their messages. Landing shows these messages at the owner's gate and never rewrites them.

### `land/land.yaml` (landing's signature)

The landing block's signature and its hand-off. Every other node is the landing design's. It runs in the checkout and reaches the tree only with `git -C $INPUTS.worktree`. It holds one wait, the owner's land or leave, answered on `gauntlet-run`'s id, and no agent node. Its only writes in the checkout are the fast-forward merge and the record copy.

```yaml
name: land
description: >-
  Gauntlet landing, included by gauntlet-run only. Not for direct use.
inputs:
  slug: { description: The task's slug. }
  worktree: { description: Absolute path of the tree. }
  branch: { description: The tree's branch. }
  base: { description: Full hash of the commit the tree was cut from. }
  brief: { description: Absolute tree path of gauntlet/baseline/<slug>.brief.txt. }
returns: handoff

nodes:
  # every node but handoff: the landing design's

  - id: handoff
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [landed, left] }
      required: [outcome]
```

The checkout's tracked files change only by `git merge --ff-only <branch>`, after the owner chooses land. No squash and no merge commit: the writers' commits and `<slug>: final` reach the checkout as they stand after the rebase.

After the merge, landing copies from the tree into the checkout's `gauntlet/`, by `cp -n`: `plans/approved/<slug>.rev<N>.txt`, `specs/approved/<slug>.rev<N>.txt`, and every `<slug>.*` and `<slug>-summary.*` file of `write/` and `revisions/`. Then it removes the tree and its branch with `archon complete <branch>`. Unmeasured: whether `archon complete` accepts the branch while `gauntlet-run` is still running; if it refuses, the builder stops and reports the gap. On leave, and on any stop, the tree and its branch stay.

### `.shared/red.py` (red against the brief baseline)

The one rule for whether a test run is red. Standard library only. `write/scripts/stage.py`'s `red` and landing's verify script import it as the planning ledger imports `.shared/rounds.py`, and compute no comparison themselves. Replaces the comparison inside `stage.py`'s `red`.

```python
def listing(text: str) -> dict[str, str]: ...
# One line per test, "PASSED <id>", "FAILED <id>" or "ERROR <id>", text from " - " on dropped; other lines ignored.
# Returns id -> "PASSED" | "FAILED" | "ERROR".

def red(run: str, brief: str, head: str = "") -> bool: ...
# run, brief, head: test-run texts, first line as their writers give it, then the brief command's output.
# True when run timed out; or a test FAILED or ERROR in run is failing in neither brief nor head;
#   or run exits non-zero with no failing line while brief exited 0 and head, when given, exited 0.
# A failure in brief or head that passes in run is not red. head "": no head check.
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

`plan-review/defense.mcp.json`, `plan-review/prosecutor.mcp.json`, `plan-review/reporter.mcp.json` and `spec-review/speccer.mcp.json` each set `FENCE_HIDE=gauntlet/failed`, with every other `FENCE_*` value as their phase designs give it.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| How a phase enters the run | `include:` of the phase's workflow: in `gauntlet-run.yaml`, node ids `intake`, `plan-review`, `spec-review` and `land`; in `gauntlet-tree.yaml`, node id `write` | a phase run as a `workflow:` child (the cut's `tree` node excepted); a phase's nodes copied into `gauntlet-run.yaml` or `gauntlet-tree.yaml`; a phase description inviting direct use |
| Phase order | the `depends_on` chain in `gauntlet-run.yaml`: `guard`, `intake`, `plan-review`, `spec-review`, `pin`, `tree`, `cut`, then `land` on `written` or `fail` and `kill` on `defective`; in `gauntlet-tree.yaml`: `guard`, `copy-in` and `baseline`, `paths`, `write`, `handoff` | a phase depending on any node but the one before it; any node or phase sending the run back to an earlier phase |
| The run's inputs | `gauntlet-run.yaml`'s `file` input and the run's message | an input declared for the run anywhere else; a phase reading the run's input except through `with:` |
| Run-owned settings (`worktree`, `container`, `budget`, `evidence_policy`) | `gauntlet-run.yaml`; `gauntlet-tree.yaml` for the tree run | any of them in a phase file |
| The working-folder check | node `guard` of `gauntlet-run` in the checkout, once per run, ahead of every phase; node `guard` of `gauntlet-tree` in the tree | a guard node or `guard.ts` in `intake/`, `plan-review/`, `spec-review/`, `write/` or `land/` |
| The hand-off between phases | each phase's `returns: handoff` node, whose `output_format` declares every field, read by the next node's `with:` or script as `$<phase>.output.<field>`; writing's read by the tree run's `handoff` | a phase reading another phase's inner node, a file or a path the previous phase did not hand off |
| Inputs inside a phase block | `$INPUTS.<name>` in prompts and `bash:`; `INPUTS_<NAME>` in scripts; a node output in `when:` | `$INPUTS` in a `when:`; `$INPUTS.<name>` in an inline `script:` |
| Where the owner answers | `gauntlet-run`'s id for intake, plan review, spec review and landing; the tree run's id for writing | any pause of writing placed in `gauntlet-run`; any pause of landing placed in the tree run |
| A wrong plan or spec found in writing | an approved revision, tried and approved inside writing's one loop | intake, plan review or spec review run again; `<slug>.txt` edited, moved or copied whole |
| Writing to the tree's `approved/` folders | `copy-in` of the tree run for `<slug>.txt` and `<slug>-summary.md`; writing's `enter`, by `cp -n`, for `<slug>.rev<N>.txt` | any agent or other node writing there; any other file name there; a revision in the checkout but landing's record copy |
| Reading the approved plan or spec in writing | `<slug>.txt` and each `<slug>.rev<N>.txt` in order of N | an agent handed `<slug>.txt` alone once a revision exists |
| Ending the run on a defective plan | the juror's verdict `defective`, handed off as writing's `outcome`; `fail` records it; `kill` cancels the run | a node failing the run for it; a line-count or size threshold; Gauntlet removing the tree or its branch |
| The failed task record | `gauntlet/failed/<slug>.txt` of the checkout: the juror's defective ruling verbatim, written once by `fail`, read by Clerk; hidden from every other checkout role by `FENCE_HIDE=gauntlet/failed` | any other writer or content; any other phase or role reading it, the defense included; intake's file route reading it; a fence outside `intake/` with `FENCE_READ` covering `gauntlet/failed/` and no `FENCE_HIDE` for it |
| Whether a test run is red | `.shared/red.py`, called by writing's `stage.py red` and landing's verify | any other comparison of test listings; a listing parsed in `write/` or `land/` |
| The final commit's message | writing's `seal`: `<slug>: final`, the approved plan's summary, each revision summary in order of N | any other message on the final commit; a message rewritten in landing |
| Landing on the checkout | landing's `git merge --ff-only` of the tree's branch, after the owner chooses land | any other Gauntlet write to the checkout's tracked files, branch or `HEAD`; a squash or merge commit; a push or PR |
| The tree's records in the checkout | landing's record copy into the checkout's `gauntlet/`, by `cp -n`, after the merge | any other writer; a copy before the merge or on leave |
| Removing the tree and its branch | landing, by `archon complete <branch>`, after the record copy | Gauntlet removing them on `fail`, `kill`, leave or any stop |
| Refusing a read inside a readable folder | `FENCE_HIDE` in `fence/files.py` | any other read check; `FENCE_DENY` widened to reads |
| Rounds, verdict parsing and the owner's cases in writing | `.shared/rounds.py`, with writing's verdicts in a `write/scripts/ledger.py` `Profile` (spec review design) | any of it computed in a `write/` node, prompt or command |
| Steering screening in writing | the `screen` workflow (spec review design), included by writing | any other steering check before a reviewer reads a round file |
| What each writer can see | `fence/files.py` (plan review design), through writing's `*.mcp.json` | any other confinement of the test writers to `tests/` or of the code writers away from `tests/` |
| Writing's roles | `write/commands/<role>.md` | a `write/` node using or restating a role file of `plan-review/` or `spec-review/`; a `write/` node resuming a session of another block |

## Order

1. The run's head: `gauntlet-run/gauntlet-run.yaml` (name, inputs, worktree, nodes `guard`, `intake`, `plan-review`, `spec-review`), `gauntlet-run/scripts/guard.ts`. Needs the intake design's `.shared/working-folder.ts` and the three phase blocks. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
2. Failed slugs in intake: `intake/scripts/ground.ts` (the `gauntlet/failed/` listing). Needs the intake design's `ground`. Agent: `builder`.
3. Failed slugs in Clerk: `intake/commands/clerk.md` (the added rule). Needs the intake design's `clerk.md`. Agent: `role-author`.
4. Writing in the tree run: `gauntlet-tree/gauntlet-tree.yaml` (nodes `paths`, `write`, `handoff`, the description), `gauntlet-tree/fixtures/tree.stubs.yaml`, `gauntlet-tree/fixtures/defective.stubs.yaml` (writing hands off `defective`, `handoff` reached). Needs the worktree cut design's tree run and the writing design's `write/write.yaml`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
5. The run's end: `gauntlet-run/gauntlet-run.yaml` (`cut`'s `outcome` and `verdict`, nodes `fail` and `kill`, the description), `gauntlet-run/fixtures/cut.stubs.yaml`, `gauntlet-run/fixtures/defective.stubs.yaml` (`fail` and `kill` run, the run cancelled). Needs steps 1 and 4 and the worktree cut design's step 3. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
6. Hidden paths in the fence: `fence/files.py` (`FENCE_HIDE`), `fence/test_files_hide.py`. Needs the plan review design's step 1. Agent: `builder`.
7. Failed slugs hidden outside intake: `plan-review/defense.mcp.json`, `plan-review/prosecutor.mcp.json`, `plan-review/reporter.mcp.json`, `spec-review/speccer.mcp.json` (`FENCE_HIDE=gauntlet/failed`). Needs step 6 and those files as their phase designs give them. Agent: `workflow-builder`.
8. Red rule: `.shared/red.py`, `.shared/tests/test_red.py`. Writing's `write/scripts/stage.py` and landing's verify script need it. Agent: `builder`.
9. The final commit's message: `write/write.yaml` (node `seal`), `write/fixtures/written.stubs.yaml`. Needs the writing design's step 7. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
10. The brief baseline handed off: `gauntlet-tree/gauntlet-tree.yaml` (`handoff` prints `brief`), `gauntlet-tree/fixtures/tree.stubs.yaml`. Needs step 4 and the writing design's step 8. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
11. Landing in the run: `gauntlet-run/gauntlet-run.yaml` (`cut`'s `brief`, node `land`, the description), `gauntlet-run/fixtures/landed.stubs.yaml` (landing hands off `landed`), `gauntlet-run/fixtures/left.stubs.yaml` (landing hands off `left`). Needs steps 5 and 10 and the landing design's `land/land.yaml`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
