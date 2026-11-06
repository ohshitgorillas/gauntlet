# Convergence round 3 - gauntlet-intake-design.md

Reviewer return (cad-reviewer-medium, opus), verbatim. Designs at 87e0734.

```json
{ "findings": [
  { "file": "docs/superpowers/specs/gauntlet-intake-design.md",
    "line": 59,
    "severity": "medium",
    "claim": "Mark: new. The applied G-80/D-53 form, \"a rule from a .gitignore passes only when git tracks that file and `git diff --quiet HEAD -- <file>` holds\" (with the message at :66-67, \"...which is not committed... Commit <file> and restart the run\"; rows H1, S3), fails the run-start guard whenever .gitignore has any uncommitted edit, even when HEAD's .gitignore already holds the gauntlet/ rule the tree will get. That is a stop on a non-issue under CLAUDE.md 1.4.",
    "failure_scenario": "HEAD's .gitignore holds `gauntlet/`. The owner has an uncommitted, unrelated `*.log` line in .gitignore. `git check-ignore -v gauntlet/` names .gitignore, `git diff --quiet HEAD -- .gitignore` fails, and gauntlet-run's guard exits 1 telling the owner to commit the file. The tree cut from HEAD would have ignored gauntlet/ anyway. This also pre-empts gauntlet-design.md's `dirty` ask (gauntlet-design.md:65-71), which exists to offer 'Go on' for exactly such uncommitted changes. A variant: the working-copy .gitignore adds the rule and .git/info/exclude also holds it. check-ignore names the higher-precedence .gitignore, so the run is refused though the tree shares info/exclude." },
  { "file": "docs/superpowers/specs/gauntlet-intake-design.md",
    "line": 255,
    "severity": "low",
    "claim": "Mark: new (the defect class of G-73/D-50, which fixed the refusal but not the reply). Node `show` prints \"reply (turn's, else the opening)\" from `reply: { from: $turn.output.reply, if_skipped: \"\" }` (:257), so it cannot tell a skipped `turn` from one that ran with an empty reply. It then reprints Clerk's opening reply as if it were current. Missing contract: the source of the reply `show` displays (intake's own row 'A Clerk iteration's task path and refusal', :308, covers only the task and refusal; A14 is the `if_skipped` form).",
    "failure_scenario": "Iteration 1: Clerk's opening reply asks three questions and holds no draft. The owner answers 'approve'. In iteration 2, `turn` outputs the draft with reply \"\" (nothing open). `show` sees reply \"\" and prints the opening reply's three stale questions above the new task file. The owner answers questions Clerk already settled, which costs a needless turn, or approves under a misleading prompt." },
  { "file": "docs/superpowers/specs/gauntlet-intake-design.md",
    "line": 145,
    "severity": "low",
    "claim": "Mark: new. put.ts's first branch, \"draft \\\"\\\" or slug \\\"\\\": writes nothing ... stdout { \\\"slug\\\": <owned> or \\\"\\\", \\\"task\\\", \\\"refusal\\\": \\\"\\\" }\", also silently drops a non-empty draft whose slug is \"\". The `clerk`/`turn` pattern (:205, :231) allows \"\" there. No refusal reaches Clerk, and every other wrong-slug case gets a refusal (:147-150). Rows P6, H3, and the refusal hand-off contract G-73 added.",
    "failure_scenario": "Before any write, `turn` outputs a full draft with slug \"\". `put` writes nothing, `latest` prints task \"\" and refusal \"\", and `show` prints 'No task file yet.' The owner approves. `until_bash` fails on `[ -s \"\" ]`. The next turn's prompt carries 'approve' and an empty refusal, so nothing tells Clerk its draft was dropped. Clerk believes the draft is written and may answer with draft \"\" again, so each further owner answer is spent with no task file. After a first write, the same branch discards an edited draft, and `show` keeps the old file with no word to Clerk." },
  { "file": "docs/superpowers/specs/gauntlet-design.md",
    "line": 23,
    "severity": "low",
    "claim": "Mark: new (citations drifted after the G-12 rewrite and the pass-2 application). The copy list's citations into the intake design no longer point at the text they claim. `gauntlet-intake-design.md:152` (description, :23) is put.ts's stdout comment; the description is at :161-162. `:157` (worktree, :24) is the prose line; `worktree:` is at :166-167. `:165` (guard, :25) is `effort: medium`; `guard` is at :175-177. `:260` (handoff output_format, :26) is show's `opening:` binding; handoff's output_format is at :278. `:179`/`:186` (the when lines, :27) are comments; the `when:` lines are at :189 and :196. `:122` (:30) is inside the JSON; the CLAUDE_PROJECT_DIR prose is at :127. Rows H13, A1, S13, H3, H6 (seeds B01-B05).",
    "failure_scenario": "A builder at gauntlet Order step 1 checks each 'Resolved by G-12' claim at the cited intake lines. It finds put.ts comments, `effort: medium` and show bindings instead of the description, the `worktree:` key, the guard node and the handoff's output_format, and has to hunt for the real text or report a false mismatch." }
] }
```
