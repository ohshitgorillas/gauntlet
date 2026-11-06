Status: proposed.

# Gauntlet worktree cut

## Why

Gauntlet is one run, `gauntlet-run`; the run, its head and how phases join are `gauntlet-design.md`'s. The cut is phase 4, after spec review, and the phase ends at its node `cut`. It takes `task`, `plan` and `spec` from spec review's hand-off `{ task, plan, spec, outcome }` (`plan` and `spec` `""` when absent), has Archon cut one worktree from the commit the owner's checkout holds, lets the repository's own `.archon/config.yaml` set it up, records the test baseline, copies the approved files in, and hands off the worktree path, branch and artifact paths. Every path is relative to the pack root unless it names the checkout (the owner's live checkout the run executes in) or the tree (the new worktree). `gauntlet/` always sits in the checkout or the tree.

The cut never starts from `main` or from the repository's default branch. It starts from the checkout's `HEAD` commit at the first cut, whatever branch that is, because the plan and spec were reviewed against that code. A repository such as hqptuner2, worked on a refactor branch off `v2`, gets a tree cut from the refactor branch.

What the tree already holds for the concerns the cut touches:

- The one Gauntlet workflow: no copy. `gauntlet-design.md` gives `gauntlet-run/gauntlet-run.yaml`'s head, which includes intake, plan review and spec review as blocks.
- Worktree cutting and setup: no copy. The run's one `worktree: enabled: false` sits in the head, and every phase before the cut runs in the checkout.
- The repository's test command: one copy, `fence/checks.py`, which runs the brief command recorded in `gauntlet/settings.json` of its root (timeout from the same file, default 900 s) with a process-group kill, as an MCP tool for agents. The repository declares its brief command in its `env:` below, and node `settings` writes it once per tree run.
- Test baseline: no copy.
- Working-folder guard: designed and unbuilt, `.shared/working-folder.ts` (intake design). The checkout's check is node `guard` of the head; the tree's is node `guard` of `gauntlet-tree`.
- Slug from a task path: stated as a prompt rule in the spec review design (`slug = the task's file name without .md`) and as the file route's rule in the intake design. This phase derives it in `gauntlet-run/scripts/pin.py` alone.
- Approved artifact paths: `gauntlet/plans/approved/<slug>.txt` and `<slug>-summary.md` (plan review design), `gauntlet/specs/approved/<slug>.txt` and `<slug>-summary.md` (spec review design). Git does not carry the ignored `gauntlet/` into a worktree.

- Work in the tree: one place, the tree run, and after it a re-mend run (landing design) for the mend only, each in its own tree. An agent runs in its run's checkout, and `fence/files.py` and `fence/checks.py` take their root from `CLAUDE_PROJECT_DIR`, the agent's own folder. No node field sets an agent's folder, and a `workflow:` node's `isolation:` gives only `inherit` or a fresh worktree on a new branch. A node of `gauntlet-run` therefore cannot work in an existing tree; the re-mend run works in a second tree, cut on a new branch pinned at the first tree's tip, never in the first.

Uncommitted changes in the checkout do not reach the tree. `gauntlet-run`'s `guard` lists them in `dirty` (the tracked paths git reports changed and the untracked paths that are not ignored, `gauntlet/` excluded), and its node `dirty` asks the owner, before any paid phase, to go on or leave (`gauntlet-design.md`). `pin` and `cut` carry no such list.

How the tree is cut: inside a run, only a `workflow:` node with `isolation: worktree` gets a worktree. Node `pin` creates the branch Archon will name at the checkout's `HEAD` before node `tree` runs, so Archon cuts the tree from the owner's commit. A crashed run is resumed (`archon workflow resume`); the resumed `tree` node reuses the worktree recorded on its child run.

Measured on Archon v0.13.2 (a compiled binary with no source tree; throwaway repositories):

- Branch name: `"archon/task-" + norm(identifier)`. `identifier` is `WORKFLOW_ID[:8]`, `slug(nodeId)`, `sha256(nodeId)` hex `[:8]`, `child`, child index, joined by `-` with empty parts dropped. `slug` lowercases, turns each run of characters outside `[a-z0-9]` into `-`, trims leading and trailing `-`, cuts to 16 characters and trims a trailing `-`. `norm` applies the same lowercase and dash rule, trims, and cuts to 50 characters. The hash input is the node id alone. For node `tree`, `sha256("tree")[:8]` is `dc9c5edb`, and a run whose `WORKFLOW_ID` starts `72773a16` got `archon/task-72773a16-tree-dc9c5edb-child-0`. The child index is 0 for a node that is not fanned out.
- Branch reuse: Archon fetches `origin/<baseBranch>` first. A local branch of that name absent on the remote is checked out as the tree, not overwritten; with no such branch, the tree is cut from `origin/<baseBranch>`. Archon then warns that the kept worktree has commits on no remote.
- Base branch: Archon must resolve `<baseBranch>`; with `origin/HEAD` unknown and no `worktree.baseBranch`, it fails with "Cannot detect default branch ... origin/HEAD is not known".
- Remote: a repository with no remote, or an unreachable one, cannot be cut, pinned branch or not; node `tree` fails with Archon's message, and the run is resumed once the repository has a reachable `origin`. A bare remote on a local file path counts as reachable.
- `env:`: a committed `.archon/config.yaml`'s `env:` reaches the parent run's and the child run's bash nodes.

Unmeasured: whether `env:` from an uncommitted or ignored `.archon/config.yaml` reaches the tree run.

## Terms

- **Slug**: the task file's name without `.md`.
- **Branch**: the branch Archon names for node `tree`'s child, `archon/task-<first 8 characters of $WORKFLOW_ID>-tree-dc9c5edb-child-0`, normalised as Archon's `norm`.
- **Base**: the commit node `pin` creates the branch at, the checkout's `HEAD` at the cut. No node prints it.
- **Tree run**: the child run of node `tree`, workflow `gauntlet-tree`, executing in the tree. It is the only run whose nodes and agents work in the tree. When landing finds the checkout moved, the re-mend runs `gauntlet-remend` in a second tree (landing design), which holds a copy of the first tree's `gauntlet/`.

Files the phase writes:

| File | Where | Writer | Rule |
|---|---|---|---|
| `gauntlet/tasks/<slug>.md`, `gauntlet/plans/approved/<slug>.txt`, `gauntlet/plans/approved/<slug>-summary.md`, `gauntlet/specs/approved/<slug>.txt`, `gauntlet/specs/approved/<slug>-summary.md` | tree | node `copy-in` | copied once from the same path in the checkout; each named input that is not `""` must be present there, else `copy-in` fails naming the missing file |
| `gauntlet/baseline/<slug>.brief.txt` | tree | node `baseline` | written once |
| `gauntlet/settings.json` | tree | node `settings` | written once per tree run: the repository's brief command, timeout and test base |

## Modules

### `.shared/pin.py` (the branch Archon will name, and its creation)

The one place a tree's branch name is composed and the branch created. Standard library only; calls `git` as a subprocess. Imported by `gauntlet-run/scripts/pin.py` for the first tree and by `land/scripts/pin.py` (landing design) for each second tree, as the planning ledger imports `.shared/rounds.py`. Replaces nothing.

```python
# branch_name(workflow_id: str, node_id: str) -> str
#   "archon/task-" + norm(workflow_id[:8] + "-" + slug(node_id) + "-" + hashlib.sha256(node_id.encode()).hexdigest()[:8] + "-child-0"),
#   slug and norm as measured (lowercase, each run outside [a-z0-9] -> "-", trim "-"; slug cuts to 16 characters and trims a
#   trailing "-"; norm cuts to 50 characters).
# pin(workflow_id: str, node_id: str, source: str) -> { "branch": str }
#   source "" is the checkout's HEAD, else a branch name.
#   branch absent locally: git branch <branch> <source, or HEAD for ""> creates it.
#   branch present: left as it is.
```

Suite: `.shared/tests/test_pin.py`, run as `docs/testing.md` states with the folder `.shared/tests`. It drives both functions against a real git repository under `tmp_path`. It pins: the branch `archon/task-72773a16-tree-dc9c5edb-child-0` for node id `tree` and a `WORKFLOW_ID` starting `72773a16`, the name Archon produced; `archon/task-72773a16-land-retree-797b5dc7-child-0` for node id `land__retree`; a fresh branch created at `HEAD` for source `""` and at the named branch's tip otherwise; an existing branch left at its commit.

### `gauntlet-run/scripts/pin.py`

Node `pin`: slug, the predicted branch, and the branch created at the checkout's `HEAD` before Archon cuts the tree. Runs in the checkout. Imports `.shared/pin.py` with node id `tree` and source `""`. Standard library only. Replaces nothing.

```python
# /// script
# requires-python = ">=3.12"
# ///
# Environment: WORKFLOW_ID (set by Archon), INPUTS_TASK (absolute path of gauntlet/tasks/<slug>.md in the checkout).
# slug = the task file's name without .md.
# stdout:
# { "slug": str, "branch": str }   # branch as .shared/pin.py gives it for node id "tree"
# Not inside a git work tree, or HEAD has no commit: stderr names the checkout; exit 2.
def main() -> int: ...
```

Suite: `gauntlet-run/tests/test_pin.py`, run as `docs/testing.md` states with the folder `gauntlet-run/tests`. It drives `main` against a real git repository under `tmp_path`. It pins: the slug; the branch `.shared/pin.py` gives for node `tree`; exit 2 outside a git work tree.

### `gauntlet-tree/scripts/guard.ts`

The tree run's first node. Replaces nothing.

```typescript
import { requireIgnored } from "../../.shared/working-folder.ts";
requireIgnored();
```

### `gauntlet-run/gauntlet-run.yaml`

The one Gauntlet workflow the owner starts. Its head (`name`, `inputs`, `worktree`, nodes `guard`, `intake`, `plan-review`, `spec-review`) is `gauntlet-design.md`'s. This design gives its `description` and its nodes `pin`, `tree` and `cut`. Replaces nothing.

```yaml
name: gauntlet-run
description: >-
  Gauntlet: takes the owner's task through intake, planning, test speccing and the worktree cut,
  in one run started once. Use for any piece of work the owner wants built.
# inputs, worktree: as gauntlet-design.md gives them

nodes:
  # guard, intake, plan-review, spec-review: as gauntlet-design.md gives them;
  # spec-review's hand-off is $spec-review.output { task, plan, spec, outcome }

  - id: pin
    depends_on: [spec-review]
    runtime: uv
    script: pin
    with: { task: $spec-review.output.task }
    output_format: <object: slug, branch (strings), all required>

  - id: tree
    depends_on: [pin]
    workflow: gauntlet-tree
    isolation: worktree
    with: { slug: $pin.output.slug, branch: $pin.output.branch, task: $spec-review.output.task,
            plan: $spec-review.output.plan, spec: $spec-review.output.spec }

  - id: cut                            # the phase's hand-off
    depends_on: [pin, tree]
    runtime: bun
    script: <print { worktree, branch, task, plan, spec } from $tree.output, branch included>
    output_format: <object: worktree, branch, task, plan, spec (strings), all required>

  # land, land-2, land-3, land-4, fail, kill: as gauntlet-design.md gives them
```

Fixtures: `gauntlet-run/fixtures/cut.stubs.yaml` (`pin`, `tree` and `cut` run, `cut` reached); `gauntlet-run/fixtures/tree-failed.stubs.yaml` (`tree` fails, `cut` not reached).

### `gauntlet-tree/gauntlet-tree.yaml`

The child run in the tree. Archon cuts the tree and runs the repository's `worktree.copyFiles` and `worktree.postCreate` before its first node. Run only by node `tree` of `gauntlet-run`. Every node and agent that works in the tree is a node or block of this run: writing's block `write`, then the mend's block `mend`, as `gauntlet-design.md` gives their places. This design gives its inputs and its nodes `guard`, `branch-check`, `settings`, `copy-in`, `baseline` and `handoff`. The checkout's root is `task` with its trailing `/gauntlet/tasks/<slug>.md` removed, so the run takes no `checkout` input. Replaces nothing.

```yaml
name: gauntlet-tree
description: >-
  Gauntlet's tree run, started only by gauntlet-run's tree node. Copies the approved files from the owner's
  checkout into the worktree, records the test baseline once and runs every Gauntlet step that works in the
  worktree. Never started by hand.
inputs:
  slug: { description: The task's slug, from node pin. }
  branch: { description: The branch node pin created at the checkout's HEAD. }
  task: { description: Absolute path of gauntlet/tasks/<slug>.md in the checkout. }
  plan: { default: "", description: Absolute approved plan path in the checkout, or "". }
  spec: { default: "", description: Absolute approved spec path in the checkout, or "". }
returns: handoff

nodes:
  - id: guard
    runtime: bun
    script: guard

  - id: branch-check                   # the run's first node after guard: the tree is on the branch pin named
    depends_on: [guard]
    bash: <git branch --show-current differs from $INPUTS.branch: exit non-zero naming both, before anything is copied>

  - id: settings                       # the only writer of gauntlet/settings.json
    depends_on: [guard, branch-check]
    bash: <write gauntlet/settings.json in the tree's root, once per tree run, from the repository's env: {"brief":
          GAUNTLET_TEST_BRIEF_COMMAND, "timeout": GAUNTLET_TEST_TIMEOUT (900 when unset), "base": GAUNTLET_TEST_BASE
          split on ":" (an empty list when unset)}. The fences read this file, never
          the environment>

  - id: copy-in                        # the only writer of the tree's gauntlet/tasks, plans and specs
    depends_on: [guard, branch-check]
    bash: <the checkout's root is $INPUTS.task with its trailing /gauntlet/tasks/$INPUTS.slug.md removed. For the task,
          the plan and its <slug>-summary.md, the spec and its <slug>-summary.md, each named by a non-empty input: absent
          from the checkout: exit non-zero naming the missing file; target is the same path under the tree; target absent:
          cp -n; target identical (cmp): nothing; target differing: exit non-zero naming both paths, nothing more copied>

  - id: baseline                       # the only writer of gauntlet/baseline/; no node timeout, the inner timeout -k bounds it
    depends_on: [guard, branch-check]
    bash: <gauntlet/baseline/<slug>.brief.txt present: nothing. Else run GAUNTLET_TEST_BRIEF_COMMAND in the tree's root, in
          the foreground, as timeout -k 10 "${GAUNTLET_TEST_TIMEOUT:-900}" nice -n 10 bash -c "$GAUNTLET_TEST_BRIEF_COMMAND"
          < /dev/null, and write the file: first line "exit=<n> timed_out=<true|false>", then the command's whole stdout
          and stderr. Exit 0 whatever the command's exit: a red tree is the baseline. The run-start guard has refused a
          blank command, so none is recorded as "no test command">

  - id: handoff
    depends_on: [copy-in, baseline, settings]
    runtime: bun
    script: <print { worktree, branch, task, plan, spec }: worktree the tree's absolute root; branch from
            git branch --show-current; task, plan and spec as absolute tree paths, plan and spec "" when
            their input is ""; inputs read as INPUTS_<NAME> from the environment, never $INPUTS.<name>>
    output_format: <object: worktree, branch, task, plan, spec (strings), all required>
```

Fixtures: `gauntlet-tree/fixtures/tree.stubs.yaml` (`handoff` reached); `gauntlet-tree/fixtures/conflict.stubs.yaml` (`copy-in` fails, `handoff` not reached); `gauntlet-tree/fixtures/branch.stubs.yaml` (`branch-check` fails, `copy-in` not reached).

### The repository's `.archon/config.yaml`

Each repository Gauntlet cuts in declares, in its own `.archon/config.yaml`, committed in the checkout, everything the tree needs. Gauntlet writes and decides none of it. The repository has a reachable `origin`.

```yaml
worktree:
  baseBranch: <branch>                 # required when origin/HEAD is unknown; Archon resolves and fetches it, never cuts from it
  copyFiles: [...]                     # optional; files git does not carry, such as .env
  postCreate: [...]                    # optional; the tree's setup commands
env:
  GAUNTLET_TEST_BRIEF_COMMAND: "<the whole test command, one line per test (writing design); required>"
  GAUNTLET_TEST_TIMEOUT: "<seconds, a positive integer; optional, 900 when unset>"
  GAUNTLET_TEST_BASE: "<colon-separated root paths the test writer may use (writing design); optional, none when unset>"
```

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| Slug | `gauntlet-run/scripts/pin.py` | any node, prompt or other script deriving it |
| The predicted branch name and its creation | `.shared/pin.py`, called by `gauntlet-run/scripts/pin.py` for node `tree` and by `land/scripts/pin.py` for each re-mend run's node `<round>__retree` | any node, prompt or other script composing a branch name |
| The branch the cut hands off | node `branch-check` of `gauntlet-tree`, comparing pin's name with `git branch --show-current` and failing the run naming both; node `cut` reading `branch` from `$tree.output` | the cut taking `branch` from `$pin.output`; a mismatch found after the tree run |
| The commit the tree starts from | node `pin`, creating the branch at the checkout's `HEAD`; for a second tree, node `repin` of block `land`, creating the branch at the first tree's tip (landing design) | `main`, `worktree.baseBranch`, `--base` or the remote default as a start point; any other `git branch` in a Gauntlet file |
| Cutting the tree | Archon, through node `tree`'s `isolation: worktree`; for a second tree, through node `retree` of block `land`, at most twice (landing design) | `git worktree add` in any Gauntlet file; `archon workflow run` from inside the run; any other isolated node |
| Work in the tree | the tree run, `gauntlet-tree`: blocks `write`, then `mend`; after it, `gauntlet-remend`, block `mend` only, in a second tree (landing design) | a rebase, test run or commit in a tree from `gauntlet-run`; a node field, sub-run or fence root set to reach an existing tree from another run (`gauntlet-design.md`) |
| Setting up the tree | the repository's `worktree.copyFiles` and `worktree.postCreate` | any install, copy or setup command in a Gauntlet file |
| The repository's test command and timeout | the repository's `env:`: `GAUNTLET_TEST_BRIEF_COMMAND`, required, refused at run start when unset or blank; `GAUNTLET_TEST_TIMEOUT`, optional (900 when unset), refused at run start when set but not a positive integer; `GAUNTLET_TEST_BASE`, optional (none when unset) (`gauntlet-design.md`) | a test command written, guessed or detected by any Gauntlet file; a node `timeout:` on a test node |
| What the fences read of those settings | `gauntlet/settings.json` of the tree, written once by node `settings` | a fence server reading the environment for them; a `sh -c` launch line building a `FENCE_*` value |
| The test baseline | `gauntlet/baseline/<slug>.brief.txt` of the tree, written once by node `baseline` | a red baseline stopping the run; a rerun rewriting it; any other baseline file |
| Approved files in the tree | node `copy-in`, by `cp -n`, failing on a named input that is absent from the checkout | any agent or other node writing the tree's `gauntlet/tasks`, `gauntlet/plans` or `gauntlet/specs`; a move or edit of a checkout file; a missing input skipped |
| Working-folder check in the tree | node `guard` of `gauntlet-tree`, through `.shared/working-folder.ts` (intake design) | any other check of `gauntlet/` being ignored in the tree |
| The tree run's hand-off | node `handoff` of `gauntlet-tree`, whose `output_format` declares every field, read by node `cut` as `$tree.output.<field>` | node `cut` reading any other node of the tree run, or a file |
| The cut's hand-off | node `cut`, whose `output_format` declares `{ worktree, branch, task, plan, spec }` and the `outcome`, `verdict`, `line` and `summary` `gauntlet-design.md` adds | any other node or file telling where the tree is |

## Order

1. Branch pin: `.shared/pin.py`, `.shared/tests/test_pin.py`, `gauntlet-run/scripts/pin.py`, `gauntlet-run/tests/test_pin.py`. Agent: `builder`.
2. Tree run: `gauntlet-tree/gauntlet-tree.yaml`, `gauntlet-tree/scripts/guard.ts`, `gauntlet-tree/fixtures/tree.stubs.yaml`, `gauntlet-tree/fixtures/conflict.stubs.yaml`, `gauntlet-tree/fixtures/branch.stubs.yaml`. Needs the intake design's `.shared/working-folder.ts`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
3. Cut nodes of the Gauntlet workflow: `gauntlet-run/gauntlet-run.yaml` (nodes `pin`, `tree`, `cut`), `gauntlet-run/fixtures/cut.stubs.yaml`, `gauntlet-run/fixtures/tree-failed.stubs.yaml`. Needs steps 1 and 2 and the run's head from `gauntlet-design.md`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
