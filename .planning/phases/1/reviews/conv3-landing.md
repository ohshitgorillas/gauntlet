# Convergence round 3 - landing-design.md

Reviewer return (cad-reviewer-medium, opus), verbatim. Designs at 87e0734.

```json
{ "findings": [
  { "file": "docs/superpowers/specs/landing-design.md",
    "line": 234,
    "severity": "high",
    "claim": "new (rows H22, H34, P9). The design says \"a resumed `repair` starts at iteration 1, its verdict, review, reply, changes and mended files kept\", but `repair` only runs when `confirm` is red. On a resume, `test-tree` runs on the branch tip that already carries the mend. It reuses the green file `retest` wrote under the same key, `run.<head>.<tip>.txt` (:66, :157). So `confirm` is skipped, `repair` is skipped, and a committed mend with no SOUND review lands. `handoff` (:220-222) checks \"red false or confirm not red\" first, so it prints \"Rerun on ...: no new failure.\" even though a `mended.*` file exists. Two Homes rows are broken: :526 (\"a mend that ends unreviewed\") and :528 (the line at the gate).",
    "failure_scenario": "Rebase needed, so marker `rebased.<head>` is written. Iteration 1: juror CODE, mend-code committed, retest green, mended writes its file, then the `review` agent node fails (crash or timeout) or returns UNSOUND and the next iteration's juror fails. The owner runs `archon workflow resume <gauntlet-run id>`. `onto` gives moved true from the marker. `test-tree` reuses retest's green file, `red` is false, `test-head`, `confirm` and `repair` are skipped. `handoff` returns ready with \"Rerun on <head>: no new failure.\", and the gate offers to land a mend nobody reviewed, or one ruled UNSOUND." },
  { "file": "docs/superpowers/specs/landing-design.md",
    "line": 353,
    "severity": "low",
    "claim": "matches G-68: the D-47 amendment was applied in landing and H39 but not in gauntlet-design.md. Landing says \"`merge` counts a move only when the checkout's `HEAD` is no longer an ancestor of the branch, in every round, so a checkout `HEAD` the branch still fast-forwards lands\". The Homes row \"Landing on the checkout\" at gauntlet-design.md:414 still allows the merge only \"in the round the owner answers land, with the checkout unmoved\". Row H39.",
    "failure_scenario": "While the gate waits, the checkout HEAD moves to a commit the branch still contains (for example the owner checks out an earlier commit of the branch's history). Landing's `merge` fast-forwards as designed. Under gauntlet-design.md:414 that same merge is a forbidden write, because the checkout moved. A builder or checker holding both designs gets two contradicting rules for this route." }
] }
```
