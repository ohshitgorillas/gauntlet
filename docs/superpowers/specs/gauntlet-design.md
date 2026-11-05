Status: proposed.

# Gauntlet

## Why

Gauntlet is one run, `gauntlet-run`, started by one command: `archon workflow run gauntlet-run`, with the owner's message and an optional `--input file=<path>`, or the same text typed in the Archon web UI. Every phase runs inside that run, in order, and each phase hands its result to the next. The owner answers every pause on that one run. This file covers how the phases join. Each phase's own design covers its inside, and nothing here restates it.

The phases, in run order:

1. **Intake** (`gauntlet-intake-design.md`). Turns the owner's task into `gauntlet/tasks/<slug>.md`, from a file the owner wrote or through a conversation with Clerk that ends on the owner's approval. Hands off `{ task }`.
2. **Plan review** (`plan-review-design.md`). The defense decides whether the task needs a plan and writes one. The prosecutor tries it round by round, and the owner approves the plain-English summary. Hands off `{ task, plan }`, with `plan` set to `""` when no plan is needed.
3. **Spec review** (`spec-review-design.md`). The speccer decides whether tests need speccing and writes the specs. The arbiter tries them, and the owner approves them or confirms that nothing is testable. Hands off `{ task, plan, spec, outcome }`.
4. **Worktree cut** (`worktree-cut-design.md`). Cuts one worktree from the checkout's `HEAD`, copies the approved files in and records the test baseline. Hands off `{ worktree, branch, base, task, plan, spec, baseline, uncommitted }`.

No phase after the cut is designed. The run ends at node `cut`.

The phase designs contain these copies:

- Standalone phase workflows: 3. The intake, plan review and spec review designs each write their phase as a workflow started on its own. Each description invites direct use, so Archon's router can pick a phase instead of the whole run. Only the worktree cut design's `gauntlet-run/gauntlet-run.yaml` joins phases, and it leaves the earlier phases' entry open.
- `worktree: enabled: false`: 4, in `intake/intake.yaml`, `plan-review/plan-review.yaml`, `spec-review/spec-review.yaml` and `gauntlet-run/gauntlet-run.yaml`. Under `include:`, Archon drops a composed file's `worktree:` with a load-time warning, because the run owns it.
- Working-folder guard nodes in the checkout: 3, `intake/scripts/guard.ts`, `plan-review/scripts/guard.ts` and `spec-review/scripts/guard.ts`, so the guard runs three times in one run. `gauntlet-tree/scripts/guard.ts` runs in the worktree, so it is not a copy.
- Hand-off contracts: 3 `handoff` nodes. Only intake's declares an `output_format`. Plan review's and spec review's declare none, but the cut reads `$spec-review.output.task`, `.plan` and `.spec`.
- `$INPUTS` left of a `when:` comparison: 2, on intake's `from-file` and `ground`. Archon rejects this form at load inside an `include:` block.
- Inline `script:` handoffs that print an input: 2, plan review's and spec review's `handoff`. Inside an `include:` block, `$INPUTS.<name>` in an inline script is a load error.

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

  # pin, tree, cut: as the worktree cut design gives them; pin depends on [spec-review]
```

The run's message (`$ARGUMENTS`) reaches Clerk unchanged, because an included block runs inside the run. Every pause of every phase is answered on the run's own id. A failed phase fails the run, and `archon workflow resume <run id>` picks the run up there.

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

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| How a phase enters the run | `include:` of the phase's workflow in `gauntlet-run.yaml`, with node ids `intake`, `plan-review` and `spec-review` | a phase run as a `workflow:` child (the cut's `tree` node excepted); a phase's nodes copied into `gauntlet-run.yaml`; a phase description inviting direct use |
| Phase order | the `depends_on` chain in `gauntlet-run.yaml`: `guard`, `intake`, `plan-review`, `spec-review`, `pin` | a phase depending on any node but the phase before it |
| The run's inputs | `gauntlet-run.yaml`'s `file` input and the run's message | an input declared for the run anywhere else; a phase reading the run's input except through `with:` |
| Run-owned settings (`worktree`, `container`, `budget`, `evidence_policy`) | `gauntlet-run.yaml` | any of them in a phase file |
| The working-folder check in the checkout | node `guard` of `gauntlet-run`, once per run, ahead of every phase | a guard node or `guard.ts` in `intake/`, `plan-review/` or `spec-review/` |
| The hand-off between phases | each phase's `returns: handoff` node, whose `output_format` declares every field, read by the next phase's `with:` as `$<phase>.output.<field>` | a phase reading another phase's inner node, a file or a path the previous phase did not hand off |
| Inputs inside a phase block | `$INPUTS.<name>` in prompts and `bash:`; `INPUTS_<NAME>` in scripts; a node output in `when:` | `$INPUTS` in a `when:`; `$INPUTS.<name>` in an inline `script:` |
