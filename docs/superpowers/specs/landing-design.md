Status: proposed.

# Gauntlet landing

## Why

Landing is phase 6, block `land` of `gauntlet-run`, after `cut`, when writing hands off `written`. `gauntlet-design.md` gives its place in the run, its signature and hand-off, the fast-forward merge as the only write to the checkout's tracked files, the record copy, the tree's removal by `archon complete <branch> --force`, and `.shared/red.py`. This file gives every other node of `land/land.yaml` and nothing that design states. Every path is relative to the pack root unless it names the checkout or the tree.

By landing time the checkout may have moved past base and may hold uncommitted edits. Landing rebases the tree's branch onto the checkout's `HEAD`, verifies the rebased tree only when the checkout has moved, and mends a red on the rebased tree inside the run: the owner picks a code mend or a test mend and guides it, a fenced agent commits the mend in the tree, a reviewer reads it, and the owner sees each attempt before the next. Then landing shows the owner the diff stat and the commit messages, waits for land or leave, and on land fast-forwards the checkout, copies the records and removes the tree. It runs git, the brief test command, one script, Archon's CLI and, only in the mend, three agents.

What the designs hold for the concerns landing touches:

- Running a test command from a bash node: 3 designed copies of one invocation, `timeout -k 10 "${GAUNTLET_TEST_TIMEOUT:-900}" nice -n 10 bash -c "<command>" < /dev/null` in the tree's root, writing `exit=<n> timed_out=<true|false>` then the output: node `baseline` of the tree run, for `GAUNTLET_TEST_COMMAND` (worktree cut design) and `GAUNTLET_TEST_BRIEF_COMMAND` (writing design), and node `test` of writing. Landing's three test nodes make 6. `fence/checks.py` runs a test command for agents only, as an MCP tool, so no bash node can call it. Named scripts resolve only from a workflow's own `scripts/`, and the repository's `env:` is measured to reach bash nodes only, so no shared runner can hold the invocation. Its one home is node `baseline`'s invocation and file format, which every other node uses verbatim.
- Red against the brief baseline: 1 home, `.shared/red.py` (`gauntlet-design.md`). Landing calls it through `land/scripts/verify.py` and parses no listing.
- Copying a file only when absent or identical: 1 designed copy, node `copy-in` of the tree run (worktree cut design). Landing's `record` applies the same rule in the other direction, tree to checkout.
- Rebase, fast-forward and branch removal: no copy. No other Gauntlet file rebases, merges or removes a branch.
- Fences for an agent writing code or tests: 2 designed copies, `write-code/coder.mcp.json` and `write-tests/test-writer.mcp.json` (writing design), both rooted at the agent's own working folder. The mend's two writers take their settings verbatim, plus read access to `gauntlet/land`, rooted at the tree.

Measured in Archon's reference: a wait cannot carry `always_run`, so a resumed run replays the owner's answer and never asks again; `always_run: true` reruns a node on resume while other completed nodes replay, and the reference excludes it from no `loop_group`; `archon complete --force` removes a worktree whose commits are on no remote, which `archon isolation cleanup` keeps. A `loop_group` whose body ends in an attention wait as its sole terminal sink asks once per iteration, hands the answer to the next iteration as `$LOOP_PREV.<wait>.output`, and lets each accepted answer run one iteration past `max_iterations`; a failure resume restarts the group at iteration 1; `$group.output` is the output of the nodes the wait depends on; a `select` wait answers `{ decision, text }` and may take its options from an upstream output. Unmeasured: whether Archon can root a node's agent and its MCP servers at a folder known only at run time, the tree.

## Modules

### `land/land.yaml` (landing's nodes)

The signature and `handoff`'s `output_format` are `gauntlet-design.md`'s. It runs in the checkout; every tree path is reached through `$INPUTS.worktree` and `git -C $INPUTS.worktree`. Nodes `onto`, `rebase`, `test-tree`, `red`, `test-head`, `confirm` and the group `mend` carry `always_run: true`, so a resume rebases, verifies and mends against the checkout as it then stands; `show` and `gate` replay. Test-run files sit in the tree's `gauntlet/land/`, keyed by the commits they ran on, so a rerun on the same commits reuses its file.

The mend's agents run with the tree as their working folder and their fences rooted at the tree, as writing's agents run in the tree. Step 3 measures first how Archon roots them there; with no way in Archon, step 3 stops and reports the gap.

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

  - id: confirm                        # red with the head check; red opens the mend
    depends_on: [test-head]
    always_run: true
    runtime: uv
    script: verify
    with: { run: $test-tree.output.file, brief: $INPUTS.brief, head: $test-head.output.file }

  - id: mend                           # the only writer in the tree after writing, only on a confirmed red
    depends_on: [confirm]
    when: "$confirm.output.red == true"
    always_run: true
    loop_group:
      max_iterations: 1                # every further iteration follows an owner answer at ask
      fresh_context: true
      until_bash: 'decision=$ask.output.decision; [ "$decision" = done ] || [ "$decision" = leave ]'
      nodes:
        - id: mend-code                # owner chose a code mend; iteration 1 runs neither mender
          when: "$LOOP_PREV.ask.output.decision == 'mend-code'"
          command: mend-code
          context: fresh
          allowed_tools: []
          mcp: mend-code.mcp.json
          prompt: <the owner's guidance $LOOP_PREV.ask.output.text; the latest review gauntlet/land/$INPUTS.slug.mend.<n>.txt;
                  the latest run file and $test-head.output.file; the approved plan gauntlet/plans/approved/$INPUTS.slug.txt
                  and each of its revisions in order of N>
          output_format: <object: outcome (committed | contest | commit-failed), commit (string), grounds (string), all required>

        - id: mend-tests               # owner chose a test mend
          when: "$LOOP_PREV.ask.output.decision == 'mend-tests'"
          command: mend-tests
          context: fresh
          allowed_tools: []
          mcp: mend-tests.mcp.json
          prompt: <as mend-code, with the approved spec gauntlet/specs/approved/$INPUTS.slug.txt and its revisions in place of the plan>
          output_format: <as mend-code>

        - id: retest                   # the branch as the mend left it
          depends_on: [mend-code, mend-tests]
          trigger_rule: none_failed_min_one_success
          timeout: <GAUNTLET_TEST_TIMEOUT plus 60 s, in ms; 960000 when unset>
          bash: <as test-tree, unconditionally, into gauntlet/land/$INPUTS.slug.run.$onto.output.head.<tip>.txt; iteration 1
                reuses test-tree's file. n = count of gauntlet/land/$INPUTS.slug.mend.*.txt in the tree, plus 1.
                print { file, n } with file an absolute tree path>
          output_format: <object: file (string), n (integer), all required>

        - id: recheck                  # red with the head check, on the mended branch
          depends_on: [retest]
          runtime: uv
          script: verify
          with: { run: $retest.output.file, brief: $INPUTS.brief, head: $test-head.output.file }

        - id: review                   # every attempt read before the owner answers; iteration 1 is the diagnosis
          depends_on: [recheck]
          command: mend-review
          context: fresh
          allowed_tools: []
          mcp: mend-review.mcp.json
          prompt: <review file gauntlet/land/$INPUTS.slug.mend.$retest.output.n.txt; the run files $test-tree.output.file,
                  $retest.output.file and $test-head.output.file; recheck's red; the owner's guidance $LOOP_PREV.ask.output.text;
                  the menders' outcome and grounds, when one ran; git -C $INPUTS.worktree log and diff of
                  $onto.output.head..$INPUTS.branch; the approved plan and spec with their revisions in order of N>
          output_format: <object: verdict (SOUND | UNSOUND | DIAGNOSIS), file (string), all required>

        - id: pose                     # what the owner reads at ask, and the choices
          depends_on: [review]
          bash: <red = $recheck.output.red. attention: "Mend $INPUTS.slug on $onto.output.head:" then the test line ("red: see the
                review" or "no new failure"), the review file's text, git -C $INPUTS.worktree diff --stat and
                log --reverse --format='%h%n%B' of $onto.output.head..$INPUTS.branch. options: red: mend-code, mend-tests, leave;
                not red: done, mend-code, mend-tests. Labels: done "Accept the mend", mend-code "Mend the code (guidance in the text)",
                mend-tests "Mend the tests (guidance in the text)", leave "Leave". print { red, attention, options }>
          output_format: <object: red (boolean), attention (string), options (array of { id, label }), all required>

        - id: ask                      # the owner's guidance and choice, once per attempt
          depends_on: [pose]
          wait:
            form: select
            attention: "$pose.output.attention"
            options: "$pose.output.options"

  - id: show                           # what the owner reads at the gate
    depends_on: [rebase, red, confirm, mend]
    trigger_rule: none_failed_min_one_success
    when: "$mend.output.red != true"   # a skipped mend reads as not red
    bash: <print: "Land $INPUTS.slug: fast-forward the checkout from $onto.output.head to $INPUTS.branch?";
          the test line: moved false: "Checkout at base: not rerun."; red false or confirm not red:
          "Rerun on $onto.output.head: no new failure."; mend ran: "Mended on $onto.output.head: no new failure.";
          then git -C $INPUTS.worktree diff --stat $onto.output.head $INPUTS.branch, then
          git -C $INPUTS.worktree log --reverse --format='%h%n%B' $onto.output.head..$INPUTS.branch>

  - id: gate                           # the owner's land or leave, answered on gauntlet-run's id
    depends_on: [show]
    wait:
      form: select
      attention: "$show.output"
      options: [ { id: land, label: Land }, { id: leave, label: Leave } ]

  - id: merge                          # the only write to the checkout's tracked files
    depends_on: [gate, rebase, red, confirm, mend]
    trigger_rule: none_failed_min_one_success
    when: "$gate.output.decision == 'land' && $mend.output.red != true"
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
    depends_on: [gate, remove, mend]
    trigger_rule: none_failed_min_one_success
    bash: <mend red true: print { "outcome": "left" }. Else decision=$gate.output.decision; land: print { "outcome": "landed" };
          leave: print { "outcome": "left" }>
```

Every stop is a failed node: a rebase conflict, a failed mend node, a moved checkout at merge, a refused merge, a differing record or a failed removal. The tree, its branch and any rebase in progress stay, and `archon workflow resume <run id>` picks the run up there; a resumed `mend` starts at iteration 1 and asks again. A red on the rebased tree is no stop: it opens `mend`. The mend ends only on the owner's `done`, with the branch not red, or `leave`, which ends the run `left` with the tree kept. Mend commits sit on top of `<slug>: final`; landing never resets, amends or drops a commit, never aborts a rebase, never stashes, resets or discards the owner's edits, and never cancels the run. Unrelated uncommitted files in the checkout stay as they are. A resume after `merge` sees `landed` true, so it reruns no rebase, test or mend.

Fixtures, `land/fixtures/<route>.stubs.yaml`, one per route: `still` (checkout at base, `test-tree` not reached, land, `landed`); `moved` (`red` false, `test-head` not reached, land, `landed`); `head-red` (`red` true, `confirm` not red, `mend` not reached, land, `landed`); `mend` (`confirm` red; iteration 1 diagnosis, `mend-code`; iteration 2 `mend-code` committed, `recheck` not red, `done`; land, `landed`); `mend-tests` (`confirm` red; `mend-tests` committed, `recheck` not red, `done`; land, `landed`); `mend-leave` (`confirm` red, `leave` at `ask`, `gate` not reached, `left`); `leave` (`merge` not reached, `left`); `conflict` (`rebase` fails, `gate` not reached); `refused` (`merge` fails, `record` not reached).

### `land/commands/mend-code.md`, `land/commands/mend-tests.md`, `land/commands/mend-review.md` (the mend's roles)

The three agents of the mend. Each starts a fresh session, primed from files. Replaces nothing.

```markdown
mend-code
Inputs: the owner's guidance, the latest review, the rebased tree's red run file and the head file, the approved
plan with its revisions. Work from the approved plan and the owner's guidance only.
Make the failing tests the run file names pass on the rebased tree, changing code only. Run the repository's tests
through fence-checks as often as the work needs.
A test you believe wrong: stop, outcome contest, grounds. Never ask for a test to be changed any other way.
Done: commit through the commit tool, with a message of your own and the paths you changed. A failed commit: stop,
outcome commit-failed, the tool's output as grounds. Never retry it.
Tools: fence-files, fence-checks.
```

```markdown
mend-tests
Inputs: the owner's guidance, the latest review, the rebased tree's red run file and the head file, the approved
spec with its revisions. Work from the approved spec and the owner's guidance only.
Change only the tests the run file names as failing, and only where the checkout's HEAD changed what they test.
A change to a test's contract: only to match the approved spec. A test the spec makes impossible to keep: stop,
outcome contest, grounds.
Done: commit through the commit tool, with a message of your own and the paths you changed. A failed commit: stop,
outcome commit-failed, the tool's output as grounds. Never retry it.
Tools: fence-files, fence-checks.
```

```markdown
mend-review
Inputs: the review file to write, the run files, recheck's red, the owner's guidance, the mender's outcome and grounds,
the log and diff of the branch past the checkout's HEAD, the approved plan and spec with their revisions.
No mender ran (iteration 1): verdict DIAGNOSIS. Write which tests fail on the rebased tree, which commits of the
checkout's HEAD and of the branch meet in them, and whether a code mend or a test mend fits, with why.
A mender ran: verdict SOUND or UNSOUND. UNSOUND when the mend departs from the approved plan or spec, from the owner's
guidance, or changes a test's contract the approved spec does not require, or when it leaves the tree red. Write
each finding with its path. Write the review file once; write nothing else.
Tools: fence-files.
```

Fences, one file each beside `land/land.yaml`, every server rooted at the tree, launched by `sh -c` with every `FENCE_*` built from the repository's `env:` in the launch line:

| File | Server | Settings |
|---|---|---|
| `mend-code.mcp.json` | `fence-files` | `write-code/coder.mcp.json`'s, verbatim |
| `mend-code.mcp.json` | `fence-checks` | `write-code/coder.mcp.json`'s, verbatim |
| `mend-tests.mcp.json` | `fence-files` | `write-tests/test-writer.mcp.json`'s, with `:gauntlet/land` added to `FENCE_READ` |
| `mend-tests.mcp.json` | `fence-checks` | `write-tests/test-writer.mcp.json`'s, verbatim |
| `mend-review.mcp.json` | `fence-files` | `FENCE_READ=.`; `FENCE_WRITE=gauntlet/land/*.mend.*.txt`; `FENCE_ONCE=gauntlet/land/*.mend.*.txt`; `FENCE_COMMIT` unset |

### `land/scripts/verify.py` (red at landing)

Reads the test-run files and asks `.shared/red.py`. Imports it as the planning ledger imports `.shared/rounds.py`, computes no comparison and parses no listing. Standard library only. Replaces nothing.

```python
# /// script
# requires-python = ">=3.12"
# ///
# Env: INPUTS_RUN, INPUTS_BRIEF, INPUTS_HEAD: absolute tree paths; INPUTS_HEAD "" for no head check.
# red(<run text>, <brief text>, <head text, or "" when INPUTS_HEAD is "">) from .shared/red.py.
# stdout { "red": bool }; exit 0, red or not.
# A named file missing: stderr names it; exit 2.
def main() -> int: ...
```

Suite: `land/tests/test_verify.py`, run as `docs/testing.md` states with the folder `land/tests`. It drives `main` through real files under `tmp_path`. It pins: a failure only in the run, with no head, printing `red` true; the same failure also failing in the head file, printing `red` false; a failure absent from both brief and head printing `red` true and exiting 0; a missing file exiting 2.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| The commit landing lands against | node `onto`'s `head`, read by `rebase`, the test nodes, `mend`, `show` and `merge` | any other node reading the checkout's `HEAD`, `merge`'s equality check excepted |
| Rebasing the tree's branch | node `rebase`, `git -C <tree> rebase <head> <branch>` | any other rebase, reset, amend, squash or history rewrite in a Gauntlet file; a rebase in the checkout; a rebase aborted by Gauntlet |
| Whether landing reruns tests | `onto`'s `moved` for `test-tree`; `red`'s answer for `test-head`; each mend iteration for `retest` | a test run when the checkout is at base; a head run when the rebased tree is not red without it; a test run in the checkout |
| Landing's test runs | `test-tree`, `test-head` and `retest`, as node `baseline` runs its command, into `gauntlet/land/<slug>.run.<head>.<tip>.txt` and `gauntlet/land/<slug>.head.<head>.txt` of the tree | any other file name or folder; another invocation of the brief command in `land/` |
| Red at landing | `land/scripts/verify.py` over `.shared/red.py`; a red with the head check opens `mend` | a comparison or listing in a `land/` node; a red shown at the gate; a red stopping the run |
| Mending a red on the rebased tree | group `mend`: the owner's choice at `ask` runs one mender, `mend-code` fenced out of `tests/` and `gauntlet/`, `mend-tests` fenced to `tests/` and the test base; `mend-review` reviews every attempt into `gauntlet/land/<slug>.mend.<n>.txt`; `done` offered only when `recheck` is not red | a mend the owner did not choose; one agent writing both code and tests; a mend commit that reaches the gate unreviewed; a mend in the checkout; any other agent writing in the tree during landing |
| What the owner sees and answers | `mend`'s `ask`, form `select`, with `pose`'s text and options; `show`'s text and the one `gate` wait, form `select`, options `land` and `leave` | any other wait or agent in `land/`; the gate showing anything but the test line, the diff stat and the commit messages |
| Which tree records reach the checkout | `record`'s five patterns | any other tree file copied, `gauntlet/land/`, `gauntlet/tasks/` and `gauntlet/baseline/` included; a copy that overwrites a differing file |
| A stop in landing | a failed node with the tree kept, resumed by `archon workflow resume` | landing stashing, resetting or discarding the owner's edits; cancelling the run; removing the tree on any stop; a red ending the run outside the owner's `leave` |

## Order

1. Red at landing: `land/scripts/verify.py`, `land/tests/test_verify.py`. Needs `gauntlet-design.md`'s step 8. Agent: `builder`.
2. The mend's roles: `land/commands/mend-code.md`, `land/commands/mend-tests.md`, `land/commands/mend-review.md`. Agent: `role-author`.
3. Landing block: `land/land.yaml`, `land/mend-code.mcp.json`, `land/mend-tests.mcp.json`, `land/mend-review.mcp.json`, `land/fixtures/still.stubs.yaml`, `land/fixtures/moved.stubs.yaml`, `land/fixtures/head-red.stubs.yaml`, `land/fixtures/mend.stubs.yaml`, `land/fixtures/mend-tests.stubs.yaml`, `land/fixtures/mend-leave.stubs.yaml`, `land/fixtures/leave.stubs.yaml`, `land/fixtures/conflict.stubs.yaml`, `land/fixtures/refused.stubs.yaml`. Needs steps 1 and 2 and writing's `write-code/coder.mcp.json` and `write-tests/test-writer.mcp.json`. Measures first how Archon roots the mend's agents and fences at the tree. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.

`gauntlet-design.md`'s step 11 needs step 3.

## Decisions for the owner

1. Whether you may accept a mend the reviewer finds unsound. Recommend: `done` is offered whenever the branch is not red, with the review's UNSOUND findings shown above it; you are the last reviewer. Cost: an unsound mend lands if you accept it. Alternative: `done` is withheld while the latest review is UNSOUND, so you must ask for another mend or leave. Cost: a reviewer you disagree with can keep a clean tree from landing, and each further attempt spends a mender and a review, unmeasured.
