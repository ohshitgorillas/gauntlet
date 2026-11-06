1. **blocker**: `landing-design.md:47`, row H22 (also H17, which carries `line` to the gate). Quoted: "moved = not (git merge-base --is-ancestor head tip)". Also `:30`: "a resume rebases, verifies and mends against the checkout as it then stands".
   Once the first pass has rebased the branch, the checkout's head is an ancestor of tip, so on any resume `onto` (always_run) prints `moved` false. `test-tree` is then skipped, and the skip passes on to `red`, `test-head`, `confirm` and `repair` (`workflow-language.md:83`).
   - Scenario (a): the rebase hits a conflict (`:55`). The owner runs `git rebase --continue` and resumes. The resolved rebase is never tested, and `handoff` (`:195`) prints "Checkout not moved past the tree's base: not rerun."
   - Scenario (b): any repair node fails (an agent error, verify exiting 2, a test node timing out) and the owner resumes. The confirmed red is never mended and `handoff` hands off `ready` with the same false line.
   - In both cases `land` shows that line at `gate`, and the owner lands an untested or still-red branch. The claim at `:205` that "a resumed `repair` starts at iteration 1" never comes true, because `repair`'s `when:` reads a skipped `confirm`.
   - The Homes rule at `:368` ("a test run when the checkout's HEAD is in the branch's history" is forbidden) writes the same mistake into the design's rules.

2. **high**: `landing-design.md:172`, row H34 (also H22). Quoted: "First that holds. hear left: end "left". recheck not red and review SOUND: end "done"."
   `pose` ends the repair without checking that the mender committed.
   - `mend-code` returns `commit-failed` with its edits left uncommitted in the tree. `retest` (`:143-147`, `none_failed_min_one_success`, so it runs after a mender that succeeded as a node) tests the dirty tree, and `recheck` finds it not red.
   - `mend-review`'s UNSOUND list (`:326-327`) does not cover a mend that was never committed, so the reviewer can rule SOUND. `pose` then ends "done" and `handoff` prints "Mended on <head>: no new failure.".
   - `land` then fast-forwards a branch that lacks the tested fix.
   - On a later resume, `rebase` meets the dirty tree, and git refuses with "cannot rebase: You have unstaged changes". The stop message at `:55` then tells the owner to run `git rebase --continue`, but no rebase is in progress.

3. **medium**: `landing-design.md:147`, row P9. Quoted: "as test-tree, unconditionally, into gauntlet/mend/$INPUTS.slug.run.$onto.output.head.<tip>.txt".
   When the mender does not commit (`contest` or `commit-failed`), tip is unchanged. `retest` then writes to the same path as `test-tree`'s file (`:63`) and overwrites it, possibly with a run on a dirty tree.
   That breaks the promise at `:30` that files are "keyed by the commits they ran on, so a rerun on the same commits reuses its file". It also changes what the juror's fallback `$test-tree.output.file` (`:116`) shows from then on.

4. **medium**: `landing-design.md:143`, `:157`, internal (CLAUDE.md 1.3). Quoted: `:143` "retest ... skipped when no mender ran" and `:157` "review # every mend read before it can end the repair". With `:327`: "UNSOUND when ... leaves the tree red".
   - After a `contest`, nothing was mended, yet `retest` runs a full brief-suite run (up to 900 s) on the same commit and `review` spends an agent session.
   - Whenever `recheck` is red, the review's verdict is fixed in advance (UNSOUND by its own role), and `pose` ends on recheck alone. That agent call buys nothing the sequence needs.
   - The fix: gate `retest` and `recheck` on `outcome == committed`, and gate `review` on recheck not being red.

5. **medium**: `landing-design.md:172-174` with `:116`, internal. Quoted: "case = newline-separated tree paths the next juror reads: the latest run file when red ..." and "the case: $LOOP_PREV.pose.output.case, or $test-tree.output.file when empty".
   - In an iteration where the juror rules DEFECTIVE, `retest` and `recheck` are skipped, so `pose` has no "latest run file" and no red to test. The case comes out empty or undefined.
   - After the owner's reply, the next juror falls back to `$test-tree.output.file`, the run from before any mend, even when an earlier iteration has already committed a mend. The same happens at iteration 1 after a resume.
   - Result: the juror and the mender (`:129` "the latest run file") work from a red that no longer matches the branch.

6. **medium**: `landing-design.md:178`, row H31. Quoted: "options [ { id: reply, label: "Guide the juror (your guidance in the text)" }, { id: leave, label: Leave } ]".
   The owner cannot accept the rebased tree or ask for a rerun.
   - Scenario: a flaky or environment-only failure on the rebased tree is red by `.shared/red.py`. The juror cannot mend it and rules DEFECTIVE.
   - The owner can then only keep sending guidance into a loop that cannot reach "not red and SOUND", or choose `leave`. A leave ends the run with no landing: the record copy and tree removal fall to the owner.
   - This is a stop on a non-issue (CLAUDE.md 1.4).

7. **low**: `landing-design.md:373`, row H31. Quoted: "`repair`'s `ask`, only on DEFECTIVE or 5 verdicts since the latest reply".
   This omits the third ask condition, which `pose` states at `:175-176` ("or hear.n >= 200") and `:98` relies on ("from iteration 200 every iteration asks, so the bound never fails the run"). A builder working from the Homes table would drop the ask that keeps `max_iterations` from failing the run.

I checked the candidates against `workflow-language.md:83`, `:324-332` (a skipped dependency passes its skip on; `none_failed_min_one_success`), `writing-design.md:270-295` (the coder and test-writer fences) and `gauntlet-design.md:16`, `:98`, `:165-206`, `:247-277`. Dropped after that check:
- The skip cascade on the `still` route.
- `land`'s branch-absent route.
- Record-copy collisions.
- The brief-versus-full test command in the mend's fence-checks: inherited verbatim from writing, not specific to landing.
- Multi-iteration fixtures: an A25 / cross-design question.
- Anything already covered by 1.01-1.12.
