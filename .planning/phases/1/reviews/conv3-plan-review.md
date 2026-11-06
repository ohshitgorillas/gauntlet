# Convergence round 3 - plan-review-design.md

Reviewer return (cad-reviewer-medium, opus), verbatim. Designs at 87e0734.

```json
{ "findings": [
  { "file": "docs/superpowers/specs/plan-review-design.md",
    "line": 330,
    "severity": "high",
    "claim": "[row H38, also A15; new] The loop body has a second terminal sink: node `vacate` depends on `filing` and nothing depends on it. Yet `bench` is declared the body's \"sole terminal sink\" (:409), and Archon rejects that shape at load.",
    "failure_scenario": "Quoted: \"- id: vacate ... depends_on: [filing] ... cancel: ...\" (:330-333) and \"- id: bench  # the owner; sole terminal sink of the body\" (:409). loop-nodes.md:682-684: \"A wait pauses the group only as the body's sole terminal sink: nothing depends on it, and every other body node leads to it. Any other placement is a load error\"; workflow-language.md:773 likewise rejects a non-terminal body wait. `vacate` does not lead to `bench`, so plan-review.yaml as designed fails `archon validate workflows` and cannot run, standalone or as a block of gauntlet-run. spec-review-design.md:421-424 has the same `vacate` shape. G-11 and G-56 ruled where `vacate` reads its value, not the sink rule."
  },
  { "file": "docs/superpowers/specs/plan-review-design.md",
    "line": 149,
    "severity": "medium",
    "claim": "[row H28; new] An owner case is read only from a review written in the same iteration. A failure resume restarts the loop at iteration 1, and a rerun continues from the files, so a review whose case was never put to the owner loses that case for good.",
    "failure_scenario": "Quoted: \"Every case but guard and cap is read only from a review written in this iteration; an iteration with no new review is \\\"none\\\" unless guard or cap holds.\" The prosecutor writes `<slug>.review.N.txt` APPROVED. Then node `report` (an agent) fails, or the run dies before `bench`. The owner runs `archon workflow resume`, which, per loop-nodes.md:945-947, restarts the loop_group at iteration 1, or starts a rerun as :444 invites. `filing` sees round N tried (its review exists) and owes the defense round N+1. `docket` finds no new review and returns none. The approved plan never reaches the owner. Instead an Opus defense turn revises it \"to answer the latest review\" (:188), and the screen and a prosecutor try it again (CLAUDE.md 1.3). An APPROACH THE BENCH question is lost the same way. Spec review shares this through `.shared/rounds.py` (spec-review-design.md:131)."
  },
  { "file": "docs/superpowers/specs/plan-review-design.md",
    "line": 87,
    "severity": "medium",
    "claim": "[missing row: cite.py's exit contract, P20 area; new] `cite.py` exits 2 when the plan file is missing. A defense turn that wrote no plan N therefore fails node `cite`, which blocks `ready` and fails the run, where the ledger would simply have owed the defense again.",
    "failure_scenario": "Quoted: \"# Plan file unreadable or unwritable: exit 2.\" Compare the comment on node `cite` (:349), \"exit 0, so a bad marker fails nothing\". The defense ends its turn without writing `gauntlet/plans/<slug>.N.txt` (a fence refusal on a typed path, or a wrong N). Then `cite` gets `INPUTS_PLAN=$filing.output.file`, the file is missing, and it exits 2. `ready` (`none_failed_min_one_success`) is blocked by the failed dependency, so the hearing fails and the run stops. Yet `state` already reports a missing plan as owed defense (:119), and spec review, which has no cite node, just retries the speccer. This is a stop on a recoverable slip (CLAUDE.md 1.4). The resume then restarts the loop at iteration 1."
  },
  { "file": "docs/superpowers/specs/plan-review-design.md",
    "line": 400,
    "severity": "medium",
    "claim": "[missing row: the reporter role's inputs; R1 and R2 cover only defense.md and prosecutor.md; new] The fresh reporter is handed only a round number, but its role reads `gauntlet/plans/<slug>.N.txt`. No input gives it the slug or the task path.",
    "failure_scenario": "Quoted: \"prompt: <approved round $case.output.round>\" with \"context: fresh\" (:397). The role (:243) says \"Input: the approved round N. Read gauntlet/plans/<slug>.N.txt\". Unlike the prosecutor and defense, which continue sessions primed with $INPUTS.task, this reporter never saw the task. Suppose the checkout's gauntlet/plans holds `a.3.txt` and `b.3.txt` from two tasks. A reporter told \"round 3\" must list the folder and guess. It may write `b-summary.3.md` for task `a`, and FENCE_ONCE then blocks a correct rewrite. The owner is asked to approve on a wrong or empty `attention` (the summary text, :140). spec-review-design.md:489 and writing-design.md:513 pass the same round-only prompt."
  },
  { "file": "docs/superpowers/specs/plan-review-design.md",
    "line": 76,
    "severity": "medium",
    "claim": "[missing row: the cite-marker grammar (named missing by G-59), against row H29's `filed` test; matches G-20, which the applied ruling resolved only in part] The ledger's cited test is a bare substring match on \"[cite:\", while `cite.py` resolves a grammar that does not define a marker lacking \" | \". Such text can leave a plan uncited forever with no unresolved line written.",
    "failure_scenario": "Quoted: \"The path ends at the first \\\" | \\\" after \\\"[cite: \\\"\" (:76) and \"A plan is cited when it holds no \\\"[cite:\\\" marker.\" (:106). The defense writes `[cite: a.py]`, or cites a code line that itself holds \"[cite:\" with no \" | \" after it (for example `filed=lambda text: \"[cite:\" not in text,` in this pack's own ledger, spec-review-design.md:178). The reasons `cite.py` can give (:81) have no case for a missing \" | \". If cite.py does not count it as a marker, it prints `{ \"unresolved\": [] }` and appends no `.cite.N.txt` line, so `repairs` stays 0 and the stretch does not grow. Meanwhile the ledger still sees \"[cite:\" and owes the defense, which is told nothing to fix. Each iteration then costs an Opus defense turn, up to CAP 200, after which every iteration asks the owner. G-20's ruling (b) made cite.py exit 0, but it did not align the two tests."
  },
  { "file": "docs/superpowers/specs/plan-review-design.md",
    "line": 140,
    "severity": "low",
    "claim": "[row H28; new] A guard ask raised by repairs >= REPAIRS shows the owner the counts and the latest review's text, never the unresolved markers or their reasons. Those exist only in `cite`'s stdout, and `<slug>.cite.N.txt` keeps only \"unresolved <n>\".",
    "failure_scenario": "Quoted: \"others: the counts and the latest review's text\". Plan 4 fails to cite five times, so case guard asks with `round` 4. The attention shows `repairs: 5` and review 3's text, which is about an earlier plan, and nothing about which paths or quotes failed. The owner's reply is the only way out of the loop, but the owner must answer blind or dig through files. The reply becomes a guard line, the defense may fail again, and five more Opus repair turns pass before the next ask."
  },
  { "file": "docs/superpowers/specs/plan-review-design.md",
    "line": 144,
    "severity": "low",
    "claim": "[rows H28 and A15; new, an interaction of the G-56 and G-55 rulings] The rule \"none when next is vacant\" takes precedence over cap. When the twelfth LEADING review lands in an iteration at or past 200, nothing is asked, so no further iteration is allowed and the loop ends on max_iterations, contrary to :26.",
    "failure_scenario": "Quoted: \"Cases, first that holds: none when next is vacant (vacate cancels in the next iteration, nothing asked)\" against :26, \"so the loop never ends on max_iterations\". The run is at iteration m >= 200, which runs only because the owner answered the cap ask of iteration m-1. Its prosecutor writes the twelfth LEADING review, `docket` returns none, and `bench` is skipped. With no accepted answer, Archon allows no iteration m+1 (workflow-language.md:773), so `vacate` never runs. The hearing fails on max_iterations instead of the run ending cancelled, which is the route gauntlet-design.md:19 states for vacancy."
  },
  { "file": "docs/superpowers/specs/plan-review-design.md",
    "line": 30,
    "severity": "low",
    "claim": "[rows P7 and H36; new] The no-collision guarantee rests on intake's kebab-case slug. But the standalone input accepts \"the owner's own\" task file, the slug is just its file name without .md, and nothing checks its shape.",
    "failure_scenario": "Quoted: \"Slug: kebab-case, [a-z0-9] runs joined by - (intake design), so no plan file <slug>.N.txt shares a name with any <slug>.review.N.txt\" against :278, \"Path of a task file under gauntlet/tasks/ (intake's handoff, through with:, or the owner's own)\". Take `archon workflow run plan-review --input task=gauntlet/tasks/a.review.md`. The slug is `a.review`, so plan 1 is `a.review.1.txt`, the same name as slug `a`'s review 1. The defense's FENCE_DENY pattern `gauntlet/plans/*.review.*.txt` (:255) also forbids it to write its own plan. A dotted slug such as `v2.1-fix` likewise shares the `v2.` prefix with slug `v2` in the stale set-aside, which moves \"every file of the slug\" (:44)."
  }
] }
```
