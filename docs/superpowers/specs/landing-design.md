Status: proposed.

# Gauntlet landing

## Why

Landing is two blocks and one run. Block `mend`, `mend/mend.yaml`, runs in the tree as part of the tree run `gauntlet-tree`, after `write`, when writing hands off `written`, and again in the re-mend run `gauntlet-remend`, `gauntlet-remend/gauntlet-remend.yaml`, the child run of block `land`'s node `retree`. Block `land`, `land/land.yaml`, is phase 7 of `gauntlet-run`, after `cut`, when the tree run hands off `ready`; `gauntlet-run` includes it four times, under the ids `land`, `land-2`, `land-3` and `land-4`, one round each. `gauntlet-design.md` gives the fast-forward merge as the only write to the checkout's tracked files, the record copy, the removal of every tree landing made by `archon complete <branch> --force`, and `.shared/red.py`. This file gives both blocks' nodes and signatures. Every path is relative to the pack root unless it names the checkout or the tree.

By the end of writing the checkout may have moved past base and may hold uncommitted edits. Block `mend` reads the checkout's `HEAD`, rebases the tree's branch onto it, verifies the rebased tree only when the checkout has moved (or a first pass already started rebasing the branch, so a resume reruns it), and mends a red on the rebased tree: a juror rules each red a code mend, a test mend or defective, the mender it names commits the mend, and a reviewer reads every mend. The owner is asked on the id of the run the mend executes in, in plain words and with no diff, only when the juror rules defective or the mend stalls, and answers with guidance, a rerun or leave. It runs git, the brief test command, one script and, only in the repair, four agents. Block `land` checks that the branch still fast-forwards the checkout. When the checkout has moved past it, the round pins a second branch at the tree's tip, starts the re-mend run in a second tree cut on it, and so re-mends at most twice, whatever the timing of the moves: a round's `onto` re-mends while `made` holds fewer than two branches, and a move that would need a third re-mend fails `onto`, naming the move. The re-mend run repeats only block `mend`, in a second tree; no `gauntlet-run` node goes back. The round then shows the owner the test line, the diff stat and the commit messages, waits for land or leave, and on land fast-forwards the checkout, copies the records and removes every tree it made. A checkout that moves while the gate waits sends the run to the next round, which checks it again and asks again; in the last round, `land-4`, `merge` stops the run instead, naming the move. Landing itself runs git, Archon's CLI and one script, and no agent; the agents of a re-mend run in the re-mend run.

An agent runs in its run's checkout, and no node field sets another folder; `fence/files.py` and `fence/checks.py` root at `CLAUDE_PROJECT_DIR`, the agent's folder. The tree run and the re-mend run are the only runs whose checkout is a tree, each its own, so every agent that writes in a tree, the mend's four included, runs in one of them. The re-mend run works in a second tree, never in the tree of the run that came before it: Archon cuts it, on a branch pinned at that tree's tip.

What the designs hold for the concerns landing touches:

- Running a test command from a bash node: 2 designed copies of one invocation, `timeout -k 10 <timeout> nice -n 10 bash -c <brief> < /dev/null` in the tree's root, `brief` and `timeout` read from the tree's `gauntlet/settings.json`, writing `exit=<n> timed_out=<true|false>` then the output: node `baseline` of the tree run (worktree cut design), and node `test` of writing. The mend's three test nodes make 5. `fence/checks.py` runs a test command for agents only, as an MCP tool, so no bash node can call it. Named scripts resolve only from a workflow's own `scripts/`, and the repository's `env:` is measured to reach bash nodes only, so no shared runner can hold the invocation. Its one home is node `baseline`'s invocation and file format, which every other node uses verbatim.
- Red against the brief baseline: 1 home, `.shared/red.py` (`gauntlet-design.md`). The mend calls it through `mend/scripts/verify.py` and parses no listing.
- Copying a file only when absent or identical: 3 designed copies of one rule, node `copy-in` of the tree run (worktree cut design), node `copy-in` of the re-mend run (the previous tree's `gauntlet/` into the new tree, the first mend's `gauntlet/mend/<slug>.verdict.*`, `.review.*`, `.reply.*`, `.grounds.*`, `.changes.*`, `.mended.*` and `.rebased.*` files excepted) and landing's `record`, which applies the rule in the other direction, tree to checkout.
- Rebase, fast-forward and branch removal: no copy. No other Gauntlet file rebases, merges or removes a branch.
- Creating a branch at a tree's tip for Archon to cut a tree on: 1 home, `.shared/pin.py` (worktree cut design), called by `gauntlet-run/scripts/pin.py` for the first tree and by `land/scripts/pin.py` for each second tree.
- Fences for an agent writing code or tests: 2 designed copies, `write-code/coder.mcp.json` and `write-tests/test-writer.mcp.json` (writing design), both rooted at the agent's own working folder, the tree. The mend's two writers take their settings verbatim, plus read access to `gauntlet/mend`.
- Ruling on a red: 1 designed juror, `write/commands/juror.md` (writing design), with verdicts `TESTS`, `CODE`, `SPEC`, `PLAN` and `DEFECTIVE` over writing's cases. The mend's juror, `mend/commands/mend-juror.md`, rules only a red on the rebased tree, with verdicts `CODE`, `TESTS` and `DEFECTIVE`, and revises no plan or spec.
- Asking the owner on a stall: 1 designed copy, writing's `stalled` case (5 verdicts and rejected cuts since the latest writing ruling) answered at `bench`. The mend asks on the same count, with no cuts in the mend, on the id of the run the mend executes in.
- Reading the checkout from a tree: no copy. The checkout root (the tree run's `task` input without its trailing `/gauntlet/tasks/<slug>.md`, worktree cut design; the re-mend run's `checkout` input) is read by node `copy-in` of the tree run for files; the mend's `onto` is the only node reading the checkout's `HEAD` from a tree, and `land`'s `onto` the only one in `gauntlet-run`.

Measured in Archon's reference: a wait cannot carry `always_run`, so a resumed run replays the owner's answer and never asks again; `always_run: true` reruns a node on resume while other completed nodes replay, and the reference excludes it from no `loop_group`; `archon complete --force` removes a worktree whose commits are on no remote, which `archon isolation cleanup` keeps. A `loop_group` whose body ends in an attention wait as its sole terminal sink asks at most once per iteration, may skip the ask by its `when:`, in which case `until_bash` must read the work and not the skipped wait, hands the answer to the next iteration as `$LOOP_PREV.<wait>.output`, and lets each accepted answer run one iteration past `max_iterations`; a failure resume restarts the group at iteration 1; `$group.output` is the output of the nodes the wait depends on; a `select` wait answers `{ decision, text }` and may take its options from an upstream output. An `include:` expands at load time into ordinary nodes of the containing scope, ids `<includeId>__<id>` (`workflow-language.md:1588-1596`), and only a `workflow:` node in a `loop_group` body is rejected (`:1732-1733`, `:2543-2544`), so a `workflow:` node of an included block outside a loop is a documented form; includes nest 3 deep (`:1735`), and `gauntlet-run` nests one. A `workflow:` node with `isolation: worktree` gets the branch `archon/task-<parentRunId8>-<nodeId>-<hash>-child-<n>` (`:2105`), and a local branch of that name is reused (worktree cut design, "Branch reuse"). Unmeasured: whether a resumed `tree` node of `gauntlet-run` resumes its child run's completed nodes or runs them anew; the mend's `always_run` nodes rerun either way. Unmeasured: whether the node id Archon hashes into a branch name for a `workflow:` node inside an included block is the expanded id `<includeId>__<id>` (`land__retree`); the re-mend run's `branch-check` fails the run naming both branches when it is not.

## Modules

### `mend/mend.yaml` (the mend: rebase, verify, repair)

Included by `gauntlet-tree`, as node `mend` after `write`, when `$write.output.outcome == 'written'`, with `slug`, `checkout`, `branch` and `brief` from its node `paths`, and by `gauntlet-remend`, as node `mend`, with `slug` and `checkout` from the run's inputs, `branch` the second branch and `brief` from its node `paths`. The tree run's `handoff` prints the mend's `outcome` in place of writing's when the mend ran, and its `line`; the re-mend run's `handoff` prints the mend's `outcome` and `line`. It runs in a tree: every path it reads or writes is in that tree, and it reads the checkout only by `git -C $INPUTS.checkout rev-parse HEAD`. Nodes `onto`, `rebase`, `test-tree`, `red`, `test-head`, `confirm` and the group `repair` carry `always_run: true`, so a resume rebases, verifies and mends against the checkout as it then stands. Test-run files sit in `gauntlet/mend/`, keyed by the commits they ran on, so a rerun on the same commits reuses its file. Its waits are answered on the id of the run the mend executes in, the tree run's or the re-mend run's.

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
  - id: onto                           # the checkout's HEAD as the mend finds it
    always_run: true
    bash: <head = git -C $INPUTS.checkout rev-parse HEAD. tip = git rev-parse $INPUTS.branch.
          moved = not (git merge-base --is-ancestor head tip), or the file gauntlet/mend/$INPUTS.slug.rebased.<head> exists
          (a first pass already started rebasing the branch onto this head, so a resume still reruns the tests). print { head, moved }>
    output_format: <object: head (string), moved (boolean), all required>

  - id: rebase                         # the only rebase in Gauntlet
    depends_on: [onto]
    always_run: true
    bash: <head not an ancestor of $INPUTS.branch (git merge-base --is-ancestor fails): first write
          gauntlet/mend/$INPUTS.slug.rebased.<head> by cp -n semantics, so a conflict leaves it. Then
          git rebase $onto.output.head $INPUTS.branch; already based on head: git does nothing.
          Any refusal or conflict: leave the rebase as git stops it, print git's output and
          "Resolve it in <tree> (git rebase --continue), then archon workflow resume <gauntlet-run id>.", exit 1>

  - id: test-tree                      # the rebased tree, when the checkout moved or a first pass rebased it
    depends_on: [rebase]
    when: "$onto.output.moved == true"
    always_run: true
    bash: <git checkout $INPUTS.branch.
          file = gauntlet/mend/$INPUTS.slug.run.<head>.<tip>.txt, tip the branch's commit now.
          file absent: run the brief command in the tree's root as node baseline runs it, "brief" and "timeout" read
          from the tree's gauntlet/settings.json, written in its format. print { file } as an absolute tree path>
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
          git checkout --detach $onto.output.head, run the brief command as test-tree
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

        - id: changes                  # the branch past the checkout's HEAD, for the juror; not on a leave or a retry
          depends_on: [hear]
          when: "$hear.output.left == false && $hear.output.retry == false"
          bash: <git -C <tree> log -p $onto.output.head..$INPUTS.branch, <tree> the tree's root, into
                gauntlet/mend/$INPUTS.slug.changes.$hear.output.n.txt, over any earlier file of that n (no verdict read it,
                or n would be higher). print { file } as an absolute tree path>
          output_format: <object: file (string), required>

        - id: juror                    # rules every red in the repair, but a retry; the owner never picks a mender
          depends_on: [changes]
          when: "$hear.output.left == false && $hear.output.retry == false"
          command: mend-juror
          context: fresh
          allowed_tools: []
          mcp: mend-juror.mcp.json
          prompt: <verdict file gauntlet/mend/$INPUTS.slug.verdict.$hear.output.n.txt; the case: $LOOP_PREV.pose.output.case,
                  or $test-tree.output.file when empty; $test-head.output.file; every gauntlet/mend/$INPUTS.slug.verdict.*,
                  .review.* and .reply.* file in order of n; the changes file $changes.output.file;
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

        - id: mended                   # the branch past the checkout's HEAD, for the reviewer; also the record that a mend was committed
          depends_on: [recheck]
          bash: <A retry whose recheck is red, or a retry with no gauntlet/mend/$INPUTS.slug.mended.*.txt file (the repair
                has committed no mend): print { "file": "" }. Else, after a committed mend or after a retry not red that
                follows one (a SOUND review of the latest committed mend ends the repair, so after a retry that mend has
                none): git -C <tree> log -p $onto.output.head..$INPUTS.branch, <tree> the tree's root, into
                gauntlet/mend/$INPUTS.slug.mended.$hear.output.n.txt, over any earlier file of that n.
                print { file } as an absolute tree path>
          output_format: <object: file (string), required>

        - id: review                   # every committed mend read before it can end the repair, after a retry too; never on a red recheck
          depends_on: [mended]
          when: "$recheck.output.red == false && $mended.output.file != ''"
          command: mend-review
          context: fresh
          allowed_tools: []
          mcp: mend-review.mcp.json
          prompt: <review file gauntlet/mend/$INPUTS.slug.review.$hear.output.n.txt; the latest verdict file
                  gauntlet/mend/$INPUTS.slug.verdict.<n>.txt; the run files $retest.output.file and $test-head.output.file;
                  recheck's red; the mender's outcome and grounds when this iteration ran a mender, or "retry" when it did not;
                  the mended file $mended.output.file; the approved plan and spec with their revisions in order of N>
          output_format: <object: verdict (SOUND | UNSOUND), file (string), all required>

        - id: pose                     # whether the repair ends, the next case, and whether to ask the owner
          depends_on: [hear, juror, review]
          trigger_rule: none_failed_min_one_success
          bash: <First that holds. hear left: end "left". A committed mend, recheck not red and review SOUND: end "done". A
                retry whose rerun is not red, with no uncommitted mend (git status --porcelain empty, gauntlet/ excluded),
                and review SOUND or not run (no committed mend awaits one): end "done". Else end "", and case =
                newline-separated tree paths the next juror reads: the latest run file and the latest review file it holds, each when there is one, and the mender's grounds written by cp -n to
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
          "Rerun on $onto.output.head: no new failure."; repair ran with a committed mend (a gauntlet/mend/$INPUTS.slug.mended.*.txt file
          exists): "Mended on $onto.output.head: no new failure."; repair ran with no committed mend (no such file; the
          branch tip is the rebased tip test-tree ran on): "Rerun on
          $onto.output.head after retry: no new failure.">
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [ready, left] }
        line: { type: string }
      required: [outcome, line]
```

Every stop is a failed node: a rebase conflict or a failed repair node. It fails the tree run and so `gauntlet-run`'s node `tree` (in a re-mend, the re-mend run and so the round's node `retree`, and `archon workflow resume <gauntlet-run id>` re-drives that child); the tree, its branch and any rebase in progress stay, and `archon workflow resume <gauntlet-run id>` picks the run up there; a resumed `repair` starts at iteration 1, its verdict, review, reply, changes and mended files kept. A red on the rebased tree is no stop: it opens `repair`. The repair ends when a mend is committed, the branch is not red and the latest review is SOUND, when the owner's retry reruns the tests green with nothing uncommitted and the latest committed mend, when there is one, has a SOUND review (a retry after a committed mend runs `review` once more), or on the owner's `leave`, which hands off `left` with the tree kept; `gauntlet-run` then ends with no landing. An uncommitted mend (a commit-failed mender) never ends the repair: the juror sees it as the next case. The owner never picks a mender and is never shown a diff in the repair. Mend commits sit on top of the branch's last commit; the mend never resets, amends or drops a commit, never aborts a rebase and never writes in the checkout.

Fixtures, `mend/fixtures/<route>.stubs.yaml`, one per route: `still` (`moved` false, `test-tree` not reached, `ready`); `moved` (`red` false, `test-head` not reached, `ready`); `resumed` (`moved` true on a rebased marker, `test-tree` reached); `head-red` (`red` true, `confirm` not red, `repair` not reached, `ready`); `repair` (`confirm` red; `juror` CODE, `mend-code` committed, `recheck` not red, `review` SOUND, `ask` not reached; `ready`); `repair-tests` (`juror` TESTS, `mend-tests` committed, not red, SOUND; `ready`); `repair-unsound` (`juror` CODE, `review` UNSOUND; iteration 2 `juror` CODE, SOUND; `ready`); `repair-uncommitted` (`mend-code` commit-failed, `retest` not reached, `pose` ends "", iteration 2 `juror` sees the grounds); `repair-reply` (`juror` DEFECTIVE, `ask` answered `reply`; iteration 2 reply file written, `juror` CODE, SOUND; `ready`); `repair-retry` (`juror` DEFECTIVE, `ask` answered `retry`; iteration 2 reply file holds `retry`, `changes`, `juror` and menders not reached, `retest` green, `mended` prints "", `review` not reached, `ready`); `repair-retry-review` (`mend-code` committed, `recheck` red, `review` not reached; iteration 2 `juror` DEFECTIVE, `ask` answered `retry`; iteration 3 `retest` green, `mended` writes its file, `review` SOUND, `ready`); `repair-stall` (5 verdicts with no end, `ask` reached); `repair-leave` (`juror` DEFECTIVE, `leave` at `ask`, `left`); `conflict` (`rebase` fails, its rebased marker written, `handoff` not reached).

### `land/land.yaml` (landing in the checkout)

Included by `gauntlet-run` only, four times, one round each: as node `land` after `cut`, when the tree run hands off `ready`, and as nodes `land-2`, `land-3` and `land-4`, each after the round before it, when that round hands off `moved`. A round takes `slug` from node `pin`; `round` its own include id; `worktree`, `branch` and `line` from the cut (`land`) or the round before; `summary` from the cut; and `made` from the round before. It runs in the checkout, reaches a tree only by `git -C <worktree>`, `archon complete` and, for the re-mend, a `workflow:` node, and writes nothing in a tree. It has no agent node. `onto` carries `always_run: true`, so a resume checks the checkout as it then stands; `show` and `gate` replay.

```yaml
name: land
description: >-
  Gauntlet landing, included by gauntlet-run only. Not for direct use.
inputs:
  slug: { description: The task's slug. }
  round: { description: "The id of the include node that runs this round: land, land-2, land-3 or land-4." }
  worktree: { description: Absolute path of the tree this round lands. }
  branch: { description: The branch of that tree. }
  line: { description: The mend's test line for that tree. }
  summary: { description: The plan summary and the approved revision summaries, shown at the gate. }
  made: { default: "", description: "The branches of the trees earlier rounds left behind, one per line. Landing removes them with the landed tree." }
returns: handoff

nodes:
  - id: onto                           # the checkout as the round finds it
    always_run: true
    bash: <checkout = git rev-parse --show-toplevel. head = git rev-parse HEAD in the checkout. tip = git rev-parse $INPUTS.branch
          in the checkout, where every tree's branch is visible, so no tree folder is read; "" when the branch is absent. moved = false when tip is "", or git merge-base
          --is-ancestor tip head (landed), or git merge-base --is-ancestor head tip (fast-forwards); else true.
          moved and $INPUTS.made holds two branches (landing has re-mended twice): print "The checkout moved to <head>
          again after landing re-mended twice; $INPUTS.branch no longer fast-forwards it. Bring the checkout back to an
          ancestor of $INPUTS.branch, then archon workflow resume <run id>.", exit 1. Else print { head, moved, checkout }>
    output_format: <object: head (string), moved (boolean), checkout (string), all required>

  - id: repin                          # the branch the second tree is cut on, only when the checkout moved
    depends_on: [onto]
    when: "$onto.output.moved == true"
    runtime: uv
    script: pin                        # land/scripts/pin.py
    output_format: <object: branch (string), required>

  - id: retree                         # the re-mend run, in a second tree: block mend only, then back here
    depends_on: [onto, repin]
    workflow: gauntlet-remend
    isolation: worktree
    with: { slug: $INPUTS.slug, branch: $repin.output.branch, from: $INPUTS.worktree, checkout: $onto.output.checkout }

  - id: cur                            # the tree this round lands
    depends_on: [onto, retree]
    trigger_rule: none_failed_min_one_success
    runtime: bun
    script: <print { outcome, worktree, branch, line, made }. retree ran (its output is not ""): outcome, worktree, branch and
            line from it, made the input made with the input branch added as its last line. Else outcome "ready" and the
            inputs, read as INPUTS_WORKTREE, INPUTS_BRANCH, INPUTS_LINE and INPUTS_MADE>
    with: { retree: { from: $retree.output, if_skipped: "" } }
    output_format: <object: outcome (enum ready, left), worktree, branch, line, made (strings), all required>

  - id: show                           # what the owner reads at the gate
    depends_on: [onto, cur]
    when: "$cur.output.outcome == 'ready'"
    bash: <print: "Land $INPUTS.slug: fast-forward the checkout from $onto.output.head to $cur.output.branch?";
          $cur.output.line; $INPUTS.summary; then git -C $cur.output.worktree diff --stat $onto.output.head $cur.output.branch,
          then git -C $cur.output.worktree log --reverse --format='%h%n%B' $onto.output.head..$cur.output.branch>

  - id: gate                           # the owner's land or leave, answered on gauntlet-run's id, once per round that reaches it
    depends_on: [show]
    wait:
      form: select
      attention: "$show.output"
      options: [ { id: land, label: Land }, { id: leave, label: Leave } ]

  - id: merge                          # the only write to the checkout's tracked files
    depends_on: [onto, cur, gate]
    when: "$gate.output.decision == 'land'"
    bash: <now = git rev-parse HEAD in the checkout. Moved: git merge-base --is-ancestor now $cur.output.branch fails and
          git merge-base --is-ancestor $cur.output.branch now fails (the branch no longer fast-forwards the checkout and is
          not in it). Moved in round land-4 ($INPUTS.round): print "The checkout moved from <onto> to <now> while the last
          round of landing waited; $cur.output.branch no longer fast-forwards it. Bring the checkout back to an ancestor of
          $cur.output.branch, then archon workflow resume <run id>.", exit 1, writing nothing. Moved in any other round:
          print on stderr "The checkout moved from <onto> to <now> while landing waited; the next round checks it and asks
          again.", print { "result": "moved" }, exit 0, writing nothing. Else git merge --ff-only $cur.output.branch. git
          refusing: git status --porcelain=v2 --branch in the checkout. Its branch.oid differs from now (HEAD moved after
          the check, so the refusal is no edit of the owner's): repeat this node's steps from the start with now that HEAD.
          Else (uncommitted edits in the files it would change, or untracked files in its way): print git's output and
          "Stash those edits (git stash --include-untracked), then archon workflow resume <run id>.", exit 1.
          Merged: print { "result": "merged" }>
    output_format: <object: result (enum merged, moved), required>

  - id: record                         # the only writer of tree records in the checkout
    depends_on: [cur, merge]
    when: "$merge.output.result == 'merged'"
    bash: <for each file of the tree $cur.output.worktree among gauntlet/plans/approved/$INPUTS.slug.rev*.txt,
          gauntlet/specs/approved/$INPUTS.slug.rev*.txt, gauntlet/write/$INPUTS.slug.*, gauntlet/revisions/$INPUTS.slug.* and
          gauntlet/revisions/$INPUTS.slug-summary.*: target the same path in the checkout. Absent: cp -n. Identical (cmp):
          nothing. Differing: exit 1 naming both paths, nothing more copied>

  - id: remove                         # every tree this landing made
    depends_on: [cur, record]
    bash: <for each branch in $cur.output.made, then $cur.output.branch: branch absent: nothing. Else
          archon complete <branch> --force, its failure exiting non-zero with its output>

  - id: handoff
    depends_on: [cur, gate, merge, remove]
    trigger_rule: none_failed_min_one_success
    runtime: bun
    script: <print { outcome, worktree, branch, line, made } with the last four from cur. outcome: "left" when cur's outcome is
            left or gate's decision is leave; "moved" when merge's result is moved; "landed" when merge's result is merged>
    with: { cur: $cur.output, gate: { from: $gate.output.decision, if_skipped: "" },
            merge: { from: $merge.output.result, if_skipped: "" } }
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

Landing re-mends at most twice, whatever the timing of the moves, in four rounds. A round whose `onto` finds the checkout past the branch (the branch neither contains the checkout's `HEAD` nor is contained by it) re-mends before it asks, while `made` holds fewer than two branches: `repin` creates the second branch at the tree's tip, `retree` starts `gauntlet-remend` on it, in a second tree, and the round lands that tree's branch, which `cur` adds to `made`. With two branches in `made`, such a move fails `onto`, naming it. A checkout that moves while the gate waits is no stop in the first three rounds: `merge` writes nothing, the round hands off `moved`, and the next round checks the checkout again, re-mends if the branch no longer fast-forwards it, and asks the owner again; the answer `land` of the round before does not stand. `merge` counts a move only when the checkout's `HEAD` is no longer an ancestor of the branch, in every round, so a checkout `HEAD` the branch still fast-forwards lands. In `land-4` such a move fails `merge`, naming it. Two re-mends therefore hold however the moves fall, and no move ends the run unlanded and unnamed. When the re-mend run's mend ends on the owner's `leave`, `cur` hands off `left` and the run ends with every tree kept.

Every stop is a failed node: a move that would need a third re-mend (`onto`), a move found by `merge` in `land-4`, a failed re-mend run (`retree`), a merge git refuses over the owner's uncommitted edits (the owner stashes them; a commit would move `HEAD`, and the resumed `merge` would count a move), a differing record or a failed removal. Every tree and branch stays, and `archon workflow resume <run id>` picks the run up there. Landing never resets, amends or drops a commit, never stashes, resets or discards the owner's edits, and never cancels the run; the rebase belongs to the mend, in a tree. Unrelated uncommitted files in the checkout stay as they are. A resume after `merge` finds the branch an ancestor of the checkout, so `onto` passes and `merge` replays.

Fixtures, `land/fixtures/<route>.stubs.yaml`, one per route: `land` (`onto` not moved, `repin` not reached, land, `landed`); `leave` (`merge` not reached, `left`); `moved` (`onto` moved, `repin` and `retree` reached, land, `landed`); `moved-left` (`retree` hands off `left`, `show` not reached, `left`); `waited` (`merge` prints `moved`, `record` not reached, `moved`); `third` (`made` holds two branches, `onto` moved, `onto` fails, `repin` not reached); `gate-moved-last` (round `land-4`, the checkout's `HEAD` no longer an ancestor of the branch at `merge`, `merge` fails naming the move, `record` not reached); `refused` (`merge` fails on uncommitted edits with the stash advice, `record` not reached).

### `land/scripts/pin.py` (the second tree's branch)

Node `repin`: the branch Archon will name for the round's node `retree`, created at the tree's tip before Archon cuts the second tree. Runs in the checkout. Imports `pin` from `.shared/pin.py` (worktree cut design) as the planning ledger imports `.shared/rounds.py`; standard library only. Replaces nothing.

```python
# /// script
# requires-python = ">=3.12"
# ///
# Environment: WORKFLOW_ID (set by Archon), INPUTS_ROUND (the round's include id), INPUTS_BRANCH (the tree's branch).
# node id = INPUTS_ROUND + "__retree", the id the include expands node retree to; source = INPUTS_BRANCH.
# stdout { "branch": str }: the branch .shared/pin.py names for that node id, created at the tip of INPUTS_BRANCH
#   (left as it is when present).
# INPUTS_BRANCH absent from the repository: stderr names it; exit 2.
def main() -> int: ...
```

Suite: `land/tests/test_pin.py`, run as `docs/testing.md` states with the folder `land/tests`. It drives `main` against a real git repository under `tmp_path`. It pins: the branch `archon/task-72773a16-land-retree-797b5dc7-child-0` for round `land` and `archon/task-72773a16-land-2-retree-bf269529-child-0` for `land-2`, a `WORKFLOW_ID` starting `72773a16`; the new branch created at the tip of `INPUTS_BRANCH`, not at `HEAD`; an existing branch left where it is; exit 2 for an absent `INPUTS_BRANCH`.

### `gauntlet-remend/gauntlet-remend.yaml` (the re-mend run)

The child run in a second tree, started only by node `retree` of block `land`. Archon cuts the tree on the branch `repin` created, and runs the repository's `worktree.copyFiles` and `worktree.postCreate` before its first node. The tree holds the previous tree's commits and none of its ignored `gauntlet/`, so `copy-in` brings that over, all but the previous mend's verdict, review, reply, grounds, changes, mended and rebased-marker files, so the re-mend numbers its own files from 1, its juror and reviewer read none of the superseded ones, and no earlier mend counts as committed in its repair. It runs block `mend` and nothing else; every agent it holds is the mend's. Its pauses are answered on its own id, which `archon workflow get <gauntlet-run id> --json` gives at `.metadata.approval.childRunId`. Replaces nothing.

```yaml
name: gauntlet-remend
description: >-
  Gauntlet's re-mend run, started only by block land's node retree. Copies the previous tree's gauntlet/ into its own
  tree and runs block mend there. Never started by hand.
inputs:
  slug: { description: The task's slug. }
  branch: { description: The branch node repin of block land created at the previous tree's tip. }
  from: { description: Absolute path of the previous tree. }
  checkout: { description: Absolute path of the owner's checkout. }
returns: handoff

nodes:
  - id: guard
    runtime: bun
    script: guard                      # gauntlet-remend/scripts/guard.ts, the two lines of gauntlet-tree's

  - id: branch-check                   # the tree is on the branch repin created; fails before anything is copied
    depends_on: [guard]
    bash: <git branch --show-current differs from $INPUTS.branch: exit non-zero naming both>

  - id: copy-in                        # the only writer of this tree's gauntlet/
    depends_on: [guard, branch-check]
    bash: <$INPUTS.from/gauntlet absent: exit non-zero naming it. Every file under it, gauntlet/settings.json included, but
          gauntlet/mend/$INPUTS.slug.verdict.*, .review.*, .reply.*, .grounds.*, .changes.*, .mended.* and .rebased.*, to the same path under this
          tree: absent: cp -n; identical (cmp): nothing; differing: exit non-zero naming both paths, nothing more copied>

  - id: paths
    depends_on: [copy-in]
    runtime: bun
    script: <print { worktree, brief }: worktree the tree's absolute root, brief its gauntlet/baseline/<slug>.brief.txt, slug
            read as INPUTS_SLUG>
    output_format: <object: worktree, brief (strings), all required>

  - id: mend
    depends_on: [paths]
    include: mend
    with: { slug: $INPUTS.slug, checkout: $INPUTS.checkout, branch: $INPUTS.branch, brief: $paths.output.brief }

  - id: handoff
    depends_on: [paths, mend]
    runtime: bun
    script: <print { worktree, branch, outcome, line }: worktree from $paths.output, branch from git branch --show-current,
            outcome and line from $mend.output>
    output_format: <object: worktree, branch, outcome, line (strings), all required; outcome enum ready, left>
```

Fixtures, `gauntlet-remend/fixtures/<route>.stubs.yaml`, one per route: `remend` (`handoff` reached, `ready`); `left` (the mend hands off `left`); `conflict` (`copy-in` fails, `mend` not reached); `branch` (`branch-check` fails, `copy-in` not reached).

`gauntlet-remend/scripts/guard.ts` is `gauntlet-tree/scripts/guard.ts`'s two lines, the shared working-folder check, run in the second tree.

### `mend/commands/mend-juror.md`, `mend/commands/mend-code.md`, `mend/commands/mend-tests.md`, `mend/commands/mend-review.md` (the mend's roles)

The four agents of the mend. Each starts a fresh session, primed from files. Replaces nothing.

```markdown
mend-juror
Inputs: the verdict file to write, the case files, the head file, every earlier verdict, review and owner reply of
this mend, the changes file (the log and patches of the branch past the checkout's HEAD), the approved plan and spec
with their revisions.
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
Inputs: the review file to write, the latest verdict file, the run files, recheck's red, the mender's outcome and
grounds or the word retry, the mended file (the log and patches of the branch past the checkout's HEAD), the approved
plan and spec with their revisions.
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
| Where each landing node runs | block `mend`, included by `gauntlet-tree` after `write` and by `gauntlet-remend`, for the read of the checkout's `HEAD`, the rebase, every test run and every agent, each in its run's own tree; block `land`, included by `gauntlet-run` after `cut` under the ids `land`, `land-2`, `land-3` and `land-4`, for the check, the second branch, the re-mend run's start, the gate, the merge, the record copy and the removal | an agent node in `land/`; a rebase or test run in `land/`; any `land/` node writing in a tree; a `mend/` node writing in the checkout |
| The commit the mend rebases onto | `mend`'s node `onto`'s `head`, by `git -C $INPUTS.checkout rev-parse HEAD`, read by `rebase`, the test nodes, `repair` and `handoff` | any other tree-run or re-mend-run node reading the checkout's `HEAD` |
| Re-mending when the checkout moved | block `land`'s nodes `onto` (the check), `repin`, `retree` and `cur`, at most twice in all, in any round whose `onto` finds fewer than two branches in `made`; `gauntlet-remend` running block `mend` only, in a second tree | a re-mend by any other node; a third re-mend; a re-mend in the tree of the run before it; a rebase, test run or agent in `land/` |
| The second tree's branch | `land/scripts/pin.py` over `.shared/pin.py`, creating the branch Archon will name for node `<round>__retree` at the tip of the tree's branch | any other node or script composing that name or creating that branch |
| What the second tree holds | node `copy-in` of `gauntlet-remend`, the previous tree's `gauntlet/` by `cp -n` semantics, `settings.json` included, but `gauntlet/mend/<slug>.verdict.*`, `.review.*`, `.reply.*`, `.grounds.*`, `.changes.*`, `.mended.*` and `.rebased.*` | an agent or other node writing the second tree's `gauntlet/` before `mend`; a differing file overwritten |
| The commit landing lands against | `land`'s node `onto`'s `head`, read by `show` and `merge` | any other `land/` node reading the checkout's `HEAD`, `merge`'s ancestry check excepted |
| Rebasing the tree's branch | `mend`'s node `rebase`, `git rebase <head> <branch>` in the tree | any other rebase, reset, amend, squash or history rewrite in a Gauntlet file; a rebase in the checkout; a rebase aborted by Gauntlet |
| Whether the mend reruns tests | `onto`'s `moved` for `test-tree`; `red`'s answer for `test-head`; a committed mend or a retry for `retest` | a retest with no committed mend and no retry; a test run when the checkout's `HEAD` is in the branch's history, except after a first pass's rebase, marked by `gauntlet/mend/<slug>.rebased.<head>`; a head run when the rebased tree is not red without it; a test run in the checkout |
| The mend's test runs | `test-tree`, `test-head` and `retest`, as node `baseline` runs its command, with no node `timeout:`, into `gauntlet/mend/<slug>.run.<head>.<tip>.txt` and `gauntlet/mend/<slug>.head.<head>.txt` of the tree | any other file name or folder; another invocation of the brief command in `mend/` or `land/` |
| Red in the mend | `mend/scripts/verify.py` over `.shared/red.py`; a red with the head check opens `repair` | a comparison or listing in a `mend/` or `land/` node; a red shown at the gate; a red stopping the run |
| Mending a red on the rebased tree | group `repair` of block `mend`: `mend-juror` rules every red, UNSOUND review and uncommitted mend into `gauntlet/mend/<slug>.verdict.<n>.txt`; its verdict runs one mender, `mend-code` fenced out of `tests/` and `gauntlet/`, `mend-tests` fenced to `tests/` and the test base; `mend-review` reviews every mend into `gauntlet/mend/<slug>.review.<n>.txt`; `pose` ends the repair only on a committed mend, not red and SOUND, or on a retry rerun that is not red with nothing uncommitted and the latest committed mend, when there is one, reviewed SOUND | the owner picking a mender; a mender run without a juror verdict; one agent writing both code and tests; a mend that ends unreviewed; a mend in the checkout; any other agent writing in the tree after writing |
| What the juror and reviewer read of the branch | group `repair`'s node `changes`, after `hear`, into `gauntlet/mend/<slug>.changes.<n>.txt` for `juror`, and node `mended`, after `recheck`, into `gauntlet/mend/<slug>.mended.<n>.txt` for `review`, each `git -C <tree> log -p <head>..<branch>`; a `mended` file also records that the repair committed a mend | a git tool or command given to a mend agent; any other writer of those files; a log of the branch's whole history |
| The test line at the gate | `mend`'s `handoff` `line`, carried by the tree run's `handoff` and `cut` to `land`'s input `line`, or by the re-mend run's `handoff` and `cur` when a re-mend ran, and by a round's `handoff` to the next round's `line`; the plan and revision summaries, `write`'s `summary`, carried the same way to `land`'s input `summary` | any other node composing them |
| What the owner sees and answers | on the tree run's id, or the re-mend run's, `repair`'s `ask`, only on DEFECTIVE, 5 verdicts since the latest reply, or `hear.n >= 200`, in plain words from the verdict file, options `reply`, `retry` and `leave`, the reply kept by `hear` in `gauntlet/mend/<slug>.reply.<n>.txt` (holding `retry` for a retry, which resets the stall count); on `gauntlet-run`'s id, `show`'s text and the one `gate` wait of each round that reaches it, form `select`, options `land` and `leave` | any other wait or agent in `mend/` or `land/`; a diff shown at `ask`; the gate showing anything but the test line, the plan and revision summaries, the diff stat and the commit messages |
| Which tree records reach the checkout | `record`'s five patterns | any other tree file copied, `gauntlet/mend/`, `gauntlet/tasks/` and `gauntlet/baseline/` included; a copy that overwrites a differing file |
| Removing the trees | node `remove` of the round that lands, `archon complete <branch> --force` for each branch in `made` and then the landed branch | a removal on leave or on any stop; a tree landing made and left behind after a landing |
| A stop in the mend or landing | a failed node with every tree kept, resumed by `archon workflow resume <gauntlet-run id>`; a move that would need a third re-mend, failed by `onto`, or found by `merge` in `land-4`, naming it | stashing, resetting or discarding the owner's edits; cancelling the run; removing a tree on any stop; a red ending the run outside the owner's `leave`; a fifth round |

## Order

1. Red in the mend: `mend/scripts/verify.py`, `mend/tests/test_verify.py`. Needs `gauntlet-design.md`'s step 8. Agent: `builder`.
2. The mend's roles: `mend/commands/mend-juror.md`, `mend/commands/mend-code.md`, `mend/commands/mend-tests.md`, `mend/commands/mend-review.md`. Agent: `role-author`.
3. Mend block: `mend/mend.yaml`, `mend/mend-juror.mcp.json`, `mend/mend-code.mcp.json`, `mend/mend-tests.mcp.json`, `mend/mend-review.mcp.json`, `mend/fixtures/still.stubs.yaml`, `mend/fixtures/moved.stubs.yaml`, `mend/fixtures/resumed.stubs.yaml`, `mend/fixtures/head-red.stubs.yaml`, `mend/fixtures/repair.stubs.yaml`, `mend/fixtures/repair-tests.stubs.yaml`, `mend/fixtures/repair-unsound.stubs.yaml`, `mend/fixtures/repair-uncommitted.stubs.yaml`, `mend/fixtures/repair-reply.stubs.yaml`, `mend/fixtures/repair-retry.stubs.yaml`, `mend/fixtures/repair-retry-review.stubs.yaml`, `mend/fixtures/repair-stall.stubs.yaml`, `mend/fixtures/repair-leave.stubs.yaml`, `mend/fixtures/conflict.stubs.yaml`. Needs steps 1 and 2 and writing's `write-code/coder.mcp.json` and `write-tests/test-writer.mcp.json`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
4. The second tree's branch: `land/scripts/pin.py`, `land/tests/test_pin.py`. Needs the worktree cut design's `.shared/pin.py` (its step 1). Agent: `builder`.
5. The re-mend run: `gauntlet-remend/gauntlet-remend.yaml`, `gauntlet-remend/scripts/guard.ts`, `gauntlet-remend/fixtures/remend.stubs.yaml`, `gauntlet-remend/fixtures/left.stubs.yaml`, `gauntlet-remend/fixtures/conflict.stubs.yaml`, `gauntlet-remend/fixtures/branch.stubs.yaml`. Needs step 3 and the intake design's `.shared/working-folder.ts`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
6. Landing block: `land/land.yaml`, `land/fixtures/land.stubs.yaml`, `land/fixtures/leave.stubs.yaml`, `land/fixtures/moved.stubs.yaml`, `land/fixtures/moved-left.stubs.yaml`, `land/fixtures/waited.stubs.yaml`, `land/fixtures/third.stubs.yaml`, `land/fixtures/gate-moved-last.stubs.yaml`, `land/fixtures/refused.stubs.yaml`. Needs steps 4 and 5. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.

`gauntlet-tree`'s node `mend` and its `handoff`'s `outcome` and `line` need step 3; `gauntlet-design.md`'s step 10 needs step 6.

## Decisions for the owner

None open. Ruled (G-45, owner, 2026-11-05): when the checkout has moved past the branch's base, landing rebases the branch onto the checkout's new head, reruns the tests (and the repair when red) and then lands. Landing re-mends at most 2 times. Each round is an `include`d block of `land` under its own id (`land`, `land-2`, `land-3`) that checks the checkout, re-mends on a move (the second tree run `gauntlet-remend`, running block `mend` only, in a second tree cut on a branch pinned at the tip of the branch of the tree the round lands, the first tree's for round 1) and asks the land-or-leave gate again; a third move stops the run, naming the move. The earlier recommendation (stop and resume once the owner moves the new commits aside) and its alternative (hand off `left`) were not taken. Ruled (G-69, owner, 2026-11-05): four rounds, `land` to `land-4`, so the two re-mends hold whatever the timing of the moves; no round is passed `remend`, `onto` counts the re-mends in `made`, and a move found while `land-4`'s gate waits fails `merge` (G-68).
