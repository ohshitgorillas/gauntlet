Status: proposed.

# Gauntlet landing

## Why

Landing is two blocks and one run, and it ends in the owner. Block `mend`, `mend/mend.yaml`, runs in the tree as part of the tree run `gauntlet-tree`, after `write`, when writing hands off `written`, and again in the re-mend run `gauntlet-remend`, `gauntlet-remend/gauntlet-remend.yaml`, the child run of block `land`'s node `retree`. Block `land`, `land/land.yaml`, is phase 7 of `gauntlet-run`, after `cut`, when the tree run hands off `ready`; `gauntlet-run` includes it once per round and stage, under the ids `land`, `land-2`, `land-3` and `land-4` for stage 1 and under their stage-prefixed ids after it (`gauntlet-design.md`, "Stages"), one round each. `gauntlet-design.md` gives the fast-forward merge as the only write to the checkout's tracked files, the record copy, the removal of every tree landing made by `archon complete <branch> --force`, and `.shared/red.py`. This file gives both blocks' nodes and signatures, and is the home of the review before landing. Every path is relative to the pack root unless it names the checkout or the tree.

By the end of writing the checkout may have moved past base and may hold uncommitted edits. Block `mend` reads the checkout's `HEAD`, rebases the tree's branch onto it, verifies the rebased tree only when the checkout has moved (or a first pass already started rebasing the branch, so a resume reruns it), and then meets the owner, whatever the tree's state. Every landing, failed or clean, meets the owner first (the owner-control design, section 3): a red on the rebased tree, a mender's contest or failed commit, and a mend its reviewer finds unsound are the mend's amicus cases, and a landable tree gets the review before landing, node `final`. The amicus briefs the owner on each case, in plain words, and rules on nothing; the owner answers on the id of the run the mend executes in, with the choices discuss with the amicus, run again with a direction (the code or the tests mended, or the tests only rerun), back to planning, leave, and, when the tree is landable, land. The owner picks the mender; no agent does. The mend runs git, the brief test command, scripts and, in the repair, up to five agents (the amicus, `mend-code`, `mend-tests`, `mend-review` and `final-review`). Block `land` checks that the branch still fast-forwards the checkout. When the checkout has moved past it, the round pins a second branch at the tree's tip, starts the re-mend run in a second tree cut on it, and so re-mends within the landing rounds' bound (`runtime-model-design.md`, "Loop shape and bounds"). The re-mend run repeats only block `mend`, with its review and the owner, in a second tree; no `gauntlet-run` node goes back. The round then fast-forwards the checkout (`runtime-model-design.md`, "Commit model"), copies the records and removes every tree it made: the owner's land is the answer given at the review, so block `land` holds no wait. A checkout that moves after the review sends the run to the next round, which checks it again and re-mends; the last round stops the run instead, naming the move. Landing itself runs git, Archon's CLI and one script, and no agent; the agents of a re-mend run in the re-mend run. Back to planning ends the mend with the direction and the amicus record handed off (`gauntlet-design.md`, "Back to planning").

An agent runs in its run's checkout, and no node field sets another folder; `fence/files.py` and `fence/checks.py` root at `CLAUDE_PROJECT_DIR`, the agent's folder. The tree run and the re-mend run are the only runs whose checkout is a tree, each its own, so every agent that writes in a tree, the mend's four included, runs in one of them. The re-mend run works in a second tree, never in the tree of the run that came before it: Archon cuts it, on a branch pinned at that tree's tip.

What the designs hold for the concerns landing touches:

- Running a test command from a bash node: 2 designed copies of one invocation, `timeout -k 10 <timeout> nice -n 10 bash -c <brief> < /dev/null` in the tree's root, `brief` and `timeout` read from the tree's `gauntlet/settings.json`, writing `exit=<n> timed_out=<true|false>` then the output: node `baseline` of the tree run (worktree cut design), and node `test` of writing. The mend's three test nodes make 5. `fence/checks.py` runs a test command for agents only, as an MCP tool, so no bash node can call it. Named scripts resolve only from a workflow's own `scripts/`, and the repository's `env:` is measured to reach bash nodes only, so no shared runner can hold the invocation. Its one home is node `baseline`'s invocation and file format, which every other node uses verbatim.
- Red against the brief baseline: 1 home, `.shared/red.py` (`gauntlet-design.md`). The mend calls it through `mend/scripts/verify.py` and parses no listing.
- Copying a file only when absent or identical: 3 designed copies of one rule, node `copy-in` of the tree run (worktree cut design), node `copy-in` of the re-mend run (the previous tree's `gauntlet/` into the new tree, the first mend's `gauntlet/mend/<slug>.direction.*`, `.amicus.*`, `.final.*`, `.review.*`, `.reply.*`, `.grounds.*`, `.leftover.*`, `.changes.*`, `.mended.*` and `.rebased.*` files excepted) and landing's `record`, which applies the rule in the other direction, tree to checkout.
- Rebase, fast-forward and branch removal: no copy. No other Gauntlet file rebases, merges or removes a branch.
- Creating a branch at a tree's tip for Archon to cut a tree on: 1 home, `.shared/pin.py` (worktree cut design), called by `gauntlet-run/scripts/pin.py` for the first tree and by `land/scripts/pin.py` for each second tree.
- Fences for an agent writing code or tests: 2 designed copies, `write-code/coder.mcp.json` and `write-tests/test-writer.mcp.json` (writing design), both rooted at the agent's own working folder, the tree. The mend's two writers take their settings verbatim, plus read access to `gauntlet/mend`.
- Briefing the owner on a red and asking before every landing: 1 designed role, the amicus (writing design, "Amicus"), a shared block the mend includes; it rules on nothing. The mend's cases are a red on the rebased tree, a mender's contest or failed commit, and an UNSOUND mend review, plus the review before landing; the owner's direction (writing design, "Direction") picks the mender and binds the next pass.
- Asking the owner: one wait per iteration, `ask`, at the end of every iteration of group `repair` that the owner has not ended, on the id of the run the mend executes in. There is no stall count: every iteration is an owner stop.
- Reading the checkout from a tree: no copy. The checkout root (the tree run's `items` input without its trailing `/gauntlet/items/<slug>.md`, worktree cut design; the re-mend run's `checkout` input) is read by node `copy-in` of the tree run for files; the mend's `onto` is the only node reading the checkout's `HEAD` from a tree, and `land`'s `onto` the only one in `gauntlet-run`.

Measured in Archon's reference: the loop, wait and resume forms are `runtime-model-design.md`'s ("Loop shape and bounds", "Resume and rerun"); `archon complete --force` removes a worktree whose commits are on no remote, which `archon isolation cleanup` keeps. An `include:` expands at load time into ordinary nodes of the containing scope, ids `<includeId>__<id>` (`workflow-language.md:1588-1596`), and only a `workflow:` node in a `loop_group` body is rejected (`:1732-1733`, `:2543-2544`), so a `workflow:` node of an included block outside a loop is a documented form; includes nest 3 deep (`:1735`), and `gauntlet-run` nests one. A `workflow:` node with `isolation: worktree` gets the branch `archon/task-<parentRunId8>-<nodeId>-<hash>-child-<n>` (`:2105`), and a local branch of that name is reused (worktree cut design, "Branch reuse"). Unmeasured: whether a resumed `tree` node of `gauntlet-run` resumes its child run's completed nodes or runs them anew; the mend's `always_run` nodes rerun either way. Unmeasured: whether the node id Archon hashes into a branch name for a `workflow:` node inside an included block is the expanded id `<includeId>__<id>` (`land__retree`); the re-mend run's `branch-check` fails the run naming both branches when it is not.

## Modules

### `mend/mend.yaml` (the mend: rebase, verify, repair, and the review before landing)

Included by `gauntlet-tree`, as node `mend` after `write`, when `$write.output.outcome == 'written'`, with `slug`, `checkout`, `branch`, `brief` and `stage` from its node `paths` and `summary` from `write`, and by `gauntlet-remend`, as node `mend`, with `slug`, `checkout`, `stage` and `summary` from the run's inputs, `branch` the second branch and `brief` from its node `paths`. The tree run's `handoff` prints the mend's `outcome` in place of writing's when the mend ran, and its `direction` and `amicus`; the re-mend run's `handoff` prints the mend's `outcome`, `direction` and `amicus`. It runs in a tree: every path it reads or writes is in that tree, and it reads the checkout only by `git -C $INPUTS.checkout rev-parse HEAD`. Nodes `onto`, `rebase`, `test-tree`, `red`, `test-head`, `confirm` and the group `repair` carry `always_run: true` (what it does on a resume: `runtime-model-design.md`, "Resume and rerun"). Test-run files sit in `gauntlet/mend/`. Its waits are answered on the id of the run the mend executes in, the tree run's or the re-mend run's.

The mend ends in the owner, on every landing, failed or clean (D-92). Group `repair` is the amicus loop: each iteration ends in the one wait `ask`, where the owner chooses, and the amicus (the shared block, writing design "Amicus") briefs the owner first. The review before landing is this block's node `final`, run in the iteration where the tree is landable; it is the landing design's, and it runs in the tree run and in the re-mend run alike, never in block `land`, which holds no agent and no wait.

```yaml
name: mend
description: >-
  Gauntlet mend, included by gauntlet-tree and gauntlet-remend only. Not for direct use.
inputs:
  slug: { description: The item file's slug. }
  checkout: { description: Absolute path of the owner's checkout. }
  branch: { description: The tree's branch. }
  brief: { description: Absolute tree path of gauntlet/baseline/<slug>.brief.txt. }
  stage: { description: "The stage of the approved plan this tree wrote, counted from 1 (gauntlet-design.md, \"Stages\")." }
  summary: { description: The plan summary and the approved revision summaries, shown with the review before landing. }
returns: handoff

nodes:
  - id: onto                           # the checkout's HEAD as the mend finds it
    always_run: true
    bash: <head = git -C $INPUTS.checkout rev-parse HEAD. tip = git rev-parse $INPUTS.branch.
          moved = not (git merge-base --is-ancestor head tip), or the file gauntlet/mend/$INPUTS.slug.rebased.<head> exists
          (a first pass already started rebasing the branch onto this head, so a resume still reruns the tests), or
          unreviewed is true. unreviewed = a gauntlet/mend/$INPUTS.slug.mended.<n>.txt exists and no gauntlet/mend/$INPUTS.slug.review.<m>.txt
          with m >= the highest such n has line 1 "Verdict: SOUND" (a mend committed before a stop, read from the files).
          print { head, moved, unreviewed }>
    output_format: <object: head (string), moved (boolean), unreviewed (boolean), all required>

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

  - id: test-head                      # the checkout's HEAD alone, only when the rebased tree is red without it or a mend awaits review
    depends_on: [red]
    when: "$red.output.red == true || $onto.output.unreviewed == true"
    always_run: true
    bash: <file = gauntlet/mend/$INPUTS.slug.head.$onto.output.head.txt. file absent:
          git checkout --detach $onto.output.head, run the brief command as test-tree
          does into file, then git checkout $INPUTS.branch, on every exit path.
          print { file } as an absolute tree path>
    output_format: <object: file (string), required>

  - id: confirm                        # red with the head check; red opens the first case; runs whenever red ran
    depends_on: [red, test-head]
    trigger_rule: none_failed_min_one_success
    always_run: true
    runtime: uv
    script: verify
    with: { run: $test-tree.output.file, head: { from: $test-head.output.file, if_skipped: "" } }

  - id: repair                         # the only writer in the tree after writing: the amicus loop, on every landing
    depends_on: [onto, confirm]
    trigger_rule: none_failed_min_one_success
    always_run: true
    loop_group:
      max_iterations: <CAP>               # the bound CAP, runtime-model-design.md, "Loop shape and bounds"
      fresh_context: true
      until_bash: 'end=$pose.output.end; [ -n "$end" ]'
      nodes:
        - id: hear                     # the owner's last answer, kept in the tree; every iteration
          bash: <n = one above the highest n among the direction, review, reply and amicus files gauntlet/mend/$INPUTS.slug.*.<n>.*.
                $LOOP_PREV.ask.output.decision: discuss: nothing recorded. rework-code, rework-tests or again: write the direction
                file gauntlet/mend/$INPUTS.slug.direction.<n>.md by cp -n semantics, in the form the writing design gives
                ("Direction": line 1 "Rework: code", "Rework: tests" or "Rework: again", line 2 "Landed: " and $INPUTS.stage less
                one, a blank line, $LOOP_PREV.ask.output.text verbatim). back-to-planning: the same file with "Rework: planning".
                land or leave: write that word to gauntlet/mend/$INPUTS.slug.reply.<n>.txt by cp -n semantics.
                print { n, end, rework }: end "done" for land, "left" for leave, "planning" for back-to-planning, "" otherwise;
                rework "code" or "tests" for those decisions, "again" for again, and "again" in the group's first iteration
                ($LOOP_PREV.hear.output.n empty) when $onto.output.unreviewed is true and no gauntlet/mend/$INPUTS.slug.review.<m>.txt
                with m >= the highest n of a mended file exists, so a mend left with no review is retested and reviewed before the
                owner is asked (no direction file is written for it); else "">
          output_format: <object: n (integer), end ("" | done | left | planning), rework ("" | code | tests | again), all required>

        - id: changes                  # the branch past the checkout's HEAD, for the amicus and the review; not once the owner has ended it
          depends_on: [hear]
          when: "$hear.output.end == ''"
          bash: <git -C <tree> log -p $onto.output.head..$INPUTS.branch, <tree> the tree's root, into
                gauntlet/mend/$INPUTS.slug.changes.$hear.output.n.txt, over any earlier file of that n.
                print { file } as an absolute tree path>
          output_format: <object: file (string), required>

        - id: mend-code                # the owner's direction is Rework: code; the owner picks the mender, no agent does
          depends_on: [hear, changes]
          when: "$hear.output.rework == 'code'"
          command: mend-code
          context: fresh
          allowed_tools: []
          mcp: mend-code.mcp.json
          prompt: <the direction file gauntlet/mend/$INPUTS.slug.direction.$hear.output.n.md; the latest run file and $test-head.output.file;
                  the approved plan gauntlet/plans/approved/$INPUTS.slug.txt and each of its revisions in order of N>
          output_format: <object: outcome (committed | contest | commit-failed), commit (string), grounds (string), all required>

        - id: mend-tests               # the owner's direction is Rework: tests
          depends_on: [hear, changes]
          when: "$hear.output.rework == 'tests'"
          command: mend-tests
          context: fresh
          allowed_tools: []
          mcp: mend-tests.mcp.json
          prompt: <as mend-code, with the approved spec gauntlet/specs/approved/$INPUTS.slug.txt and its revisions in place of the plan>
          output_format: <as mend-code>

        - id: retest                   # the branch as the mender left it; runs only after a committed mend or a run again
          depends_on: [hear, mend-code, mend-tests]
          trigger_rule: none_failed_min_one_success
          when: "$mend-code.output.outcome == 'committed' || $mend-tests.output.outcome == 'committed' || $hear.output.rework == 'again'"
          bash: <as test-tree, unconditionally, into gauntlet/mend/$INPUTS.slug.run.$onto.output.head.<tip>.txt, the key differing from
                test-tree's file by construction after a committed mend; after a run again the file is rewritten by cp -n semantics
                under the run's n: gauntlet/mend/$INPUTS.slug.run.$onto.output.head.<tip>.again.$hear.output.n.txt.
                print { file } as an absolute tree path>
          output_format: <object: file (string), required>

        - id: recheck                  # red with the head check, on the mended or rerun branch
          depends_on: [retest]
          runtime: uv
          script: verify
          with: { run: $retest.output.file, head: { from: $test-head.output.file, if_skipped: "" } }

        - id: mended                   # the branch past the checkout's HEAD, for the reviewer; also the record that a mend was committed
          depends_on: [recheck]
          bash: <A run again whose recheck is red, or a run again with no gauntlet/mend/$INPUTS.slug.mended.*.txt file (the repair
                has committed no mend): print { "file": "" }. Else, after a committed mend or after a run again not red that
                follows one (a SOUND review of the latest committed mend ends its case, so after a run again that mend has
                none): git -C <tree> log -p $onto.output.head..$INPUTS.branch, <tree> the tree's root, into
                gauntlet/mend/$INPUTS.slug.mended.$hear.output.n.txt, over any earlier file of that n.
                print { file } as an absolute tree path>
          output_format: <object: file (string), required>

        - id: review                   # every committed mend read before it can end its case, after a run again too; never on a red recheck
          depends_on: [mended]
          when: "$recheck.output.red == false && $mended.output.file != ''"
          command: mend-review
          context: fresh
          allowed_tools: []
          mcp: mend-review.mcp.json
          prompt: <review file gauntlet/mend/$INPUTS.slug.review.$hear.output.n.txt; the latest direction file
                  gauntlet/mend/$INPUTS.slug.direction.<n>.md; the run files $retest.output.file and $test-head.output.file;
                  recheck's red; the mender's outcome and grounds when this iteration ran a mender, or "again" when it did not;
                  the mended file $mended.output.file; the approved plan and spec with their revisions in order of N>
          output_format: <object: verdict (SOUND | UNSOUND), file (string), all required>

        - id: pose                     # whether the owner has ended it, the case, and the options
          depends_on: [hear, review]
          trigger_rule: none_failed_min_one_success
          bash: <hear ended it: end is hear's. A `discuss` answer keeps $LOOP_PREV.pose.output.case and its files. Else end "", and the case, first that holds: red (recheck red, or in the first
                iteration confirm red); contest or commit-failed (this iteration's mender outcome; the grounds written by cp -n to
                gauntlet/mend/$INPUTS.slug.grounds.$hear.output.n.txt, an uncommitted mend, git status --porcelain not empty,
                gauntlet/ excluded, counting as commit-failed; its leftover patch and the restore of the tree to HEAD, before the case is read: runtime-model-design.md, "Commit model", "The mend's uncommitted edits"); unsound (this iteration's review is UNSOUND); else review (the tree
                is landable: not red, nothing uncommitted, the latest committed mend, when there is one, reviewed SOUND).
                files = newline-separated tree paths the amicus reads: the latest run file and head file, the changes file, the
                latest direction file, the grounds file, the leftover patch gauntlet/mend/$INPUTS.slug.leftover.$hear.output.n.patch, the review or mended file of the case, each when there is one (the review before landing's file is added by node `files`, once `final` has written it).
                options: discuss, rework-code, rework-tests, again, back-to-planning, leave, and land when the case is review.
                print { end, case, files, options }>
          output_format: <object: end ("" | done | left | planning), case (string), files (string), options (array of { id, label }), all required>

        - id: final                    # the review before landing; only when the tree is landable and the owner has not ended it
          depends_on: [pose, changes]
          when: "$pose.output.end == '' && $pose.output.case == 'review' && $LOOP_PREV.ask.output.decision != 'discuss'"
          command: final-review
          context: fresh
          allowed_tools: []
          mcp: final-review.mcp.json
          prompt: <the file to write, gauntlet/mend/$INPUTS.slug.final.$hear.output.n.txt; stage $INPUTS.stage; the item file
                  gauntlet/items/$INPUTS.slug.md; the approved plan files, gauntlet/plans/approved/$INPUTS.slug.scope.txt and gauntlet/write/$INPUTS.slug.scope.rev*.txt;
                  the blocks files gauntlet/write/$INPUTS.slug.blocks.*.json; the changes file $changes.output.file>

        - id: files                    # the files the amicus reads: pose's, and for case review the review before landing's file, which exists only once final has run
          depends_on: [pose, final]
          trigger_rule: none_failed_min_one_success
          when: "$pose.output.end == ''"
          bash: <print { files }: $pose.output.files, then, for case review, gauntlet/mend/$INPUTS.slug.final.<k>.txt (k this
                iteration's n or, after a discuss, the latest final file), each when there is one>
          output_format: <object: files (string), required>

        - id: amicus                   # the shared amicus block (writing design, "Amicus"): briefs the owner, rules on nothing
          depends_on: [pose, files]
          trigger_rule: none_failed_min_one_success
          when: "$pose.output.end == ''"
          include: amicus
          with: { slug: $INPUTS.slug, case: $pose.output.case, files: $files.output.files,
                  record: gauntlet/mend/$INPUTS.slug.amicus.$hear.output.n.md, words: $LOOP_PREV.ask.output.text }

        - id: show                     # what the owner reads at ask
          depends_on: [amicus]
          bash: <print: "Mending $INPUTS.slug after the rebase onto $onto.output.head." and the case; then the text of
                gauntlet/mend/$INPUTS.slug.amicus.$hear.output.n.md verbatim; case review: then the test line ("Checkout not moved
                past the tree's base: not rerun.", or "Rerun on <head>: no new failure.", "Mended on <head>: no new failure." when
                a gauntlet/mend/$INPUTS.slug.mended.*.txt file exists), $INPUTS.summary, git diff --stat <head> <branch>, and
                git log --reverse --format='%h%n%B' <head>..<branch>, all in the tree>

        - id: ask                      # the owner, at every iteration the owner has not ended; sole terminal sink of the body
          depends_on: [pose, show]
          trigger_rule: none_failed_min_one_success
          when: "$pose.output.end == ''"
          wait:
            form: select
            attention: "$show.output"
            options: "$pose.output.options"

  - id: handoff                        # the mend's returns, read by the tree run's handoff
    depends_on: [rebase, red, confirm, repair]
    trigger_rule: none_failed_min_one_success
    bash: <the latest by n of gauntlet/mend/$INPUTS.slug.reply.<n>.txt (the word land or leave) and gauntlet/mend/$INPUTS.slug.direction.<n>.md
          with line 1 "Rework: planning". leave: print { "outcome": "left", "direction": "", "amicus": "" }. planning: print
          { "outcome": "planning", "direction": the absolute path of that direction file, "amicus": the absolute path of
          gauntlet/mend/$INPUTS.slug.amicus.<m>.md, m the highest n below that direction's }. land: first, the highest-n gauntlet/mend/$INPUTS.slug.mended.<n>.txt with no
          review file of n or higher whose line 1 is "Verdict: SOUND": exit 1 naming it, so no mend reaches landing unreviewed;
          else print { "outcome": "ready", "direction": "", "amicus": "" }>
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [ready, left, planning] }
        direction: { type: string }    # absolute tree path of the Rework: planning direction; "" otherwise
        amicus: { type: string }       # absolute tree path of the amicus record of that direction; "" otherwise
      required: [outcome, direction, amicus]
```

Every stop is a failed node: a rebase conflict or a failed repair node. It fails the tree run and so `gauntlet-run`'s node `tree` (in a re-mend, the re-mend run and so the round's node `retree`, and `archon workflow resume <gauntlet-run id>` re-drives that child); the tree, its branch and any rebase in progress stay,; the resume, the restart of `repair` and what the mend owes (`unreviewed` from `onto`) are `runtime-model-design.md`'s, "Resume and rerun"; its direction, review, reply, changes, amicus, final and mended files are kept. A red on the rebased tree is no stop: it is the first amicus case. Every iteration that is not the owner's ending one briefs the owner and asks, and an iteration the owner has ended runs no agent. The owner chooses at `ask`: discuss with the amicus; run again with a direction (`rework-code` or `rework-tests` names the mender, `again` reruns the tests with no mender and an empty direction); `back-to-planning`; `leave`, which hands off `left` with the tree kept, so `gauntlet-run` ends with no landing; and, only when the tree is landable (case `review`), `land`. The owner never sees a diff in the repair's cases; the review before landing shows the diff stat and the commit messages. An uncommitted mend (a commit-failed mender) is a case, never an end. The mend's commits and its rebase rules are `runtime-model-design.md`'s, "Commit model".

Fixtures, `mend/fixtures/<route>.stubs.yaml`, one per route: `still` (`moved` false, `test-tree` not reached, `repair` reaches case `review`, `final`, `ask` answered `land`, `ready`); `moved` (`red` false, `test-head` not reached, case `review`, `land`, `ready`); `resumed` (`moved` true on a rebased marker, `test-tree` reached); `head-red` (`red` true, `confirm` not red, case `review`, `ready`); `red-code` (`confirm` red, case `red`, `ask` answered `rework-code`; iteration 2 `mend-code` committed, `recheck` not red, `review` SOUND, case `review`, `land`; `ready`); `red-tests` (`rework-tests`, `mend-tests` committed, not red, SOUND; `ready`); `unsound` (`mend-code` committed, `review` UNSOUND, case `unsound`, `rework-code` again, SOUND; `ready`); `uncommitted` (`mend-code` commit-failed, `retest` not reached, case `commit-failed`, `ask` reached); `discuss` (`ask` answered `discuss`; iteration 2 the amicus reads the owner's words, `ask` reached again); `again` (case `red`, `ask` answered `again`; iteration 2 `changes`, menders not reached, `retest` green, `mended` prints "", `review` not reached, case `review`, `ready`); `again-review` (`mend-code` committed, `recheck` red, `review` not reached; iteration 2 `again` answered; iteration 3 `retest` green, `mended` writes its file, `review` SOUND, case `review`, `ready`); `resumed-review` (a mended file with no review on file, `confirm` not red, iteration 1 a run again: menders not reached, `review` SOUND, case `review`, `ready`); `planning` (case `red`, `back-to-planning`, `planning` with the direction and the amicus record); `leave` (case `review`, `leave`, `left`); `conflict` (`rebase` fails, its rebased marker written, `handoff` not reached).

### `land/land.yaml` (landing in the checkout)

Included by `gauntlet-run` only, once per round and stage: as node `land` after `cut`, when the tree run hands off `ready`, and as nodes `land-2`, `land-3` and `land-4`, each after the round before it, when that round hands off `moved`; a later stage includes the same four under its own ids (`gauntlet-design.md`, "Stages"). A round takes `slug` from the cut's hand-off (`$cut.output.slug`); `round` its own include id; `stage` its stage; `worktree` and `branch` from the cut (`land`) or the round before; `summary` from the cut, for the re-mend run's review; and `made` from the round before. It runs in the checkout, reaches a tree only by `git -C <worktree>`, `archon complete` and, for the re-mend, a `workflow:` node, and writes nothing in a tree. It has no agent node and no wait: the owner chose to land at the review before landing, in the tree run or the re-mend run that made `worktree` (this design, node `final` of `mend/mend.yaml`), so a round that reaches `merge` has the owner's land. `onto` carries `always_run: true` (`runtime-model-design.md`, "Resume and rerun").

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
  summary: { description: The plan summary and the approved revision summaries, handed to the re-mend run's review. }
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

  - id: retree                         # the re-mend run, in a second tree: block mend only, with its review and the owner, then back here
    depends_on: [onto, repin]
    workflow: gauntlet-remend
    isolation: worktree
    with: { slug: $INPUTS.slug, branch: $repin.output.branch, from: $INPUTS.worktree, checkout: $onto.output.checkout,
            stage: $INPUTS.stage, summary: $INPUTS.summary }

  - id: cur                            # the tree this round lands
    depends_on: [onto, retree]
    trigger_rule: none_failed_min_one_success
    runtime: bun
    script: <print { outcome, worktree, branch, made, direction, amicus }. retree ran (its output is not ""): outcome, worktree, branch, direction and amicus from it
            (outcome ready, left or planning), made the input made with the input branch added as its last line. Else outcome
            "ready" and the inputs, read as INPUTS_WORKTREE, INPUTS_BRANCH and INPUTS_MADE, direction and amicus "">
    with: { retree: { from: $retree.output, if_skipped: "" } }
    output_format: <object: outcome (enum ready, left, planning), worktree, branch, made, direction, amicus (strings), all required>

  - id: merge                          # the only write to the checkout's tracked files
    depends_on: [onto, cur]
    when: "$cur.output.outcome == 'ready'"
    bash: <now = git rev-parse HEAD in the checkout. Moved: git merge-base --is-ancestor now $cur.output.branch fails and
          git merge-base --is-ancestor $cur.output.branch now fails (the branch no longer fast-forwards the checkout and is
          not in it). Moved in the last round ($INPUTS.round ends in land-4): print "The checkout moved from <onto> to <now> after
          the last round of landing checked it; $cur.output.branch no longer fast-forwards it. Bring the checkout back to an ancestor of
          $cur.output.branch, then archon workflow resume <run id>.", exit 1, writing nothing. Moved in any other round:
          print on stderr "The checkout moved from <onto> to <now> after landing checked it; the next round checks it and meets
          the owner again.", print { "result": "moved" }, exit 0, writing nothing. Else the fast-forward merge of `runtime-model-design.md`, "Commit model", of $cur.output.branch. git
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
          gauntlet/specs/approved/$INPUTS.slug.rev*.txt, gauntlet/write/$INPUTS.slug.* except $INPUTS.slug.iter.txt (it grows in every stage), gauntlet/revisions/$INPUTS.slug.* and
          gauntlet/revisions/$INPUTS.slug-summary.*: target the same path in the checkout. Absent: cp -n. Identical (cmp):
          nothing. Differing: exit 1 naming both paths, nothing more copied>

  - id: remove                         # every tree this landing made
    depends_on: [cur, record]
    bash: <for each branch in $cur.output.made, then $cur.output.branch: branch absent: nothing. Else
          archon complete <branch> --force, its failure exiting non-zero with its output>

  - id: handoff
    depends_on: [cur, merge, remove]
    trigger_rule: none_failed_min_one_success
    runtime: bun
    script: <print { outcome, worktree, branch, made, direction, amicus } with the last five from cur. outcome: "left" when cur's outcome is
            left; "planning" when cur's outcome is planning; "moved" when merge's result is moved; "landed" when merge's result is merged>
    with: { cur: $cur.output, merge: { from: $merge.output.result, if_skipped: "" } }
    output_format:
      type: object
      properties:
        outcome: { type: string, enum: [landed, left, planning, moved] }
        worktree: { type: string }
        branch: { type: string }
        made: { type: string }
        direction: { type: string }
        amicus: { type: string }
      required: [outcome, worktree, branch, made, direction, amicus]
```

Landing re-mends within the landing rounds' bound (`runtime-model-design.md`, "Loop shape and bounds"). A round whose `onto` finds the checkout past the branch (the branch neither contains the checkout's `HEAD` nor is contained by it) re-mends before it merges, while that bound allows: `repin` creates the second branch at the tree's tip, `retree` starts `gauntlet-remend` on it, in a second tree, and the round lands that tree's branch, which `cur` adds to `made`. The re-mend rule: each re-mend meets the owner with a new review before landing, because the re-mend run's block `mend` ends in the amicus loop and node `final`, like the tree run's, so what lands after a re-mend is what the owner chose to land on that tree. A checkout that moves while the owner reviews is no stop in the first three rounds: the owner's land stands in the tree run, the round's `onto` finds the move, and the re-mend run asks the owner again; `merge` writes nothing when the checkout moves after `onto` checked it, the round hands off `moved`, and the next round checks the checkout again and re-mends if the branch no longer fast-forwards it. `merge` counts a move only when the checkout's `HEAD` is no longer an ancestor of the branch, in every round, so a checkout `HEAD` the branch still fast-forwards lands. In the last round such a move fails `merge`, naming it. No move ends the run unlanded and unnamed (D-47, D-48). When the re-mend run's mend ends on the owner's `leave` or `back-to-planning`, `cur` hands off `left` or `planning` and the round ends with every tree kept. Each stage meets the owner and lands before the next stage starts. Landing rounds multiply with stages by repetition and never by sharing: each stage has its own rounds under its own ids and its own `made`, so a plan of several stages has the same rounds per stage and no more.

Every stop is a failed node: a move that would need a third re-mend (`onto`), a move found by `merge` in `land-4`, a failed re-mend run (`retree`), a merge git refuses over the owner's uncommitted edits (the owner stashes them; a commit would move `HEAD`, and the resumed `merge` would count a move), a differing record or a failed removal. Every tree and branch stays, and the run is resumed as `runtime-model-design.md`, "Resume and rerun", says. Landing never resets, amends or drops a commit, never stashes, resets or discards the owner's edits, and never cancels the run; the rebase belongs to the mend, in a tree. Unrelated uncommitted files in the checkout stay as they are. A resume after `merge` finds the branch an ancestor of the checkout, so `onto` passes and `merge` replays.

Fixtures, `land/fixtures/<route>.stubs.yaml`, one per route: `land` (`onto` not moved, `repin` not reached, `merge`, `landed`); `moved` (`onto` moved, `repin` and `retree` reached, `landed`); `moved-left` (`retree` hands off `left`, `merge` not reached, `left`); `moved-planning` (`retree` hands off `planning`, `merge` not reached, `planning`); `waited` (`merge` prints `moved`, `record` not reached, `moved`); `third` (`made` holds two branches, `onto` moved, `onto` fails, `repin` not reached); `moved-last` (round `land-4`, the checkout's `HEAD` no longer an ancestor of the branch at `merge`, `merge` fails naming the move, `record` not reached); `refused` (`merge` fails on uncommitted edits with the stash advice, `record` not reached).

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

The child run in a second tree, started only by node `retree` of block `land`. Archon cuts the tree on the branch `repin` created, and runs the repository's `worktree.copyFiles` and `worktree.postCreate` before its first node. The tree holds the previous tree's commits and none of its ignored `gauntlet/`, so `copy-in` brings that over, all but the previous mend's direction, amicus, final, review, reply, grounds, changes, mended and rebased-marker files, so the re-mend numbers its own files from 1, its amicus and reviewers read none of the superseded ones, and no earlier mend counts as committed in its repair. It runs block `mend` and nothing else; every agent it holds is the mend's. Its pauses are answered on its own id, which `archon workflow get <gauntlet-run id> --json` gives at `.metadata.approval.childRunId`. Replaces nothing.

```yaml
name: gauntlet-remend
description: >-
  Gauntlet's re-mend run, started only by block land's node retree. Copies the previous tree's gauntlet/ into its own
  tree and runs block mend there. Never started by hand.
inputs:
  slug: { description: The item file's slug. }
  branch: { description: The branch node repin of block land created at the previous tree's tip. }
  from: { description: Absolute path of the previous tree. }
  checkout: { description: Absolute path of the owner's checkout. }
  stage: { description: The stage this tree lands, counted from 1. }
  summary: { description: The plan summary and the approved revision summaries, shown with the review before landing. }
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
          gauntlet/mend/$INPUTS.slug.direction.*, .amicus.*, .final.*, .review.*, .reply.*, .grounds.*, .leftover.*, .changes.*, .mended.* and .rebased.*, to the same path under this
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
    with: { slug: $INPUTS.slug, checkout: $INPUTS.checkout, branch: $INPUTS.branch, brief: $paths.output.brief,
            stage: $INPUTS.stage, summary: $INPUTS.summary }

  - id: handoff
    depends_on: [paths, mend]
    runtime: bun
    script: <print { worktree, branch, outcome, direction, amicus }: worktree from $paths.output, branch from git branch --show-current,
            outcome, direction and amicus from $mend.output>
    output_format: <object: worktree, branch, outcome, direction, amicus (strings), all required; outcome enum ready, left, planning>
```

Fixtures, `gauntlet-remend/fixtures/<route>.stubs.yaml`, one per route: `remend` (`handoff` reached, `ready`); `left` (the mend hands off `left`); `planning` (the mend hands off `planning`); `conflict` (`copy-in` fails, `mend` not reached); `branch` (`branch-check` fails, `copy-in` not reached).

`gauntlet-remend/scripts/guard.ts` is `gauntlet-tree/scripts/guard.ts`'s two lines, the shared working-folder check, run in the second tree.

### `mend/commands/mend-code.md`, `mend/commands/mend-tests.md`, `mend/commands/mend-review.md`, `mend/commands/final-review.md` (the mend's roles)

The four agents of the mend. Each starts a fresh session, primed from files. No agent rules in the mend: the owner picks the mender (`rework-code` or `rework-tests`), and the amicus, a shared block (writing design, "Amicus"), briefs the owner. Replaces nothing.

```markdown
mend-code
Inputs: the owner's direction file, the rebased tree's red run file and the head file, the approved plan with its
revisions. Work from the approved plan and the direction only.
Do what the owner's direction says, changing code only; make pass any failing tests a run file names.
Run the repository's tests through fence-checks as often as the work needs.
A test you believe wrong: stop, outcome contest, grounds. Never ask for a test to be changed any other way.
Done: commit through the commit tool, with a message of your own and the paths you changed. A failed commit: stop,
outcome commit-failed, the tool's output as grounds. Never retry it.
Tools: fence-files, fence-checks.
```

```markdown
mend-tests
Inputs: the owner's direction file, the rebased tree's red run file and the head file, the approved spec with its
revisions. Work from the approved spec and the direction only.
Change only the tests the direction names.
A change to a test's contract: only to match the approved spec. A test the spec makes impossible to keep: stop,
outcome contest, grounds.
Done: commit through the commit tool, with a message of your own and the paths you changed. A failed commit: stop,
outcome commit-failed, the tool's output as grounds. Never retry it.
Tools: fence-files, fence-checks.
```

```markdown
mend-review
Inputs: the review file to write, the latest direction file, the run files, recheck's red, the mender's outcome and
grounds or the word again, the mended file (the log and patches of the branch past the checkout's HEAD), the approved
plan and spec with their revisions.
Verdict SOUND or UNSOUND. UNSOUND when the mend departs from the approved plan or spec or from the direction, changes a
test's contract the approved spec does not require, leaves the tree red, or leaves a mend uncommitted. Write
the review file once: line 1 "Verdict: SOUND" or "Verdict: UNSOUND", then each finding with its path; write nothing else.
Tools: fence-files.
```

```markdown
final-review
Inputs: the file to write, the stage, the item file, the approved plan files and the plan's scope marks, the blocks files of
writing (each block's "outside" paths, the paths mark), the changes file (the log and patches of the branch past the checkout's HEAD).
The review before landing, short, because the review before implementation was extensive. Did the workers faithfully implement the
requested features and fix the bugs as instructed, and nothing else? Are there shortcuts that need to be redone properly?
Read each item of the item file against its own fields (Goal, Desired behavior, Constraints, Out of scope), the plan steps of
this stage with the item ids they cite, and the two scope-check marks: a step marked "added scope", and a block whose "outside"
list is not empty. Judge what a script cannot, such as a step that cites an item and does not serve it.
You rule on nothing. Write the file once: a few plain sentences for the owner, per item what was done and what was not, then
each mark and each shortcut with its path. The amicus carries your answer to the owner.
Tools: fence-files.
```

Fences, one file each beside `mend/mend.yaml`, every server rooted at the agent's own folder, the tree, as writing's are, received as the writing design's section `write-tests/test-writer.mcp.json` gives, with the test command and timeout read from `gauntlet/settings.json`:

| File | Server | Settings |
|---|---|---|
| `mend-code.mcp.json` | `fence-files` | `write-code/coder.mcp.json`'s, verbatim |
| `mend-code.mcp.json` | `fence-checks` | `write-code/coder.mcp.json`'s, verbatim |
| `mend-tests.mcp.json` | `fence-files` | `write-tests/test-writer.mcp.json`'s, with `:gauntlet/mend` added to `FENCE_READ` |
| `mend-tests.mcp.json` | `fence-checks` | `write-tests/test-writer.mcp.json`'s, verbatim |
| `mend-review.mcp.json` | `fence-files` | `FENCE_READ=.`; `FENCE_WRITE=gauntlet/mend/*.review.*.txt`; `FENCE_ONCE=gauntlet/mend/*.review.*.txt`; `FENCE_COMMIT` unset |
| `final-review.mcp.json` | `fence-files` | `FENCE_READ=.`; `FENCE_WRITE=gauntlet/mend/*.final.*.txt`; `FENCE_ONCE=gauntlet/mend/*.final.*.txt`; `FENCE_COMMIT` unset |

The amicus's fence is the shared block's, `amicus/amicus.mcp.json` (writing design).

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
| Where each landing node runs | block `mend`, included by `gauntlet-tree` after `write` and by `gauntlet-remend`, for the read of the checkout's `HEAD`, the rebase, every test run and every agent, each in its run's own tree; block `land`, included by `gauntlet-run` after `cut` under the ids `land`, `land-2`, `land-3` and `land-4` (and their stage prefixes), for the check, the second branch, the re-mend run's start, the merge, the record copy and the removal, and no wait | an agent node in `land/`; a rebase or test run in `land/`; any `land/` node writing in a tree; a `mend/` node writing in the checkout |
| The commit the mend rebases onto | `mend`'s node `onto`'s `head`, by `git -C $INPUTS.checkout rev-parse HEAD`, read by `rebase`, the test nodes, `repair` and `handoff` | any other tree-run or re-mend-run node reading the checkout's `HEAD` |
| Re-mending when the checkout moved | block `land`'s nodes `onto` (the check), `repin`, `retree` and `cur`, within the landing rounds' bound (`runtime-model-design.md`, "Loop shape and bounds"); `gauntlet-remend` running block `mend` only, in a second tree | a re-mend by any other node; a re-mend in the tree of the run before it; a rebase, test run or agent in `land/` |
| The second tree's branch | `land/scripts/pin.py` over `.shared/pin.py`, creating the branch Archon will name for node `<round>__retree` at the tip of the tree's branch | any other node or script composing that name or creating that branch |
| What the second tree holds | node `copy-in` of `gauntlet-remend`, the previous tree's `gauntlet/` by `cp -n` semantics, `settings.json` included, but `gauntlet/mend/<slug>.direction.*`, `.amicus.*`, `.final.*`, `.review.*`, `.reply.*`, `.grounds.*`, `.leftover.*`, `.changes.*`, `.mended.*` and `.rebased.*` | an agent or other node writing the second tree's `gauntlet/` before `mend`; a differing file overwritten |
| The commit landing lands against | `land`'s node `onto`'s `head`, read by `show` and `merge` | any other `land/` node reading the checkout's `HEAD`, `merge`'s ancestry check excepted |
| Rebasing the tree's branch | `mend`'s node `rebase`, `git rebase <head> <branch>` in the tree | any other rebase, reset, amend, squash or history rewrite in a Gauntlet file; a rebase in the checkout; a rebase aborted by Gauntlet |
| Whether the mend reruns tests | `onto`'s `moved` for `test-tree`; `red`'s answer, or `onto`'s `unreviewed`, for `test-head`; a committed mend or a run again for `retest` | a retest with no committed mend and no run again; a test run when the checkout's `HEAD` is in the branch's history, except after a first pass's rebase, marked by `gauntlet/mend/<slug>.rebased.<head>`; a head run when the rebased tree is not red without it and no mend awaits review; a test run in the checkout |
| The mend's test runs | `test-tree`, `test-head` and `retest`, as node `baseline` runs its command, with no node `timeout:`, into `gauntlet/mend/<slug>.run.<head>.<tip>.txt` and `gauntlet/mend/<slug>.head.<head>.txt` of the tree | any other file name or folder; another invocation of the brief command in `mend/` or `land/` |
| Red in the mend | `mend/scripts/verify.py` over `.shared/red.py`; a red with the head check is the first case of `repair`, and a mend `onto` finds unreviewed is retested and reviewed before the owner is asked | a comparison or listing in a `mend/` or `land/` node; a red stopping the run |
| Mending a red on the rebased tree | group `repair` of block `mend`: the amicus (writing design, "Amicus") briefs the owner on every red, contest, failed commit and UNSOUND review, and the owner's direction (`gauntlet/mend/<slug>.direction.<n>.md`, writing design "Direction") runs one mender: `mend-code` fenced out of `tests/` and `gauntlet/`, `mend-tests` fenced to `tests/` and the test base; `mend-review` reviews every mend into `gauntlet/mend/<slug>.review.<n>.txt`; only the owner ends the group, by `land`, `leave` or `back-to-planning` | an agent choosing a mender or ruling on a case; a mender run without a direction; one agent writing both code and tests; a mend that reaches landing unreviewed; a mend in the checkout; any other agent writing in the tree after writing |
| What the amicus and reviewers read of the branch | group `repair`'s node `changes`, after `hear`, into `gauntlet/mend/<slug>.changes.<n>.txt` for the amicus and `final`, and node `mended`, after `recheck`, into `gauntlet/mend/<slug>.mended.<n>.txt` for `review`, each `git -C <tree> log -p <head>..<branch>`; a `mended` file also records that the repair committed a mend | a git tool or command given to a mend agent; any other writer of those files; a log of the branch's whole history |
| The review before landing | node `final` of group `repair`, role `final-review`, writing `gauntlet/mend/<slug>.final.<n>.txt` in the iteration where the tree is landable (case `review`); it runs in the tree run and in the re-mend run, and in each re-mend (the re-mend rule), before every landing, failed or clean, and for each stage's own plan steps and items; it reads each item against its fields, the plan steps of the stage with their item ids and the two scope-check marks (plan review design, "Plan grammar"; writing design, the `outside` list of the blocks file); its answer reaches the owner through the amicus, with the choices `land`, `rework-code` or `rework-tests` or `again` (run again with a direction), `back-to-planning` and `leave` | the review in block `land` or in any node of `gauntlet-run`; a landing with no review; an agent ruling on the review; the review reading more than the files above |
| The summaries shown with the review | `write`'s hand-off `summary` (the plan summary and the approved revision summaries), carried by the tree run's `handoff` and node `cut` to `land`'s input `summary`, by `retree` to the re-mend run's input, and into `mend`'s input `summary`, which node `show` prints; the test line is composed by node `show` alone | any other node composing the summaries or the test line; either shown anywhere else |
| What the owner sees and answers | on the tree run's id, or the re-mend run's, `repair`'s `ask`, in every iteration the owner has not ended: the case, the amicus's explanation verbatim, and for case `review` the test line, the plan and revision summaries, the diff stat and the commit messages, form `select`, options `discuss`, `rework-code`, `rework-tests`, `again`, `back-to-planning`, `leave` and, for case `review` only, `land`; the answer kept by `hear` in `gauntlet/mend/<slug>.direction.<n>.md` or `<slug>.reply.<n>.txt`; `gauntlet-run`'s id asks nothing of landing | any other wait or agent in `mend/` or `land/`; a wait in block `land`; a diff shown at `ask`; `land` offered on a case that is not `review` |
| Which tree records reach the checkout | `record`'s five patterns | any other tree file copied, `gauntlet/mend/`, `gauntlet/items/` and `gauntlet/baseline/` included; a copy that overwrites a differing file |
| Removing the trees | node `remove` of the round that lands, `archon complete <branch> --force` for each branch in `made` and then the landed branch | a removal on leave or on any stop; a tree landing made and left behind after a landing |
| A stop in the mend or landing | a failed node with every tree kept, resumed as `runtime-model-design.md`, "Resume and rerun", says; a move past the re-mend bound, failed by `onto`, or found by the last round's `merge`, naming it | stashing, resetting or discarding the owner's edits; cancelling the run; removing a tree on any stop; a red ending the run outside the owner's `leave`; a round past the bound |

## Order

1. Red in the mend: `mend/scripts/verify.py`, `mend/tests/test_verify.py`. Needs `gauntlet-design.md`'s step 6. Agent: `builder`.
2. The mend's roles: `mend/commands/mend-code.md`, `mend/commands/mend-tests.md`, `mend/commands/mend-review.md`, `mend/commands/final-review.md`. Agent: `role-author`.
3. Mend block: `mend/mend.yaml`, `mend/mend-code.mcp.json`, `mend/mend-tests.mcp.json`, `mend/mend-review.mcp.json`, `mend/final-review.mcp.json`, `mend/fixtures/still.stubs.yaml`, `mend/fixtures/moved.stubs.yaml`, `mend/fixtures/resumed.stubs.yaml`, `mend/fixtures/head-red.stubs.yaml`, `mend/fixtures/red-code.stubs.yaml`, `mend/fixtures/red-tests.stubs.yaml`, `mend/fixtures/unsound.stubs.yaml`, `mend/fixtures/uncommitted.stubs.yaml`, `mend/fixtures/discuss.stubs.yaml`, `mend/fixtures/again.stubs.yaml`, `mend/fixtures/again-review.stubs.yaml`, `mend/fixtures/resumed-review.stubs.yaml`, `mend/fixtures/planning.stubs.yaml`, `mend/fixtures/leave.stubs.yaml`, `mend/fixtures/conflict.stubs.yaml`. Needs steps 1 and 2 and writing's `write-code/coder.mcp.json`, `write-tests/test-writer.mcp.json` and amicus block (its step 5). `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
4. The second tree's branch: `land/scripts/pin.py`, `land/tests/test_pin.py`. Needs the worktree cut design's `.shared/pin.py` (its step 1). Agent: `builder`.
5. The re-mend run: `gauntlet-remend/gauntlet-remend.yaml`, `gauntlet-remend/scripts/guard.ts`, `gauntlet-remend/fixtures/remend.stubs.yaml`, `gauntlet-remend/fixtures/left.stubs.yaml`, `gauntlet-remend/fixtures/conflict.stubs.yaml`, `gauntlet-remend/fixtures/branch.stubs.yaml`. Needs step 3 and the intake design's `.shared/working-folder.ts`. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.
6. Landing block: `land/land.yaml`, `land/fixtures/land.stubs.yaml`, `land/fixtures/moved.stubs.yaml`, `land/fixtures/moved-left.stubs.yaml`, `land/fixtures/moved-planning.stubs.yaml`, `land/fixtures/waited.stubs.yaml`, `land/fixtures/third.stubs.yaml`, `land/fixtures/moved-last.stubs.yaml`, `land/fixtures/refused.stubs.yaml`. Needs steps 4 and 5. `archon workflow list --json` and `archon validate workflows` pass from the pack root. Agent: `workflow-builder`.

`gauntlet-tree`'s node `mend` and its `handoff`'s `outcome`, `direction` and `amicus` need step 3; `gauntlet-design.md`'s step 8 needs step 6.

## Decisions for the owner

None open. Ruled (G-45, G-68, G-69; owner, 2026-11-05; D-47 and D-48 carried under D-85): when the checkout has moved past the branch's base, landing rebases the branch onto the checkout's new head, reruns the tests (and the repair when red) and then lands. Each round is an `include`d block of `land` under its own id that checks the checkout, re-mends on a move (the second tree run `gauntlet-remend`, running block `mend` only, in a second tree cut on a branch pinned at the tip of the branch of the tree the round lands, the first tree's for round 1) and meets the owner again in the re-mend run's review before landing. The number of rounds, the re-mend bound and the stop on a move found in the last round are `runtime-model-design.md`'s, "Loop shape and bounds". The earlier recommendation (stop and resume once the owner moves the new commits aside) and its alternative (hand off `left`) were not taken. Each re-mend meets the owner with a new review, and each stage of a staged plan has its own rounds.
