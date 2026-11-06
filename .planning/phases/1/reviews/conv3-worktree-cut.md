# Convergence round 3 - worktree-cut-design.md

Reviewer return (cad-reviewer-medium, opus), verbatim. Designs at 87e0734.

```json
{ "findings": [
  { "file": "docs/superpowers/specs/worktree-cut-design.md",
    "line": 227,
    "severity": "medium",
    "claim": "Anchor worktree-cut-design.md:227, Homes row 'Approved files in the tree', forbidden column: \"any agent or other node writing the tree's `gauntlet/tasks`, `gauntlet/plans` or `gauntlet/specs`\". Line :172 says the same: \"# the only writer of the tree's gauntlet/tasks, plans and specs\". Both contradict gauntlet-design.md. Its Homes row 'Writing to the tree's `approved/` folders' (:406) and copy-list bullet (:29) make writing's `enter` a second writer of the tree's `gauntlet/plans/approved/<slug>.rev<N>.txt` and `gauntlet/specs/approved/<slug>.rev<N>.txt` (also :278 and :295). Row H7, with H8 and P3. Mark: matches G-12 (B07 was filed there as resolved). The applied ruling rewrote only the copy list in gauntlet-design.md, so this text still stands unresolved.",
    "failure_scenario": "A writing builder reads the cut design's Homes row, which forbids any node but `copy-in` from writing the tree's gauntlet/plans or gauntlet/specs. Under that row the builder cannot place node `enter` (gauntlet-design.md:278), so approved revisions have no legal writer. If `enter` is built anyway, the cut design's own home is broken, and a checker against the cut design flags `enter` as forbidden."
  },
  { "file": "docs/superpowers/specs/worktree-cut-design.md",
    "line": 217,
    "severity": "medium",
    "claim": "Anchor worktree-cut-design.md:217, Homes row 'Slug of the cut and the tree run', forbidden column: \"any node, prompt or other script of the cut or the tree run deriving it\". Writing's hearing runs inside the tree run as block `write`, and per writing-design.md:122 \"the hearing's rounds.py calls derive theirs from INPUTS_TASK\" (.shared/rounds.py, spec-review-design.md:96). So the scoped row still forbids a derivation G-23 requires. Row H36, with H16. Mark: matches G-82. The applied ruling (D-55, scoping the row to the tree run) did not resolve it, because writing's ledger calls into rounds.py run in the tree run.",
    "failure_scenario": "A writing builder obeys the cut design's row and makes write/scripts/ledger.py pass the slug instead of letting .shared/rounds.py derive it from INPUTS_TASK. That diverges from the shared core every profile uses. Or a checker of the cut design's home flags rounds.py inside block `write` of gauntlet-tree as a forbidden second derivation of the slug."
  },
  { "file": "docs/superpowers/specs/worktree-cut-design.md",
    "line": 100,
    "severity": "low",
    "claim": "Anchor worktree-cut-design.md:100: \"Its head (`name`, `inputs`, `worktree`, nodes `guard`, `intake`, `plan-review`, `spec-review`) is `gauntlet-design.md`'s\". Line :110 repeats it: \"# guard, intake, plan-review, spec-review: as gauntlet-design.md gives them\". Both leave out nodes `env-check`, `dirty` and `stop`. gauntlet-design.md gives the head with all three (:59-76, Order step 1 at :425, Phase order row at :396). The missing row is the gauntlet-run head's node list, under H1, H13-H15 and H16. Mark: new. The three nodes came in with D-33, D-52 and D-54, and this enumeration was not updated.",
    "failure_scenario": "The workflow-builder of cut step 3 writes nodes pin, tree and cut into gauntlet-run.yaml. It reads this design's closed list of head nodes, which says the head ends at spec-review after guard. So it may treat env-check, dirty and stop as foreign and drop or reorder them, or check its edit against a head that lacks the run-start checks."
  },
  { "file": "docs/superpowers/specs/worktree-cut-design.md",
    "line": 32,
    "severity": "low",
    "claim": "Anchor worktree-cut-design.md:32: \"a repository with no remote, or an unreachable one, cannot be cut, pinned branch or not; node `tree` fails with Archon's message\". Line :31 adds the same failure when origin/HEAD is unknown and there is no worktree.baseBranch, and :200 says \"The repository has a reachable `origin`\". No run-start node checks for an `origin` remote or a resolvable base branch, so a cause that is visible at run start surfaces only at phase 4. That is the pattern D-54 objection 2 rejected for the config check. Row P11, with H9 and A22. Mark: new.",
    "failure_scenario": "A repository with no `origin`, or with no origin/HEAD and no worktree.baseBranch, passes guard and env-check. The owner then works through intake, plan review and spec review, answering every pause, and only then does node `tree` fail with Archon's message. The owner must add a remote or config and resume, though a `git remote get-url origin` or a base-branch check in env-check would have refused at run start."
  },
  { "file": "docs/superpowers/specs/worktree-cut-design.md",
    "line": 83,
    "severity": "low",
    "claim": "Anchor worktree-cut-design.md:83: \"Not inside a git work tree, or HEAD has no commit: stderr names the checkout; exit 2.\" Line :87 pins it in the suite: \"exit 2 outside a git work tree\". No run can reach this branch. gauntlet-run's guard runs git's ignore check in the checkout, and env-check refuses an .archon/config.yaml that is untracked or differs from HEAD, which needs a work tree with a commit; both run before pin. Without the check, `git branch` still fails the node. So the check and its test are build and test work the sequence does not need (CLAUDE.md 1.3). Row H16. Mark: new.",
    "failure_scenario": "Every gauntlet-run that reaches node pin has already passed guard and env-check in a git work tree with a HEAD commit. The exit-2 path and its test case in gauntlet-run/tests/test_pin.py are built and kept for an input no run can deliver."
  }
] }
```
