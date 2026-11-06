# Convergence round 3 - spec-review-design.md

Reviewer return (cad-reviewer-medium, opus), verbatim. Designs at 87e0734.

```json
{ "findings": [
  { "file": "docs/superpowers/specs/spec-review-design.md",
    "line": 421,
    "severity": "high",
    "claim": "new. Rows A15 and H38. Node `vacate` (\"depends_on: [filing] ... cancel: ...\") is a second terminal node of the `hearing` body: nothing depends on it, and it does not lead to `bench`. That contradicts \"bench # the owner; sole terminal sink of the body\" (:498). loop-nodes.md:682-684 says: \"A wait pauses the group only as the body's sole terminal sink: nothing depends on it, and every other body node leads to it. Any other placement is a load error.\" plan-review-design.md:330 has the same shape. A15's documented verdict never checked `vacate`.",
    "failure_scenario": "The builder writes spec-review.yaml as designed (step 7). `archon validate workflows` rejects the hearing loop_group, because `vacate` and `bench` are both terminal sinks. Spec review cannot load, so neither can gauntlet-run, which includes it, and plan-review fails the same way." },
  { "file": "docs/superpowers/specs/spec-review-design.md",
    "line": 112,
    "severity": "high",
    "claim": "new. Rows H29, S7 and S10. `.shared/rounds.py` state says: \"owed \\\"ended\\\": the latest ruling file's decision is an OwnerCase \\\"ends\\\"\". No Profile field turns this off, and `close` and the loop end both rest on it. Writing's revision profile declares `OwnerCase(\"SOUND\", ..., ends=\"approve\")` (writing-design.md:103). Writing also needs more rounds after an approve ruling: \"an entered plan revision, spec not \\\"\\\", and no spec round answering it closed ... next from rounds.state: reviser owes: revise; reviewer owes: review\" (writing-design.md:148-150). Once one revision is approved, rounds.state reports `ended` for good, and stage.py has no mapping for that value.",
    "failure_scenario": "In writing, the juror rules PLAN. The reviser files revision round 1, the reviewer rules SOUND, the owner approves, and `enter` writes plan rev1. Writing now owes a spec round that answers it. rounds.state reads ruling 1 (approve, an ends option) and prints owed \"ended\", never \"reviser\". So stage.py's \"revise\" branch has no next value: the spec revision never starts, and writing stalls until its own cap. The same happens to any second PLAN or SPEC verdict later in the run." },
  { "file": "docs/superpowers/specs/spec-review-design.md",
    "line": 131,
    "severity": "medium",
    "claim": "new. Rows H28 and H29 (CLAUDE.md 1.3). \"Every case but guard and cap is read only from a review written in this iteration\". With round = latest tried + 1 (state, :104-110), a fresh rerun never asks again about a READY, INVALID or APPROACH THE BENCH review the owner left unanswered. Its round counts as tried, so the speccer is owed a new block. The Why and Terms text says a rerun \"continues the rounds from the files\", but no file records a pending ask.",
    "failure_scenario": "Round 7 is READY. The reporter writes summary 7 and `bench` asks. The owner never answers that run and later starts `archon workflow run spec-review` (or gauntlet-run) on the same task. `docket-in` gives round 8, owed speccer. The speccer spends an Opus turn (plus spikers) revising a block that had nothing to answer, and the arbiter tries round 8. The owner is never shown READY round 7, and round 8 may come back different. plan-review has the same gap for an unanswered APPROVED." },
  { "file": "docs/superpowers/specs/spec-review-design.md",
    "line": 128,
    "severity": "medium",
    "claim": "new. Row H28 (missing contract: a bound on iterations that try no round in specs; CLAUDE.md 1.3). Guard reads \"stretch >= STRETCH or repairs >= 5\", but \"repairs (plans only)\" (:120). In spec review, an iteration where the speccer writes no `<slug>.N.txt`, or the arbiter writes no review, adds nothing to stretch or repairs. Only `cap` at 200 iterations asks the owner. This is the gap D-14 objection 1 fixed for plans through `repairs`, left open for specs.",
    "failure_scenario": "The speccer's filing turn ends without writing block N, for example when its spikers report \"cannot be measured\" and it stops. `ready` keeps owed speccer, `screen` and the arbiter are skipped, and docket gives case none. Every later iteration resumes the Opus speccer session (and its spikers) on the same round. The owner is asked only after 200 iterations. An arbiter turn that writes no review loops the same way, through screen plus an Opus arbiter turn per iteration." },
  { "file": "docs/superpowers/specs/spec-review-design.md",
    "line": 364,
    "severity": "low",
    "claim": "new. Rows H15 and H5. `plan: { description: Path of gauntlet/plans/approved/<slug>.txt, or \"\" when planning found no plan needed. }` declares no `default: \"\"`. The standalone form in Homes (:553) is `--input task=<path> --input plan=<path>`, and no line tells the owner to pass `--input plan=` for a tests-only task. workflow-language.md:1946-1947: \"Omitting one with no default and no required: true leaves it unset, and a body referencing it fails at the reference site.\"",
    "failure_scenario": "The owner runs `archon workflow run spec-review --input task=gauntlet/tasks/x.md` for a task that only edits tests/. `guard` and `docket-in` run, then `open` fails at its `$INPUTS.plan` reference. Nothing is wrong with the task, yet the phase stops." },
  { "file": "docs/superpowers/specs/spec-review-design.md",
    "line": 335,
    "severity": "low",
    "claim": "new. Rows A3 and H27. \"A named script, because an inline `script:` inside an `include:` block cannot read the block's inputs.\" The documents say otherwise: workflow-language.md:1704-1708 says every `script:` node, \"whether the body is inline or a named file\", receives `INPUTS_<UPPER_SNAKE>`; only the `$INPUTS.<name>` macro is a load error. plan-review-design.md:434-437 does the same job with an inline `script:` reading INPUTS_TASK, and gauntlet-design.md:28 states both handoffs read `INPUTS_<NAME>` from the environment.",
    "failure_scenario": "A builder or reviewer takes :335 as the rule. They convert plan review's inline `handoff` into a named script, or flag it as a load error. Or the designs carry two contradicting statements of the inline-script rule that rows A3 and H27 are meant to settle." }
] }
```
