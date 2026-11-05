Status: proposed.

# Gauntlet worktree cut

## Why

Gauntlet is one workflow, `gauntlet-run`, started once by the owner; no phase is started on its own. The cut is its phase 4, after spec review and before test writing. It takes the task file, planning's approved plan (optional) and spec review's approved spec (optional) from the phases before it in the same run, has Archon cut one worktree from the commit the owner's checkout holds, lets the repository's own `.archon/config.yaml` set it up, records the test baseline, copies the approved files in, and hands off the worktree path, branch, base commit and artifact paths. Test writing, coding and the blind-runner fence belong to later phases. Every path is relative to the pack root unless it names the checkout (the owner's live checkout the run executes in) or the tree (the new worktree). `gauntlet/` always sits in the checkout or the tree.

The cut never starts from `main` or from the repository's default branch. It starts from the checkout's `HEAD` commit at the first cut, whatever branch that is, because the plan and spec were reviewed against that code. A repository such as hqptuner2, worked on a refactor branch off `v2`, gets a tree cut from the refactor branch.

What the tree already holds for the concerns the cut touches:

- The one Gauntlet workflow: no copy. The intake, plan review and spec review designs each write their phase as a workflow of its own, ending in its own `returns: handoff`; nothing joins them.
- Worktree cutting and setup: no copy. Every Gauntlet phase designed so far pins `worktree.enabled: false` and runs in the checkout.
- The repository's test command: one copy, `fence/checks.py`, which runs the one command in `FENCE_TEST_COMMAND` (timeout `FENCE_TEST_TIMEOUT`, default 900 s) with a process-group kill, as an MCP tool for agents. No Gauntlet file says where a repository declares its command.
- Test baseline: no copy.
- Working-folder guard: designed and unbuilt, `.shared/working-folder.ts` (intake design).
- Slug from a task path: stated as a prompt rule in the spec review design (`slug = the task's file name without .md`) and as the file route's rule in the intake design. This phase derives it in `gauntlet-run/scripts/pin.py` alone.
- Approved artifact paths: `gauntlet/plans/approved/<slug>.txt` and `<slug>-summary.md` (plan review design), `gauntlet/specs/approved/<slug>.txt` and `<slug>-summary.md` (spec review design). Git does not carry the ignored `gauntlet/` into a worktree.

Uncommitted changes in the checkout do not reach the tree. Node `pin` lists the changed tracked paths in `uncommitted`, the cut hands them off, and the run goes on.

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
- **Base**: the full commit hash node `pin` creates the branch at.
- **Tree run**: the child run of node `tree`, workflow `gauntlet-tree`, executing in the tree.

Files the phase writes:

| File | Where | Writer | Rule |
|---|---|---|---|
| `gauntlet/tasks/<slug>.md`, `gauntlet/plans/approved/<slug>.txt`, `gauntlet/plans/approved/<slug>-summary.md`, `gauntlet/specs/approved/<slug>.txt`, `gauntlet/specs/approved/<slug>-summary.md` | tree | node `copy-in` | copied once from the same path in the checkout, each only when present there |
| `gauntlet/baseline/<slug>.txt` | tree | node `baseline` | written once |

## Modules

### `gauntlet-run/scripts/pin.py`

Node `pin`: slug, branch, base, and the branch created at the checkout's `HEAD` before Archon cuts the tree. Runs in the checkout. Standard library only; calls `git` as a subprocess. Replaces nothing.

```python
# /// script
# requires-python = ">=3.12"
# ///
# Environment: WORKFLOW_ID (set by Archon), INPUTS_TASK (absolute path of gauntlet/tasks/<slug>.md in the checkout).
# slug = the task file's name without .md.
# branch = "archon/task-" + norm(WORKFLOW_ID[:8] + "-tree-" + hashlib.sha256(b"tree").hexdigest()[:8] + "-child-0"),
#   norm as measured (lowercase, each run outside [a-z0-9] -> "-", trim "-", cut to 50 characters).
# stdout:
# { "slug": str, "branch": str,
#   "base": str,              # branch absent locally: git rev-parse HEAD, and git branch <branch> <base> creates it;
#                             # branch present: left as it is, base = git merge-base HEAD <branch>. Always a full hash.
#   "uncommitted": [str] }    # tracked paths git status --porcelain reports changed in the checkout, gauntlet/ excluded
# Not inside a git work tree, or HEAD has no commit: stderr names the checkout; exit 2.
def main() -> int: ...
```

Suite: `gauntlet-run/tests/test_pin.py`, run as `docs/testing.md` states with the folder `gauntlet-run/tests`. It drives `main` against a real git repository under `tmp_path`. It pins: the branch name `archon/task-72773a16-tree-dc9c5edb-child-0` for a `WORKFLOW_ID` starting `72773a16`, the name Archon produced; a fresh branch created at `HEAD`; an existing branch left at its commit, with its merge-base as base; `gauntlet/` changes left out of `uncommitted`; exit 2 outside a git work tree.

### `gauntlet-tree/scripts/guard.ts`

The tree run's first node. Replaces nothing.

```typescript
import { requireIgnored } from "../../.shared/working-folder.ts";
requireIgnored();
```

### `gauntlet-run/gauntlet-run.yaml`

The one Gauntlet workflow the owner starts. It holds the phases in order in one run; the earlier phases enter it as their own designs give them, each ending in its `{ task, plan, spec }` hand-off. This design gives its cut nodes. Replaces nothing.

```yaml
name: gauntlet-run
description: >-
  Gauntlet: takes the owner's task through intake, planning, test speccing, the worktree cut and the phases after it,
  in one run started once. Use for any piece of work the owner wants built.
worktree:
  enabled: false                       # runs in the live checkout; only node tree's child runs in the worktree

nodes:
  # ... intake, plan review and spec review nodes; spec-review's hand-off is $spec-review.output { task, plan, spec }

  - id: pin
    depends_on: [spec-review]
    runtime: uv
    script: pin
    with: { task: $spec-review.output.task }
    output_format: <object: slug, branch, base (strings), uncommitted (array of strings), all required>

  - id: tree
    depends_on: [pin]
    workflow: gauntlet-tree
    isolation: worktree
    with: { checkout: <the checkout's absolute root>, slug: $pin.output.slug, task: $spec-review.output.task,
            plan: $spec-review.output.plan, spec: $spec-review.output.spec }

  - id: cut                            # the phase's hand-off
    depends_on: [pin, tree]
    runtime: bun
    script: <print { worktree, branch, base, task, plan, spec, baseline, uncommitted }: branch, base and uncommitted
            from $pin.output, the rest from $tree.output>

  # ... the phases after the cut read $cut.output
```

Fixtures: `gauntlet-run/fixtures/cut.stubs.yaml` (`pin`, `tree` and `cut` run, `cut` reached); `gauntlet-run/fixtures/tree-failed.stubs.yaml` (`tree` fails, `cut` not reached).

### `gauntlet-tree/gauntlet-tree.yaml`

The child run in the tree. Archon cuts the tree and runs the repository's `worktree.copyFiles` and `worktree.postCreate` before its first node. Run only by node `tree` of `gauntlet-run`. Replaces nothing.

```yaml
name: gauntlet-tree
description: >-
  Gauntlet's worktree phase, run only by gauntlet-run's tree node. Copies the approved files from the owner's
  checkout into the worktree, records the test baseline once and returns the worktree's paths. Never started by hand.
inputs:
  checkout: { description: Absolute path of the owner's checkout. }
  slug: { description: The task's slug, from node pin. }
  task: { description: Absolute path of gauntlet/tasks/<slug>.md in the checkout. }
  plan: { default: "", description: Absolute approved plan path in the checkout, or "". }
  spec: { default: "", description: Absolute approved spec path in the checkout, or "". }
returns: handoff

nodes:
  - id: guard
    runtime: bun
    script: guard

  - id: copy-in                        # the only writer of the tree's gauntlet/tasks, plans and specs
    depends_on: [guard]
    bash: <for the task, the plan and its <slug>-summary.md, the spec and its <slug>-summary.md, each present in the
          checkout: target is the same path relative to $INPUTS.checkout, under the tree; target absent: cp -n;
          target identical (cmp): nothing; target differing: exit non-zero naming both paths, nothing more copied>

  - id: baseline                       # the only writer of gauntlet/baseline/
    depends_on: [guard]
    timeout: <GAUNTLET_TEST_TIMEOUT plus 60 s, in ms; 960000 when unset>
    bash: <gauntlet/baseline/<slug>.txt present: nothing. GAUNTLET_TEST_COMMAND unset or blank: write the file with the
          one line "no test command". Else run it in the tree's root, in the foreground, as
          timeout -k 10 "${GAUNTLET_TEST_TIMEOUT:-900}" nice -n 10 bash -c "$GAUNTLET_TEST_COMMAND" < /dev/null,
          and write the file: first line "exit=<n> timed_out=<true|false>", then the command's whole stdout and stderr.
          Exit 0 whatever the command's exit: a red tree is the baseline.>

  - id: handoff
    depends_on: [copy-in, baseline]
    runtime: bun
    script: <print { worktree, branch, task, plan, spec, baseline }: worktree the tree's absolute root; branch from
            git branch --show-current; task, plan, spec and baseline as absolute tree paths, plan and spec "" when
            their input is "">
```

Fixtures: `gauntlet-tree/fixtures/tree.stubs.yaml` (`handoff` reached); `gauntlet-tree/fixtures/conflict.stubs.yaml` (`copy-in` fails, `handoff` not reached).

### The repository's `.archon/config.yaml`

Each repository Gauntlet cuts in declares, in its own `.archon/config.yaml`, committed in the checkout, everything the tree needs. Gauntlet writes and decides none of it. The repository has a reachable `origin`.

```yaml
worktree:
  baseBranch: <branch>                 # required when origin/HEAD is unknown; Archon resolves and fetches it, never cuts from it
  copyFiles: [...]                     # optional; files git does not carry, such as .env
  postCreate: [...]                    # optional; the tree's setup commands
env:
  GAUNTLET_TEST_COMMAND: "<the repository's whole test command>"
  GAUNTLET_TEST_TIMEOUT: "<seconds; 900 when unset>"
```

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| Running Gauntlet | `gauntlet-run/gauntlet-run.yaml`, started once by the owner | any phase started on its own; a phase handing off to the next outside the one run |
| Slug and branch name | `gauntlet-run/scripts/pin.py` | any node, prompt or other script composing the branch; the tree run reads it from git |
| The commit the tree starts from | node `pin`, creating the branch at the checkout's `HEAD` | `main`, `worktree.baseBranch`, `--base` or the remote default as a start point; any other `git branch` in a Gauntlet file |
| Cutting the tree | Archon, through node `tree`'s `isolation: worktree` | `git worktree add` in any Gauntlet file; `archon workflow run` from inside the run; a second isolated node |
| Setting up the tree | the repository's `worktree.copyFiles` and `worktree.postCreate` | any install, copy or setup command in a Gauntlet file |
| The repository's test command and its timeout | `GAUNTLET_TEST_COMMAND` and `GAUNTLET_TEST_TIMEOUT` in the repository's `env:` | a test command written, guessed or detected by any Gauntlet file |
| The test baseline | `gauntlet/baseline/<slug>.txt` of the tree, written once by node `baseline` | a red baseline stopping the run; a rerun rewriting it; any other baseline file |
| Approved files in the tree | node `copy-in`, by `cp -n` | any agent or other node writing the tree's `gauntlet/tasks`, `gauntlet/plans` or `gauntlet/specs`; a move or edit of a checkout file |
| Working-folder check | `.shared/working-folder.ts` (intake design), first node of `gauntlet-tree` | any other check of `gauntlet/` being ignored |
| The hand-off to the next phase | node `cut`'s output `{ worktree, branch, base, task, plan, spec, baseline, uncommitted }` | any other node or file telling the next phase where the tree is |

## Order

1. Branch pin: `gauntlet-run/scripts/pin.py`, `gauntlet-run/tests/test_pin.py`. Agent: `builder`.
2. Tree run: `gauntlet-tree/gauntlet-tree.yaml`, `gauntlet-tree/scripts/guard.ts`, `gauntlet-tree/fixtures/tree.stubs.yaml`, `gauntlet-tree/fixtures/conflict.stubs.yaml`. Needs the intake design's `.shared/working-folder.ts`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
3. Cut nodes of the Gauntlet workflow: `gauntlet-run/gauntlet-run.yaml` (nodes `pin`, `tree`, `cut`), `gauntlet-run/fixtures/cut.stubs.yaml`, `gauntlet-run/fixtures/tree-failed.stubs.yaml`. Needs steps 1 and 2. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
