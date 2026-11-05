Status: proposed.

# Gauntlet landing

## Why

Landing is two blocks. Block `mend`, `mend/mend.yaml`, runs in the tree as part of the tree run `gauntlet-tree`, after `write`, when writing hands off `written`. Block `land`, `land/land.yaml`, is phase 7 of `gauntlet-run`, after `cut`, when the tree run hands off `ready`. `gauntlet-design.md` gives the fast-forward merge as the only write to the checkout's tracked files, the record copy, the tree's removal by `archon complete <branch> --force`, and `.shared/red.py`. This file gives both blocks' nodes and signatures. Every path is relative to the pack root unless it names the checkout or the tree.

By the end of writing the checkout may have moved past base and may hold uncommitted edits. Block `mend` reads the checkout's `HEAD`, rebases the tree's branch onto it, verifies the rebased tree only when the checkout has moved (or a first pass already rebased the branch, so a resume reruns it), and mends a red on the rebased tree: a juror rules each red a code mend, a test mend or defective, the mender it names commits the mend, and a reviewer reads every mend. The owner is asked on the tree run's id, in plain words and with no diff, only when the juror rules defective or the mend stalls, and answers with guidance, a rerun or leave. It runs git, the brief test command, one script and, only in the repair, four agents. Block `land` shows the owner the test line, the diff stat and the commit messages, waits for land or leave, and on land fast-forwards the checkout, copies the records and removes the tree. It runs git and Archon's CLI only, and no agent.

An agent runs in its run's checkout, and no node field sets another folder; `fence/files.py` and `fence/checks.py` root at `CLAUDE_PROJECT_DIR`, the agent's folder. The tree run is the only run whose checkout is the tree, so every agent that writes in the tree, the mend's four included, runs in the tree run.

What the designs hold for the concerns landing touches:

- Running a test command from a bash node: 2 designed copies of one invocation, `timeout -k 10 "${GAUNTLET_TEST_TIMEOUT:-900}" nice -n 10 bash -c "<command>" < /dev/null` in the tree's root, writing `exit=<n> timed_out=<true|false>` then the output: node `baseline` of the tree run, for `GAUNTLET_TEST_BRIEF_COMMAND` (worktree cut design), and node `test` of writing. The mend's three test nodes make 5. `fence/checks.py` runs a test command for agents only, as an MCP tool, so no bash node can call it. Named scripts resolve only from a workflow's own `scripts/`, and the repository's `env:` is measured to reach bash nodes only, so no shared runner can hold the invocation. Its one home is node `baseline`'s invocation and file format, which every other node uses verbatim.
- Red against the brief baseline: 1 home, `.shared/red.py` (`gauntlet-design.md`). The mend calls it through `mend/scripts/verify.py` and parses no listing.
- Copying a file only when absent or identical: 1 designed copy, node `copy-in` of the tree run (worktree cut design). Landing's `record` applies the same rule in the other direction, tree to checkout.
- Rebase, fast-forward and branch removal: no copy. No other Gauntlet file rebases, merges or removes a branch.
- Fences for an agent writing code or tests: 2 designed copies, `write-code/coder.mcp.json` and `write-tests/test-writer.mcp.json` (writing design), both rooted at the agent's own working folder, the tree. The mend's two writers take their settings verbatim, plus read access to `gauntlet/mend`.
- Ruling on a red: 1 designed juror, `write/commands/juror.md` (writing design), with verdicts `TESTS`, `CODE`, `SPEC`, `PLAN` and `DEFECTIVE` over writing's cases. The mend's juror, `mend/commands/mend-juror.md`, rules only a red on the rebased tree, with verdicts `CODE`, `TESTS` and `DEFECTIVE`, and revises no plan or spec.
- Asking the owner on a stall: 1 designed copy, writing's `stalled` case (5 verdicts since the latest owner ruling) answered at `bench`. The mend asks on the same count, on the same run's id.
- Reading the checkout from the tree run: no copy. The checkout root (the tree run's `task` input without its trailing `/gauntlet/tasks/<slug>.md`, worktree cut design) is read by node `copy-in` for files; the mend's `onto` is the only node reading the checkout's `HEAD` from the tree run.

Measured in Archon's reference: a wait cannot carry `always_run`, so a resumed run replays the owner's answer and never asks again; `always_run: true` reruns a node on resume while other completed nodes replay, and the reference excludes it from no `loop_group`; `archon complete --force` removes a worktree whose commits are on no remote, which `archon isolation cleanup` keeps. A `loop_group` whose body ends in an attention wait as its sole terminal sink asks at most once per iteration, may skip the ask by its `when:`, in which case `until_bash` must read the work and not the skipped wait, hands the answer to the next iteration as `$LOOP_PREV.<wait>.output`, and lets each accepted answer run one iteration past `max_iterations`; a failure resume restarts the group at iteration 1; `$group.output` is the output of the nodes the wait depends on; a `select` wait answers `{ decision, text }` and may take its options from an upstream output. Unmeasured: whether a resumed `tree` node of `gauntlet-run` resumes its child run's completed nodes or runs them anew; the mend's `always_run` nodes rerun either way.

## Modules

### `mend/mend.yaml` (the mend: rebase, verify, repair)

Included by `gauntlet-tree` only, as node `mend` after `write`, when `$write.output.outcome == 'written'`, with `slug`, `checkout`, `branch` and `brief` from its node `paths`. The tree run's `handoff` prints the mend's `outcome` in place of writing's when the mend ran, and its `line`. It runs in the tree: every path it reads or writes is in the tree, and it reads the checkout only by `git -C $INPUTS.checkout rev-parse HEAD`. Nodes `onto`, `rebase`, `test-tree`, `red`, `test-head`, `confirm` and the group `repair` carry `always_run: true`, so a resume rebases, verifies and mends against the checkout as it then stands. Test-run files sit in `gauntlet/mend/`, keyed by the commits they ran on, so a rerun on the same commits reuses its file. Its waits are answered on the tree run's id.

```yaml
name: mend
description: >-
  Gauntlet mend, included by gauntlet-tree only. Not for direct use.
inputs:
  slug: { description: The task's slug. }
  checkout: { description: Absolute path of the owner's checkout. }
  branch: { description: The tree's branch. }
  brief: { description: Absolute tree path of gauntlet/baseline/<slug>.brief.txt. }
returns: handoff

nodes:
  - id: onto                           # the checkout's HEAD as the mend finds it
    always_run: true
    bash: <head = git -C $INPUTS.checkout rev-parse HEAD. tip = git rev-parse $INPUTS.branch.
          moved = not (git merge-base --is-ancestor head tip), or the file gauntlet/mend/$INPUTS.slug.rebased.<head> exists
          (a first pass already rebased the branch onto this head, so a resume still reruns the tests). print { head, moved }>
    output_format: <object: head (string), moved (boolean), all required>

  - id: rebase                         # the only rebase in Gauntlet
    depends_on: [onto]
    always_run: true
    bash: <git rebase $onto.output.head $INPUTS.branch. Already based on head: git does nothing. A rebase that changed the
          branch: write gauntlet/mend/$INPUTS.slug.rebased.<head> by cp -n semantics.
          Any refusal or conflict: leave the rebase as git stops it, print git's output and
          "Resolve it in <tree> (git rebase --continue), then archon workflow resume <gauntlet-run id>.", exit 1>

  - id: test-tree                      # the rebased tree, when the checkout moved or a first pass rebased it
    depends_on: [rebase]
    when: "$onto.output.moved == true"
    always_run: true
    bash: <GAUNTLET_TEST_BRIEF_COMMAND blank: exit 1 naming it. git checkout $INPUTS.branch.
          file = gauntlet/mend/$INPUTS.slug.run.<head>.<tip>.txt, tip the branch's commit now.
          file absent: run GAUNTLET_TEST_BRIEF_COMMAND in the tree's root as node baseline runs it, written in its
          format. print { file } as an absolute tree path>
    output_format: <object: file (string), required>

  - id: red                            # red without the head check
    depends_on: [test-tree]
    always_run: true
    runtime: uv
    script: verify
    with: { run: $test-tree.output.file, head: "" }

  - id: test-head                      # the checkout's HEAD alone, only when the rebased tree is red without it
    depends_on: [red]
    when: "$red.output.red == true"
    always_run: true
    bash: <file = gauntlet/mend/$INPUTS.slug.head.$onto.output.head.txt. file absent:
          git checkout --detach $onto.output.head, run GAUNTLET_TEST_BRIEF_COMMAND as test-tree
          does into file, then git checkout $INPUTS.branch, on every exit path.
          print { file } as an absolute tree path>
    output_format: <object: file (string), required>

  - id: confirm                        # red with the head check; red opens the repair
    depends_on: [test-head]
    always_run: true
    runtime: uv
    script: verify
    with: { run: $test-tree.output.file, head: $test-head.output.file }

  - id: repair                         # the only writer in the tree after writing, only on a confirmed red
    depends_on: [confirm]
    when: "$confirm.output.red == true"
    always_run: true
    loop_group:
      max_iterations: 200              # from iteration 200 every iteration asks, so the bound never fails the run
      fresh_context: true
      until_bash: 'end=$pose.output.end; [ -n "$end" ]'
      nodes:
        - id: hear                     # the owner's last answer, kept in the tree; every iteration
          bash: <n = one above the highest n among the verdict, review and reply files gauntlet/mend/$INPUTS.slug.*.<n>.txt.
                $LOOP_PREV.ask.output.decision reply: write $LOOP_PREV.ask.output.text verbatim to
                gauntlet/mend/$INPUTS.slug.reply.<n>.txt by cp -n semantics; retry: write the word retry to that file the same way.
                print { n, left, retry } with left true only when that decision is leave and retry true only when it is retry>
          output_format: <object: n (integer), left (boolean), retry (boolean), all required>

        - id: juror                    # rules every red in the repair, but a retry; the owner never picks a mender
          depends_on: [hear]
          when: "$hear.output.left == false && $hear.output.retry == false"
          command: mend-juror
          context: fresh
          allowed_tools: []
          mcp: mend-juror.mcp.json
          prompt: <verdict file gauntlet/mend/$INPUTS.slug.verdict.$hear.output.n.txt; the case: $LOOP_PREV.pose.output.case,
                  or $test-tree.output.file when empty; $test-head.output.file; every gauntlet/mend/$INPUTS.slug.verdict.*,
                  .review.* and .reply.* file in order of n; git log and diff of $onto.output.head..$INPUTS.branch;
                  the approved plan and spec with their revisions in order of N>
          output_format: <object: verdict (CODE | TESTS | DEFECTIVE), file (string), all required>

        - id: mend-code                # the juror ruled CODE
          depends_on: [juror]
          when: "$juror.output.verdict == 'CODE'"
          command: mend-code
          context: fresh
          allowed_tools: []
          mcp: mend-code.mcp.json
          prompt: <the verdict file $juror.output.file; the latest run file and $test-head.output.file; the approved plan
                  gauntlet/plans/approved/$INPUTS.slug.txt and each of its revisions in order of N>
          output_format: <object: outcome (committed | contest | commit-failed), commit (string), grounds (string), all required>

        - id: mend-tests               # the juror ruled TESTS
          depends_on: [juror]
          when: "$juror.output.verdict == 'TESTS'"
          command: mend-tests
          context: fresh
          allowed_tools: []
          mcp: mend-tests.mcp.json
          prompt: <as mend-code, with the approved spec gauntlet/specs/approved/$INPUTS.slug.txt and its revisions in place of the plan>
          output_format: <as mend-code>

        - id: retest                   # the branch as the mender left it; runs only after a committed mend or a retry
          depends_on: [hear, mend-code, mend-tests]
          trigger_rule: none_failed_min_one_success
          when: "$mend-code.output.outcome == 'committed' || $mend-tests.output.outcome == 'committed' || $hear.output.retry == true"
          bash: <as test-tree, unconditionally, into gauntlet/mend/$INPUTS.slug.run.$onto.output.head.<tip>.txt, the key differing from
                test-tree's file by construction after a committed mend; after a retry the file is rewritten by cp -n semantics
                under the retry's n: gauntlet/mend/$INPUTS.slug.run.$onto.output.head.<tip>.retry.$hear.output.n.txt.
                print { file } as an absolute tree path>
          output_format: <object: file (string), required>

        - id: recheck                  # red with the head check, on the mended or retried branch
          depends_on: [retest]
          runtime: uv
          script: verify
          with: { run: $retest.output.file, head: $test-head.output.file }

        - id: review                   # every committed mend read before it can end the repair; not after a retry or a red recheck
          depends_on: [recheck]
          when: "$recheck.output.red == false && $hear.output.retry == false"
          command: mend-review
          context: fresh
          allowed_tools: []
          mcp: mend-review.mcp.json
          prompt: <review file gauntlet/mend/$INPUTS.slug.review.$hear.output.n.txt; the verdict file $juror.output.file; the run
                  files $retest.output.file and $test-head.output.file; recheck's red; the mender's outcome and grounds;
                  git log and diff of $onto.output.head..$INPUTS.branch; the approved plan and spec with
                  their revisions in order of N>
          output_format: <object: verdict (SOUND | UNSOUND), file (string), all required>

        - id: pose                     # whether the repair ends, the next case, and whether to ask the owner
          depends_on: [hear, juror, review]
          trigger_rule: none_failed_min_one_success
          bash: <First that holds. hear left: end "left". A committed mend, recheck not red and review SOUND: end "done". A
                retry whose rerun is not red, with no uncommitted mend (git status --porcelain empty, gauntlet/ excluded):
                end "done". Else end "", and case = newline-separated tree paths the next juror reads: the latest run file
                and the latest review file it holds, each when there is one, and the mender's grounds written by cp -n to
                gauntlet/mend/$INPUTS.slug.grounds.$hear.output.n.txt when it did not commit.
                ask true when end is "" and (juror DEFECTIVE, or verdicts since the latest reply file >= 5, or
                hear.n >= 200). attention, in plain words with no diff: "Mending $INPUTS.slug after the rebase onto
                $onto.output.head." then the juror's verdict file text, which states in plain words what fails, why, and what
                the juror needs to know. options [ { id: reply, label: "Guide the juror (your guidance in the text)" },
                { id: retry, label: "Rerun the tests, no mender" }, { id: leave, label: Leave } ].
                print { end, case, ask, attention, options }>
          output_format: <object: end ("" | done | left), case (string), ask (boolean), attention (string),
                         options (array of { id, label }), all required>

        - id: ask                      # the owner, only on DEFECTIVE, a stall or the 200th iteration; sole terminal sink of the body
          depends_on: [pose]
          when: "$pose.output.ask == true"
          wait:
            form: select
            attention: "$pose.output.attention"
            options: "$pose.output.options"

  - id: handoff                        # the mend's returns, read by the tree run's handoff
    depends_on: [rebase, red, confirm, repair]
    trigger_rule: none_failed_min_one_success
    bash: <repair end left: print { "outcome": "left", "line": "" }. Else outcome "ready" and line, the test line the
          gate shows: moved false: "Checkout not moved past the tree's base: not rerun."; red false or confirm not red:
          "Rerun on $onto.output.head: no new failure."; repair ran with a committed mend: "Mended on $onto.output.head: no new
          failure."; repair ran with no committed mend (the branch tip is the rebased tip test-tree ran on): "Rerun on
          $onto.output.head after retry: no new failure.">
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [ready, left] }
        line: { type: string }
      required: [outcome, line]
```

Every stop is a failed node: a rebase conflict or a failed repair node. It fails the tree run and so `gauntlet-run`'s node `tree`; the tree, its branch and any rebase in progress stay, and `archon workflow resume <gauntlet-run id>` picks the run up there; a resumed `repair` starts at iteration 1, its verdict, review and reply files kept. A red on the rebased tree is no stop: it opens `repair`. The repair ends when a mend is committed, the branch is not red and the latest review is SOUND, when the owner's retry reruns the tests green with nothing uncommitted, or on the owner's `leave`, which hands off `left` with the tree kept; `gauntlet-run` then ends with no landing. An uncommitted mend (a commit-failed mender) never ends the repair: the juror sees it as the next case. The owner never picks a mender and is never shown a diff in the repair. Mend commits sit on top of the branch's last commit; the mend never resets, amends or drops a commit, never aborts a rebase and never writes in the checkout.

Fixtures, `mend/fixtures/<route>.stubs.yaml`, one per route: `still` (`moved` false, `test-tree` not reached, `ready`); `moved` (`red` false, `test-head` not reached, `ready`); `resumed` (`moved` true on a rebased marker, `test-tree` reached); `head-red` (`red` true, `confirm` not red, `repair` not reached, `ready`); `repair` (`confirm` red; `juror` CODE, `mend-code` committed, `recheck` not red, `review` SOUND, `ask` not reached; `ready`); `repair-tests` (`juror` TESTS, `mend-tests` committed, not red, SOUND; `ready`); `repair-unsound` (`juror` CODE, `review` UNSOUND; iteration 2 `juror` CODE, SOUND; `ready`); `repair-uncommitted` (`mend-code` commit-failed, `retest` not reached, `pose` ends "", iteration 2 `juror` sees the grounds); `repair-reply` (`juror` DEFECTIVE, `ask` answered `reply`; iteration 2 reply file written, `juror` CODE, SOUND; `ready`); `repair-retry` (`juror` DEFECTIVE, `ask` answered `retry`; iteration 2 reply file holds `retry`, `juror` and menders not reached, `retest` green, `ready`); `repair-stall` (5 verdicts with no end, `ask` reached); `repair-leave` (`juror` DEFECTIVE, `leave` at `ask`, `left`); `conflict` (`rebase` fails, `handoff` not reached).

### `land/land.yaml` (landing in the checkout)

Included by `gauntlet-run` only, as node `land` after `cut`, when the tree run hands off `ready`, with `slug` from node `pin`, `worktree` and `branch` from the cut and `line` and `summary` the tree run's. It runs in the checkout, reaches the tree only by `git -C $INPUTS.worktree` and `archon complete`, and writes nothing in the tree. It has no agent node. `onto` carries `always_run: true`, so a resume checks the checkout as it then stands; `show` and `gate` replay.

```yaml
name: land
description: >-
  Gauntlet landing, included by gauntlet-run only. Not for direct use.
inputs:
  slug: { description: The task's slug. }
  worktree: { description: Absolute path of the tree. }
  branch: { description: The tree's branch. }
  line: { description: The mend's test line. }
  summary: { description: The plan summary and the approved revision summaries, shown at the gate. }
returns: handoff

nodes:
  - id: onto                           # the checkout as landing finds it
    always_run: true
    bash: <head = git rev-parse HEAD in the checkout. tip = git -C $INPUTS.worktree rev-parse $INPUTS.branch, "" when
          the branch is absent. tip "", or git merge-base --is-ancestor tip head (landed), or
          git merge-base --is-ancestor head tip (fast-forwards): print { head }. Else print "The checkout moved to <head>
          after the mend rebased $INPUTS.branch; it no longer fast-forwards. Bring the checkout back to an ancestor of
          $INPUTS.branch, then archon workflow resume <run id>.", exit 1>
    output_format: <object: head (string), required>

  - id: show                           # what the owner reads at the gate
    depends_on: [onto]
    bash: <print: "Land $INPUTS.slug: fast-forward the checkout from $onto.output.head to $INPUTS.branch?";
          $INPUTS.line; $INPUTS.summary; then git -C $INPUTS.worktree diff --stat $onto.output.head $INPUTS.branch, then
          git -C $INPUTS.worktree log --reverse --format='%h%n%B' $onto.output.head..$INPUTS.branch>

  - id: gate                           # the owner's land or leave, answered on gauntlet-run's id
    depends_on: [show]
    wait:
      form: select
      attention: "$show.output"
      options: [ { id: land, label: Land }, { id: leave, label: Leave } ]

  - id: merge                          # the only write to the checkout's tracked files
    depends_on: [gate]
    when: "$gate.output.decision == 'land'"
    bash: <git rev-parse HEAD in the checkout != $onto.output.head: print "The checkout moved from <onto> to <now>
          while landing waited. archon workflow resume <run id> lands once the checkout fast-forwards to $INPUTS.branch;
          the answer land stands.", exit 1. Else git merge --ff-only $INPUTS.branch; git refusing (uncommitted edits in
          the files it would change): print git's output and "Stash or commit those edits, then archon workflow resume
          <run id>.", exit 1>

  - id: record                         # the only writer of tree records in the checkout
    depends_on: [merge]
    bash: <for each tree file gauntlet/plans/approved/$INPUTS.slug.rev*.txt, gauntlet/specs/approved/$INPUTS.slug.rev*.txt,
          gauntlet/write/$INPUTS.slug.*, gauntlet/revisions/$INPUTS.slug.* and gauntlet/revisions/$INPUTS.slug-summary.*:
          target the same path in the checkout. Absent: cp -n. Identical (cmp): nothing. Differing: exit 1 naming both
          paths, nothing more copied>

  - id: remove                         # the tree and its branch
    depends_on: [record]
    bash: <branch absent: nothing. Else archon complete $INPUTS.branch --force, its failure exiting non-zero with its output>

  - id: handoff
    depends_on: [gate, remove]
    trigger_rule: none_failed_min_one_success
    bash: <decision=$gate.output.decision; land: print { "outcome": "landed" }; leave: print { "outcome": "left" }>
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [landed, left] }
      required: [outcome]
```

Every stop is a failed node: a checkout that no longer fast-forwards, a checkout moved at merge, a refused merge, a differing record or a failed removal. The tree and its branch stay, and `archon workflow resume <run id>` picks the run up there. Landing never rebases, resets, amends or drops a commit, never stashes, resets or discards the owner's edits, and never cancels the run. Unrelated uncommitted files in the checkout stay as they are. A resume after `merge` finds the branch an ancestor of the checkout, so `onto` passes and `merge` replays.

Fixtures, `land/fixtures/<route>.stubs.yaml`, one per route: `land` (land, `landed`); `leave` (`merge` not reached, `left`); `moved` (`onto` fails, `gate` not reached); `refused` (`merge` fails, `record` not reached).

### `mend/commands/mend-juror.md`, `mend/commands/mend-code.md`, `mend/commands/mend-tests.md`, `mend/commands/mend-review.md` (the mend's roles)

The four agents of the mend. Each starts a fresh session, primed from files. Replaces nothing.

```markdown
mend-juror
Inputs: the verdict file to write, the case files, the head file, every earlier verdict, review and owner reply of
this mend, the log and diff of the branch past the checkout's HEAD, the approved plan and spec with their revisions.
Rule the case. CODE: the code must change to meet the approved plan on the checkout's HEAD. TESTS: a test must change
because the checkout's HEAD changed what it tests, within the approved spec. DEFECTIVE: no mend within the approved
plan and spec fits, or you need the owner's word. Follow every owner reply.
Write the verdict file once: the verdict; for CODE or TESTS, what to change and why, for the mender; then, in plain
words for an owner who does not read diffs, what fails, why, and for DEFECTIVE the question you need answered.
Tools: fence-files.
```

```markdown
mend-code
Inputs: the juror's verdict file, the rebased tree's red run file and the head file, the approved plan with its
revisions. Work from the approved plan and the verdict only.
Make the failing tests the run file names pass on the rebased tree, changing code only. Run the repository's tests
through fence-checks as often as the work needs.
A test you believe wrong: stop, outcome contest, grounds. Never ask for a test to be changed any other way.
Done: commit through the commit tool, with a message of your own and the paths you changed. A failed commit: stop,
outcome commit-failed, the tool's output as grounds. Never retry it.
Tools: fence-files, fence-checks.
```

```markdown
mend-tests
Inputs: the juror's verdict file, the rebased tree's red run file and the head file, the approved spec with its
revisions. Work from the approved spec and the verdict only.
Change only the tests the verdict names, and only where the checkout's HEAD changed what they test.
A change to a test's contract: only to match the approved spec. A test the spec makes impossible to keep: stop,
outcome contest, grounds.
Done: commit through the commit tool, with a message of your own and the paths you changed. A failed commit: stop,
outcome commit-failed, the tool's output as grounds. Never retry it.
Tools: fence-files, fence-checks.
```

```markdown
mend-review
Inputs: the review file to write, the juror's verdict file, the run files, recheck's red, the mender's outcome and
grounds, the log and diff of the branch past the checkout's HEAD, the approved plan and spec with their revisions.
Verdict SOUND or UNSOUND. UNSOUND when the mend departs from the approved plan or spec or from the verdict, changes a
test's contract the approved spec does not require, leaves the tree red, or leaves a mend uncommitted. Write
each finding with its path. Write the review file once; write nothing else.
Tools: fence-files.
```

Fences, one file each beside `mend/mend.yaml`, every server rooted at the agent's own folder, the tree, as writing's are, launched plainly, with the test command and timeout read from `gauntlet/settings.json` and no `sh -c` line building a value:

| File | Server | Settings |
|---|---|---|
| `mend-code.mcp.json` | `fence-files` | `write-code/coder.mcp.json`'s, verbatim |
| `mend-code.mcp.json` | `fence-checks` | `write-code/coder.mcp.json`'s, verbatim |
| `mend-tests.mcp.json` | `fence-files` | `write-tests/test-writer.mcp.json`'s, with `:gauntlet/mend` added to `FENCE_READ` |
| `mend-tests.mcp.json` | `fence-checks` | `write-tests/test-writer.mcp.json`'s, verbatim |
| `mend-juror.mcp.json` | `fence-files` | `FENCE_READ=.`; `FENCE_WRITE=gauntlet/mend/*.verdict.*.txt`; `FENCE_ONCE=gauntlet/mend/*.verdict.*.txt`; `FENCE_COMMIT` unset |
| `mend-review.mcp.json` | `fence-files` | `FENCE_READ=.`; `FENCE_WRITE=gauntlet/mend/*.review.*.txt`; `FENCE_ONCE=gauntlet/mend/*.review.*.txt`; `FENCE_COMMIT` unset |

### `mend/scripts/verify.py` (red in the mend)

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

Suite: `mend/tests/test_verify.py`, run as `docs/testing.md` states with the folder `mend/tests`. It drives `main` through real files under `tmp_path`. It pins: a failure only in the run, with no head, printing `red` true; the same failure also failing in the head file, printing `red` false; a failure absent from both brief and head printing `red` true and exiting 0; a missing file exiting 2.

## Homes

| Concern | Home | Forbidden elsewhere |
|---|---|---|
| Where each landing node runs | block `mend`, included by `gauntlet-tree` after `write`, for the read of the checkout's `HEAD`, the rebase, every test run and every agent; block `land`, included by `gauntlet-run` after `cut`, for the gate, the merge, the record copy and the removal | an agent node in `land/`; a rebase or test run in `land/`; any `land/` node writing in the tree; a `mend/` node writing in the checkout |
| The commit the mend rebases onto | `mend`'s node `onto`'s `head`, by `git -C $INPUTS.checkout rev-parse HEAD`, read by `rebase`, the test nodes, `repair` and `handoff` | any other tree-run node reading the checkout's `HEAD` |
| The commit landing lands against | `land`'s node `onto`'s `head`, read by `show` and `merge` | any other `land/` node reading the checkout's `HEAD`, `merge`'s equality check excepted |
| Rebasing the tree's branch | `mend`'s node `rebase`, `git rebase <head> <branch>` in the tree | any other rebase, reset, amend, squash or history rewrite in a Gauntlet file; a rebase in the checkout; a rebase aborted by Gauntlet |
| Whether the mend reruns tests | `onto`'s `moved` for `test-tree`; `red`'s answer for `test-head`; a committed mend or a retry for `retest` | a retest with no committed mend and no retry; a test run when the checkout's `HEAD` is in the branch's history; a head run when the rebased tree is not red without it; a test run in the checkout |
| The mend's test runs | `test-tree`, `test-head` and `retest`, as node `baseline` runs its command, with no node `timeout:`, into `gauntlet/mend/<slug>.run.<head>.<tip>.txt` and `gauntlet/mend/<slug>.head.<head>.txt` of the tree | any other file name or folder; another invocation of the brief command in `mend/` or `land/` |
| Red in the mend | `mend/scripts/verify.py` over `.shared/red.py`; a red with the head check opens `repair` | a comparison or listing in a `mend/` or `land/` node; a red shown at the gate; a red stopping the run |
| Mending a red on the rebased tree | group `repair` of block `mend`: `mend-juror` rules every red, UNSOUND review and uncommitted mend into `gauntlet/mend/<slug>.verdict.<n>.txt`; its verdict runs one mender, `mend-code` fenced out of `tests/` and `gauntlet/`, `mend-tests` fenced to `tests/` and the test base; `mend-review` reviews every mend into `gauntlet/mend/<slug>.review.<n>.txt`; `pose` ends the repair only on a committed mend, not red and SOUND, or on a retry rerun that is not red with nothing uncommitted | the owner picking a mender; a mender run without a juror verdict; one agent writing both code and tests; a mend that ends unreviewed; a mend in the checkout; any other agent writing in the tree after writing |
| The test line at the gate | `mend`'s `handoff` `line`, carried by the tree run's `handoff` and `cut` to `land`'s input `line`; the plan and revision summaries, `write`'s `summary`, carried the same way to `land`'s input `summary` | any other node composing them |
| What the owner sees and answers | on the tree run's id, `repair`'s `ask`, only on DEFECTIVE, 5 verdicts since the latest reply, or `hear.n >= 200`, in plain words from the verdict file, options `reply`, `retry` and `leave`, the reply kept by `hear` in `gauntlet/mend/<slug>.reply.<n>.txt` (holding `retry` for a retry, which resets the stall count); on `gauntlet-run`'s id, `show`'s text and the one `gate` wait, form `select`, options `land` and `leave` | any other wait or agent in `mend/` or `land/`; a diff shown at `ask`; the gate showing anything but the test line, the plan and revision summaries, the diff stat and the commit messages |
| Which tree records reach the checkout | `record`'s five patterns | any other tree file copied, `gauntlet/mend/`, `gauntlet/tasks/` and `gauntlet/baseline/` included; a copy that overwrites a differing file |
| A stop in the mend or landing | a failed node with the tree kept, resumed by `archon workflow resume <gauntlet-run id>` | stashing, resetting or discarding the owner's edits; cancelling the run; removing the tree on any stop; a red ending the run outside the owner's `leave` |

## Order

1. Red in the mend: `mend/scripts/verify.py`, `mend/tests/test_verify.py`. Needs `gauntlet-design.md`'s step 8. Agent: `builder`.
2. The mend's roles: `mend/commands/mend-juror.md`, `mend/commands/mend-code.md`, `mend/commands/mend-tests.md`, `mend/commands/mend-review.md`. Agent: `role-author`.
3. Mend block: `mend/mend.yaml`, `mend/mend-juror.mcp.json`, `mend/mend-code.mcp.json`, `mend/mend-tests.mcp.json`, `mend/mend-review.mcp.json`, `mend/fixtures/still.stubs.yaml`, `mend/fixtures/moved.stubs.yaml`, `mend/fixtures/head-red.stubs.yaml`, `mend/fixtures/repair.stubs.yaml`, `mend/fixtures/repair-tests.stubs.yaml`, `mend/fixtures/repair-unsound.stubs.yaml`, `mend/fixtures/repair-reply.stubs.yaml`, `mend/fixtures/repair-stall.stubs.yaml`, `mend/fixtures/repair-leave.stubs.yaml`, `mend/fixtures/conflict.stubs.yaml`. Needs steps 1 and 2 and writing's `write-code/coder.mcp.json` and `write-tests/test-writer.mcp.json`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
4. Landing block: `land/land.yaml`, `land/fixtures/land.stubs.yaml`, `land/fixtures/leave.stubs.yaml`, `land/fixtures/moved.stubs.yaml`, `land/fixtures/refused.stubs.yaml`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.

`gauntlet-tree`'s node `mend` and its `handoff`'s `outcome` and `line` need step 3; `gauntlet-design.md`'s step 11 needs step 4.

## Decisions for the owner

1. The checkout moves after the mend has rebased the branch, before the merge, so the branch no longer fast-forwards. Recommend: landing stops at `onto` or `merge`, the tree, branch and any land answer kept, and `archon workflow resume <run id>` lands once the checkout is back at an ancestor of the branch; cost: the owner moves the new checkout commits aside by hand, and no test reruns on them. Alternative: landing hands off `left` with the tree kept and the owner lands by hand; cost: the run ends with no Gauntlet landing, and the record copy and tree removal fall to the owner.
