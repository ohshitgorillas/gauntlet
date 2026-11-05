Status: proposed.

# Gauntlet landing

## Why

Landing is phase 6, block `land` of `gauntlet-run`, after `cut`, when writing hands off `written`. `gauntlet-design.md` gives its place in the run, its signature and hand-off, the fast-forward merge as the only write to the checkout's tracked files, the record copy, the tree's removal by `archon complete <branch> --force`, and `.shared/red.py`. This file gives every other node of `land/land.yaml` and nothing that design states. Every path is relative to the pack root unless it names the checkout or the tree.

By landing time the checkout may have moved past base and may hold uncommitted edits. Landing rebases the tree's branch onto the checkout's `HEAD`, verifies the rebased tree only when the checkout has moved, shows the owner the diff stat and the commit messages, waits for land or leave, and on land fast-forwards the checkout, copies the records and removes the tree. It runs git, the brief test command, one script and Archon's CLI, with no agent.

What the designs hold for the concerns landing touches:

- Running a test command from a bash node: 3 designed copies of one invocation, `timeout -k 10 "${GAUNTLET_TEST_TIMEOUT:-900}" nice -n 10 bash -c "<command>" < /dev/null` in the tree's root, writing `exit=<n> timed_out=<true|false>` then the output: node `baseline` of the tree run, for `GAUNTLET_TEST_COMMAND` (worktree cut design) and `GAUNTLET_TEST_BRIEF_COMMAND` (writing design), and node `test` of writing. Landing's two test nodes make 5. `fence/checks.py` runs a test command for agents only, as an MCP tool, so no bash node can call it. Named scripts resolve only from a workflow's own `scripts/`, and the repository's `env:` is measured to reach bash nodes only, so no shared runner can hold the invocation. Its one home is node `baseline`'s invocation and file format, which every other node uses verbatim.
- Red against the brief baseline: 1 home, `.shared/red.py` (`gauntlet-design.md`). Landing calls it through `land/scripts/verify.py` and parses no listing.
- Copying a file only when absent or identical: 1 designed copy, node `copy-in` of the tree run (worktree cut design). Landing's `record` applies the same rule in the other direction, tree to checkout.
- Rebase, fast-forward and branch removal: no copy. No other Gauntlet file rebases, merges or removes a branch.

Measured in Archon's reference: a wait cannot carry `always_run`, so a resumed run replays the owner's answer and never asks again; `always_run: true` reruns a node on resume while other completed nodes replay; `archon complete --force` removes a worktree whose commits are on no remote, which `archon isolation cleanup` keeps.

## Modules

### `land/land.yaml` (landing's nodes)

The signature and `handoff`'s `output_format` are `gauntlet-design.md`'s. It runs in the checkout; every tree path is reached through `$INPUTS.worktree` and `git -C $INPUTS.worktree`. Nodes `onto`, `rebase`, `test-tree`, `red`, `test-head` and `confirm` carry `always_run: true`, so a resume rebases and verifies against the checkout as it then stands; `show` and `gate` replay. Test-run files sit in the tree's `gauntlet/land/`, keyed by the commits they ran on, so a rerun on the same commits reuses its file.

```yaml
nodes:
  - id: onto                           # the checkout as landing finds it
    always_run: true
    bash: <head = git rev-parse HEAD in the checkout. tip = git -C $INPUTS.worktree rev-parse $INPUTS.branch.
          landed = branch absent, or (tip != $INPUTS.base and git merge-base --is-ancestor tip head).
          moved = head != $INPUTS.base and not landed. print { head, landed, moved }>
    output_format: <object: head (string), landed (boolean), moved (boolean), all required>

  - id: rebase                         # the only rebase in Gauntlet
    depends_on: [onto]
    when: "$onto.output.landed == false"
    always_run: true
    bash: <git -C $INPUTS.worktree rebase $onto.output.head $INPUTS.branch. Already based on head: git does nothing.
          Any refusal or conflict: leave the rebase as git stops it, print git's output and
          "Resolve it in <worktree> (git rebase --continue), then archon workflow resume <run id>.", exit 1>

  - id: test-tree                      # the rebased tree, only when the checkout moved
    depends_on: [rebase]
    when: "$onto.output.moved == true"
    always_run: true
    timeout: <GAUNTLET_TEST_TIMEOUT plus 60 s, in ms; 960000 when unset>
    bash: <GAUNTLET_TEST_BRIEF_COMMAND blank: exit 1 naming it. git -C $INPUTS.worktree checkout $INPUTS.branch.
          file = gauntlet/land/$INPUTS.slug.run.<head>.<tip>.txt in the tree, tip the branch's commit now.
          file absent: run GAUNTLET_TEST_BRIEF_COMMAND in the tree's root as node baseline runs it, written in its
          format. print { file } as an absolute tree path>
    output_format: <object: file (string), required>

  - id: red                            # red without the head check
    depends_on: [test-tree]
    always_run: true
    runtime: uv
    script: verify
    with: { run: $test-tree.output.file, brief: $INPUTS.brief, head: "" }

  - id: test-head                      # the checkout's HEAD alone, only when the rebased tree is red without it
    depends_on: [red]
    when: "$red.output.red == true"
    always_run: true
    timeout: <GAUNTLET_TEST_TIMEOUT plus 60 s, in ms; 960000 when unset>
    bash: <file = gauntlet/land/$INPUTS.slug.head.$onto.output.head.txt in the tree. file absent:
          git -C $INPUTS.worktree checkout --detach $onto.output.head, run GAUNTLET_TEST_BRIEF_COMMAND as test-tree
          does into file, then git -C $INPUTS.worktree checkout $INPUTS.branch, on every exit path.
          print { file } as an absolute tree path>
    output_format: <object: file (string), required>

  - id: confirm                        # red with the head check; red fails the node
    depends_on: [test-head]
    always_run: true
    runtime: uv
    script: verify
    with: { run: $test-tree.output.file, brief: $INPUTS.brief, head: $test-head.output.file }

  - id: show                           # what the owner reads at the gate
    depends_on: [rebase, red, confirm]
    trigger_rule: none_failed_min_one_success
    bash: <print: "Land $INPUTS.slug: fast-forward the checkout from $onto.output.head to $INPUTS.branch?";
          the test line: moved false: "Checkout at base: not rerun."; red false or confirm passed:
          "Rerun on $onto.output.head: no new failure."; then
          git -C $INPUTS.worktree diff --stat $onto.output.head $INPUTS.branch, then
          git -C $INPUTS.worktree log --reverse --format='%h%n%B' $onto.output.head..$INPUTS.branch>

  - id: gate                           # the owner's one choice, answered on gauntlet-run's id
    depends_on: [show]
    wait:
      form: select
      attention: "$show.output"
      options: [ { id: land, label: Land }, { id: leave, label: Leave } ]

  - id: merge                          # the only write to the checkout's tracked files
    depends_on: [gate, rebase, red, confirm]
    trigger_rule: none_failed_min_one_success
    when: "$gate.output.decision == 'land'"
    bash: <git rev-parse HEAD in the checkout != $onto.output.head: print "The checkout moved from <onto> to <now>
          while landing waited. archon workflow resume <run id> rebases, verifies and lands; the answer land stands.",
          exit 1. Else git merge --ff-only $INPUTS.branch; git refusing (uncommitted edits in the files it would
          change): print git's output and "Stash or commit those edits, then archon workflow resume <run id>.", exit 1>

  - id: record                         # the only writer of tree records in the checkout
    depends_on: [merge]
    bash: <for each tree file gauntlet/plans/approved/$INPUTS.slug.rev*.txt, gauntlet/specs/approved/$INPUTS.slug.rev*.txt,
          gauntlet/write/$INPUTS.slug.*, gauntlet/revisions/$INPUTS.slug.* and gauntlet/revisions/$INPUTS.slug-summary.*:
          target the same path in the checkout. Absent: cp -n. Identical (cmp): nothing. Differing: exit 1 naming both
          paths, nothing more copied>

  - id: remove                         # the tree and its branch
    depends_on: [record]
    bash: <branch absent: nothing. Else archon complete $INPUTS.branch --force, its failure exiting non-zero with its output>

  - id: handoff                        # gauntlet-design.md's output_format
    depends_on: [gate, remove]
    trigger_rule: none_failed_min_one_success
    bash: <decision=$gate.output.decision; land: print { "outcome": "landed" }; leave: print { "outcome": "left" }>
```

Every stop is a failed node: a rebase conflict, a red confirm, a moved checkout at merge, a refused merge, a differing record or a failed removal. The tree, its branch and any rebase in progress stay, and `archon workflow resume <run id>` picks the run up there. Landing never aborts a rebase, never stashes, resets or discards the owner's edits, and never cancels the run. Unrelated uncommitted files in the checkout stay as they are. A resume after `merge` sees `landed` true, so it reruns no rebase or test.

Fixtures, `land/fixtures/<route>.stubs.yaml`, one per route: `still` (checkout at base, `test-tree` not reached, land, `landed`); `moved` (`red` false, `test-head` not reached, land, `landed`); `head-red` (`red` true, `confirm` passes, land, `landed`); `red` (`confirm` fails, `gate` not reached); `leave` (`merge` not reached, `left`); `conflict` (`rebase` fails, `gate` not reached); `refused` (`merge` fails, `record` not reached).

### `land/scripts/verify.py` (red at landing)

Reads the test-run files and asks `.shared/red.py`. Imports it as the planning ledger imports `.shared/rounds.py`, computes no comparison and parses no listing. Standard library only. Replaces nothing.

```python
# /// script
# requires-python = ">=3.12"
# ///
# Env: INPUTS_RUN, INPUTS_BRIEF, INPUTS_HEAD: absolute tree paths; INPUTS_HEAD "" for no head check.
# red(<run text>, <brief text>, <head text, or "" when INPUTS_HEAD is "">) from .shared/red.py.
# stdout { "red": bool }; exit 0.
# INPUTS_HEAD not "" and red: stderr names the three paths and "red on the rebased tree; fix it in the tree and
#   commit, then archon workflow resume <run id>"; exit 1.
# A named file missing: stderr names it; exit 2.
def main() -> int: ...
```

Suite: `land/tests/test_verify.py`, run as `docs/testing.md` states with the folder `land/tests`. It drives `main` through real files under `tmp_path`. It pins: a failure only in the run, with no head, printing `red` true; the same failure also failing in the head file, exiting 0 with `red` false; a failure absent from both brief and head exiting 1 and naming the three paths; a missing file exiting 2.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| The commit landing lands against | node `onto`'s `head`, read by `rebase`, the test nodes, `show` and `merge` | any other node reading the checkout's `HEAD`, `merge`'s equality check excepted |
| Rebasing the tree's branch | node `rebase`, `git -C <tree> rebase <head> <branch>` | any other rebase, reset, amend, squash or history rewrite in a Gauntlet file; a rebase in the checkout; a rebase aborted by Gauntlet |
| Whether landing reruns tests | `onto`'s `moved` for `test-tree`; `red`'s answer for `test-head` | a test run when the checkout is at base; a head run when the rebased tree is not red without it; a test run in the checkout |
| Landing's test runs | `test-tree` and `test-head`, as node `baseline` runs its command, into `gauntlet/land/<slug>.run.<head>.<tip>.txt` and `gauntlet/land/<slug>.head.<head>.txt` of the tree | any other file name or folder; another invocation of the brief command in `land/` |
| Red at landing | `land/scripts/verify.py` over `.shared/red.py`; a red with the head check fails `confirm` | a comparison or listing in a `land/` node; a red shown at the gate; a red with no head check stopping the run |
| What the owner sees and answers | `show`'s text and the one `gate` wait, form `select`, options `land` and `leave` | any other wait or agent in `land/`; the gate showing anything but the test line, the diff stat and the commit messages |
| Which tree records reach the checkout | `record`'s five patterns | any other tree file copied, `gauntlet/land/`, `gauntlet/tasks/` and `gauntlet/baseline/` included; a copy that overwrites a differing file |
| A stop in landing | a failed node with the tree kept, resumed by `archon workflow resume` | landing stashing, resetting or discarding the owner's edits; cancelling the run; removing the tree on any stop |

## Order

1. Red at landing: `land/scripts/verify.py`, `land/tests/test_verify.py`. Needs `gauntlet-design.md`'s step 8. Agent: `builder`.
2. Landing block: `land/land.yaml`, `land/fixtures/still.stubs.yaml`, `land/fixtures/moved.stubs.yaml`, `land/fixtures/head-red.stubs.yaml`, `land/fixtures/red.stubs.yaml`, `land/fixtures/leave.stubs.yaml`, `land/fixtures/conflict.stubs.yaml`, `land/fixtures/refused.stubs.yaml`. Needs step 1. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.

`gauntlet-design.md`'s step 11 needs step 2.

## Decisions for the owner

1. What a red on the rebased tree does. Recommend: `confirm` fails the node before the gate; you fix the tree and commit there, and a resume verifies again before asking. Cost: a red run never reaches your gate, so it ends failed or resumed, never as `left`. Alternative: the gate shows the red and you choose land or leave. Cost: one answer lands red code into the checkout; and because Archon replays a gate answer on resume, a red found on a resume after the checkout moved fails the node anyway.
